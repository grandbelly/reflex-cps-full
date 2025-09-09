--
-- PostgreSQL database dump
--



-- Dumped from database version 16.9 (Debian 16.9-1.pgdg110+1)
-- Dumped by pg_dump version 16.10 (Debian 16.10-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: timescaledb; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS timescaledb WITH SCHEMA public;


--
-- Name: EXTENSION timescaledb; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION timescaledb IS 'Enables scalable inserts and complex queries for time-series data (Community Edition)';


--
-- Name: timescaledb_toolkit; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit WITH SCHEMA public;


--
-- Name: EXTENSION timescaledb_toolkit; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION timescaledb_toolkit IS 'Library of analytical hyperfunctions, time-series pipelining, and other SQL utilities';


--
-- Name: plpython3u; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plpython3u WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpython3u; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION plpython3u IS 'PL/Python3U untrusted procedural language';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: detect_anomalies_zscore(); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.detect_anomalies_zscore()
    LANGUAGE plpgsql
    AS $$
BEGIN
  PERFORM set_config('statement_timeout','3s', true);

  WITH stats AS (
    SELECT f.tag_name,
           avg(f.mean_5m)         AS m,
           stddev_samp(f.mean_5m) AS sd
    FROM public.features_5m f
    WHERE f.bucket >= now() - interval '1 hour'
    GROUP BY f.tag_name
  ),
  latest AS (
    SELECT l.tag_name, l.ts, l.value
    FROM public.influx_latest l
  )
  INSERT INTO public.anomalies (ts, tag_name, score, level, context)
  SELECT l.ts,
         l.tag_name,
         COALESCE((l.value - s.m) / NULLIF(s.sd, 0), 0) AS z,
         CASE
           WHEN ABS(COALESCE((l.value - s.m) / NULLIF(s.sd, 0), 0)) >= 5 THEN 'CRITICAL'
           WHEN ABS(COALESCE((l.value - s.m) / NULLIF(s.sd, 0), 0)) >= 3 THEN 'HIGH'
           ELSE 'OK'
         END AS level,
         jsonb_build_object('method','zscore','window','1h','value',l.value,'mean',s.m,'sd',s.sd)
  FROM latest l
  JOIN stats  s ON s.tag_name = l.tag_name
  ON CONFLICT (ts, tag_name) DO NOTHING;
END;
$$;


--
-- Name: detect_anomalies_zscore(integer, jsonb); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.detect_anomalies_zscore(IN job_id integer, IN config jsonb)
    LANGUAGE plpgsql
    AS $$
BEGIN
  -- delegate to the zero-arg implementation
  CALL public.detect_anomalies_zscore();
END;
$$;


--
-- Name: ensure_prediction_table(text, integer, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.ensure_prediction_table(model_id text, horizon_min integer, window_min integer) RETURNS text
    LANGUAGE plpgsql
    AS $_$
DECLARE
  base TEXT := lower(regexp_replace(coalesce(model_id,'model'), '[^a-z0-9]+', '_', 'g'));
  tbl  TEXT := format('pred_%s_h%s_w%s', base, horizon_min, window_min);
BEGIN
  EXECUTE format($SQL$CREATE TABLE IF NOT EXISTS %I (
    ts        timestamptz     NOT NULL,
    tag_name  text            NOT NULL,
    horizon   interval        NOT NULL,
    yhat      double precision NOT NULL,
    pi_low    double precision,
    pi_high   double precision,
    model_id  text            NOT NULL,
    version   text            NOT NULL,
    features  jsonb           DEFAULT '{}'::jsonb,
    PRIMARY KEY (ts, tag_name)
  )$SQL$, tbl);
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I (tag_name, ts DESC)', tbl||'_tag_ts_idx', tbl);
  RETURN tbl;
END;$_$;


--
-- Name: proc_predict_plpy_linreg(integer, jsonb); Type: PROCEDURE; Schema: public; Owner: -
--

CREATE PROCEDURE public.proc_predict_plpy_linreg(IN job_id integer, IN config jsonb)
    LANGUAGE plpython3u
    AS $_$
import json

# parse config
if config is None:
    cfg = {}
elif isinstance(config, dict):
    cfg = config
else:
    try:
        cfg = json.loads(config)
    except Exception:
        cfg = {}

model_id    = str(cfg.get('model_id','linreg'))
version     = str(cfg.get('version','v1'))
horizon_min = int(cfg.get('horizon_min', 5))
window_min  = int(cfg.get('window_min', 60))

# 결과 테이블 확보 (prepare 사용)
plan_tbl = plpy.prepare("SELECT ensure_prediction_table($1,$2,$3) AS tbl", ["text","int","int"]) 
res = plpy.execute(plan_tbl, [model_id, horizon_min, window_min])[0]
tbl = res['tbl']

# tags
if 'tags' in cfg and cfg['tags']:
    tags = [str(t) for t in cfg['tags']]
else:
    tags = [r['tag_name'] for r in plpy.execute("SELECT tag_name FROM influx_tag ORDER BY tag_name")] 

# future point & data/select plans
fut_plan = plpy.prepare("SELECT EXTRACT(EPOCH FROM (now() + make_interval(mins=>$1)))::float8 AS x, (now() + make_interval(mins=>$1)) AS ts", ["int"]) 
sel_plan = plpy.prepare(
    """
    SELECT EXTRACT(EPOCH FROM bucket)::float8 AS x,
           avg::float8 AS y
    FROM influx_agg_1m
    WHERE tag_name = $1
      AND bucket > now() - make_interval(mins=>$2)
    ORDER BY bucket
    """,
    ["text","int"]
)

# dynamic insert into target table
ins_sql_tpl = (
  "INSERT INTO %s (ts, tag_name, horizon, yhat, pi_low, pi_high, model_id, version, features) "
  "VALUES ($1,$2, make_interval(mins=>$3), $4,$5,$6,$7,$8,$9::jsonb) "
  "ON CONFLICT (ts, tag_name) DO UPDATE SET yhat=EXCLUDED.yhat, pi_low=EXCLUDED.pi_low, pi_high=EXCLUDED.pi_high, model_id=EXCLUDED.model_id, version=EXCLUDED.version, features=EXCLUDED.features"
) % tbl
ins_plan = plpy.prepare(ins_sql_tpl, ["timestamptz","text","int","float8","float8","float8","text","text","text"])

fut = plpy.execute(fut_plan, [horizon_min])[0]
x_pred = float(fut['x'])
ts_pred = fut['ts']

for tag in tags:
    rows = plpy.execute(sel_plan, [tag, window_min])
    n = len(rows)
    if n < 2:
        continue
    xs = [float(r['x']) for r in rows]
    ys = [float(r['y']) for r in rows]
    sx = sum(xs); sy = sum(ys)
    sxx = sum(x*x for x in xs)
    sxy = sum(x*y for x,y in zip(xs,ys))
    denom = n * sxx - sx * sx
    if denom == 0:
        continue
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    yhat = slope * x_pred + intercept

    feats = json.dumps({
        'window_min': window_min,
        'horizon_min': horizon_min,
        'n': n,
        'slope': slope,
        'intercept': intercept
    })
    plpy.execute(ins_plan, [ts_pred, tag, horizon_min, float(yhat), float(yhat), float(yhat), model_id, version, feats])
$_$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: _compressed_hypertable_6; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._compressed_hypertable_6 (
);


--
-- Name: influx_hist; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.influx_hist (
    ts timestamp with time zone NOT NULL,
    tag_name text NOT NULL,
    value double precision NOT NULL,
    qc smallint DEFAULT 0,
    meta jsonb DEFAULT '{}'::jsonb
);


--
-- Name: _direct_view_10; Type: VIEW; Schema: _timescaledb_internal; Owner: -
--

CREATE VIEW _timescaledb_internal._direct_view_10 AS
 SELECT public.time_bucket('1 day'::interval, ts) AS bucket,
    tag_name,
    count(*) AS n,
    avg(value) AS avg,
    sum(value) AS sum,
    min(value) AS min,
    max(value) AS max,
    public.last(value, ts) AS last,
    public.first(value, ts) AS first,
    (public.last(value, ts) - public.first(value, ts)) AS diff
   FROM public.influx_hist
  GROUP BY (public.time_bucket('1 day'::interval, ts)), tag_name;


--
-- Name: _direct_view_3; Type: VIEW; Schema: _timescaledb_internal; Owner: -
--

CREATE VIEW _timescaledb_internal._direct_view_3 AS
 SELECT public.time_bucket('00:01:00'::interval, ts) AS bucket,
    tag_name,
    count(*) AS n,
    avg(value) AS avg,
    sum(value) AS sum,
    min(value) AS min,
    max(value) AS max,
    public.last(value, ts) AS last,
    public.first(value, ts) AS first,
    (public.last(value, ts) - public.first(value, ts)) AS diff
   FROM public.influx_hist
  GROUP BY (public.time_bucket('00:01:00'::interval, ts)), tag_name;


--
-- Name: _direct_view_4; Type: VIEW; Schema: _timescaledb_internal; Owner: -
--

CREATE VIEW _timescaledb_internal._direct_view_4 AS
 SELECT public.time_bucket('00:10:00'::interval, ts) AS bucket,
    tag_name,
    count(*) AS n,
    avg(value) AS avg,
    sum(value) AS sum,
    min(value) AS min,
    max(value) AS max,
    public.last(value, ts) AS last,
    public.first(value, ts) AS first,
    (public.last(value, ts) - public.first(value, ts)) AS diff
   FROM public.influx_hist
  GROUP BY (public.time_bucket('00:10:00'::interval, ts)), tag_name;


--
-- Name: _direct_view_5; Type: VIEW; Schema: _timescaledb_internal; Owner: -
--

CREATE VIEW _timescaledb_internal._direct_view_5 AS
 SELECT public.time_bucket('01:00:00'::interval, ts) AS bucket,
    tag_name,
    count(*) AS n,
    avg(value) AS avg,
    sum(value) AS sum,
    min(value) AS min,
    max(value) AS max,
    public.last(value, ts) AS last,
    public.first(value, ts) AS first,
    (public.last(value, ts) - public.first(value, ts)) AS diff
   FROM public.influx_hist
  GROUP BY (public.time_bucket('01:00:00'::interval, ts)), tag_name;


--
-- Name: _direct_view_7; Type: VIEW; Schema: _timescaledb_internal; Owner: -
--

CREATE VIEW _timescaledb_internal._direct_view_7 AS
 SELECT public.time_bucket('00:05:00'::interval, ts) AS bucket,
    tag_name,
    avg(value) AS mean_5m,
    stddev_samp(value) AS std_5m,
    min(value) AS min_5m,
    max(value) AS max_5m,
    percentile_disc((0.1)::double precision) WITHIN GROUP (ORDER BY value) AS p10_5m,
    percentile_disc((0.9)::double precision) WITHIN GROUP (ORDER BY value) AS p90_5m,
    count(*) AS n_5m
   FROM public.influx_hist
  GROUP BY (public.time_bucket('00:05:00'::interval, ts)), tag_name;


--
-- Name: _materialized_hypertable_10; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._materialized_hypertable_10 (
    bucket timestamp with time zone NOT NULL,
    tag_name text,
    n bigint,
    avg double precision,
    sum double precision,
    min double precision,
    max double precision,
    last double precision,
    first double precision,
    diff double precision
);


--
-- Name: _hyper_10_12_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_10_12_chunk (
    CONSTRAINT constraint_12 CHECK (((bucket >= '2025-07-31 09:00:00+09'::timestamp with time zone) AND (bucket < '2025-10-09 09:00:00+09'::timestamp with time zone)))
)
INHERITS (_timescaledb_internal._materialized_hypertable_10);


--
-- Name: _hyper_2_10_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_2_10_chunk (
    CONSTRAINT constraint_10 CHECK (((ts >= '2025-08-14 09:00:00+09'::timestamp with time zone) AND (ts < '2025-08-21 09:00:00+09'::timestamp with time zone)))
)
INHERITS (public.influx_hist);


--
-- Name: _hyper_2_13_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_2_13_chunk (
    CONSTRAINT constraint_13 CHECK (((ts >= '2025-08-21 09:00:00+09'::timestamp with time zone) AND (ts < '2025-08-28 09:00:00+09'::timestamp with time zone)))
)
INHERITS (public.influx_hist);


--
-- Name: _hyper_2_16_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_2_16_chunk (
    CONSTRAINT constraint_15 CHECK (((ts >= '2025-08-28 09:00:00+09'::timestamp with time zone) AND (ts < '2025-09-04 09:00:00+09'::timestamp with time zone)))
)
INHERITS (public.influx_hist);


--
-- Name: _hyper_2_4_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_2_4_chunk (
    CONSTRAINT constraint_4 CHECK (((ts >= '2025-08-07 09:00:00+09'::timestamp with time zone) AND (ts < '2025-08-14 09:00:00+09'::timestamp with time zone)))
)
INHERITS (public.influx_hist);


--
-- Name: _materialized_hypertable_3; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._materialized_hypertable_3 (
    bucket timestamp with time zone NOT NULL,
    tag_name text,
    n bigint,
    avg double precision,
    sum double precision,
    min double precision,
    max double precision,
    last double precision,
    first double precision,
    diff double precision
);


--
-- Name: _hyper_3_2_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_3_2_chunk (
    CONSTRAINT constraint_2 CHECK (((bucket >= '2025-07-31 09:00:00+09'::timestamp with time zone) AND (bucket < '2025-10-09 09:00:00+09'::timestamp with time zone)))
)
INHERITS (_timescaledb_internal._materialized_hypertable_3);


--
-- Name: _materialized_hypertable_4; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._materialized_hypertable_4 (
    bucket timestamp with time zone NOT NULL,
    tag_name text,
    n bigint,
    avg double precision,
    sum double precision,
    min double precision,
    max double precision,
    last double precision,
    first double precision,
    diff double precision
);


--
-- Name: _hyper_4_5_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_4_5_chunk (
    CONSTRAINT constraint_5 CHECK (((bucket >= '2025-07-31 09:00:00+09'::timestamp with time zone) AND (bucket < '2025-10-09 09:00:00+09'::timestamp with time zone)))
)
INHERITS (_timescaledb_internal._materialized_hypertable_4);


--
-- Name: _materialized_hypertable_5; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._materialized_hypertable_5 (
    bucket timestamp with time zone NOT NULL,
    tag_name text,
    n bigint,
    avg double precision,
    sum double precision,
    min double precision,
    max double precision,
    last double precision,
    first double precision,
    diff double precision
);


--
-- Name: _hyper_5_6_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_5_6_chunk (
    CONSTRAINT constraint_6 CHECK (((bucket >= '2025-07-31 09:00:00+09'::timestamp with time zone) AND (bucket < '2025-10-09 09:00:00+09'::timestamp with time zone)))
)
INHERITS (_timescaledb_internal._materialized_hypertable_5);


--
-- Name: predictions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.predictions (
    ts timestamp with time zone NOT NULL,
    tag_name text NOT NULL,
    horizon interval NOT NULL,
    yhat double precision NOT NULL,
    pi_low double precision,
    pi_high double precision,
    model_id text NOT NULL,
    version text NOT NULL,
    features jsonb DEFAULT '{}'::jsonb
);


--
-- Name: _hyper_8_9_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_8_9_chunk (
    CONSTRAINT constraint_9 CHECK (((ts >= '2025-08-07 09:00:00+09'::timestamp with time zone) AND (ts < '2025-08-14 09:00:00+09'::timestamp with time zone)))
)
INHERITS (public.predictions);


--
-- Name: anomalies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.anomalies (
    ts timestamp with time zone NOT NULL,
    tag_name text NOT NULL,
    score double precision NOT NULL,
    level text NOT NULL,
    context jsonb DEFAULT '{}'::jsonb
);


--
-- Name: _hyper_9_11_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_9_11_chunk (
    CONSTRAINT constraint_11 CHECK (((ts >= '2025-08-14 09:00:00+09'::timestamp with time zone) AND (ts < '2025-08-21 09:00:00+09'::timestamp with time zone)))
)
INHERITS (public.anomalies);


--
-- Name: _hyper_9_14_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_9_14_chunk (
    CONSTRAINT constraint_14 CHECK (((ts >= '2025-08-21 09:00:00+09'::timestamp with time zone) AND (ts < '2025-08-28 09:00:00+09'::timestamp with time zone)))
)
INHERITS (public.anomalies);


--
-- Name: _hyper_9_17_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_9_17_chunk (
    CONSTRAINT constraint_16 CHECK (((ts >= '2025-08-28 09:00:00+09'::timestamp with time zone) AND (ts < '2025-09-04 09:00:00+09'::timestamp with time zone)))
)
INHERITS (public.anomalies);


--
-- Name: _hyper_9_7_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._hyper_9_7_chunk (
    CONSTRAINT constraint_7 CHECK (((ts >= '2025-08-07 09:00:00+09'::timestamp with time zone) AND (ts < '2025-08-14 09:00:00+09'::timestamp with time zone)))
)
INHERITS (public.anomalies);


--
-- Name: _materialized_hypertable_7; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal._materialized_hypertable_7 (
    bucket timestamp with time zone NOT NULL,
    tag_name text,
    mean_5m double precision,
    std_5m double precision,
    min_5m double precision,
    max_5m double precision,
    p10_5m double precision,
    p90_5m double precision,
    n_5m bigint
);


--
-- Name: _partial_view_10; Type: VIEW; Schema: _timescaledb_internal; Owner: -
--

CREATE VIEW _timescaledb_internal._partial_view_10 AS
 SELECT public.time_bucket('1 day'::interval, ts) AS bucket,
    tag_name,
    count(*) AS n,
    avg(value) AS avg,
    sum(value) AS sum,
    min(value) AS min,
    max(value) AS max,
    public.last(value, ts) AS last,
    public.first(value, ts) AS first,
    (public.last(value, ts) - public.first(value, ts)) AS diff
   FROM public.influx_hist
  GROUP BY (public.time_bucket('1 day'::interval, ts)), tag_name;


--
-- Name: _partial_view_3; Type: VIEW; Schema: _timescaledb_internal; Owner: -
--

CREATE VIEW _timescaledb_internal._partial_view_3 AS
 SELECT public.time_bucket('00:01:00'::interval, ts) AS bucket,
    tag_name,
    count(*) AS n,
    avg(value) AS avg,
    sum(value) AS sum,
    min(value) AS min,
    max(value) AS max,
    public.last(value, ts) AS last,
    public.first(value, ts) AS first,
    (public.last(value, ts) - public.first(value, ts)) AS diff
   FROM public.influx_hist
  GROUP BY (public.time_bucket('00:01:00'::interval, ts)), tag_name;


--
-- Name: _partial_view_4; Type: VIEW; Schema: _timescaledb_internal; Owner: -
--

CREATE VIEW _timescaledb_internal._partial_view_4 AS
 SELECT public.time_bucket('00:10:00'::interval, ts) AS bucket,
    tag_name,
    count(*) AS n,
    avg(value) AS avg,
    sum(value) AS sum,
    min(value) AS min,
    max(value) AS max,
    public.last(value, ts) AS last,
    public.first(value, ts) AS first,
    (public.last(value, ts) - public.first(value, ts)) AS diff
   FROM public.influx_hist
  GROUP BY (public.time_bucket('00:10:00'::interval, ts)), tag_name;


--
-- Name: _partial_view_5; Type: VIEW; Schema: _timescaledb_internal; Owner: -
--

CREATE VIEW _timescaledb_internal._partial_view_5 AS
 SELECT public.time_bucket('01:00:00'::interval, ts) AS bucket,
    tag_name,
    count(*) AS n,
    avg(value) AS avg,
    sum(value) AS sum,
    min(value) AS min,
    max(value) AS max,
    public.last(value, ts) AS last,
    public.first(value, ts) AS first,
    (public.last(value, ts) - public.first(value, ts)) AS diff
   FROM public.influx_hist
  GROUP BY (public.time_bucket('01:00:00'::interval, ts)), tag_name;


--
-- Name: _partial_view_7; Type: VIEW; Schema: _timescaledb_internal; Owner: -
--

CREATE VIEW _timescaledb_internal._partial_view_7 AS
 SELECT public.time_bucket('00:05:00'::interval, ts) AS bucket,
    tag_name,
    avg(value) AS mean_5m,
    stddev_samp(value) AS std_5m,
    min(value) AS min_5m,
    max(value) AS max_5m,
    percentile_disc((0.1)::double precision) WITHIN GROUP (ORDER BY value) AS p10_5m,
    percentile_disc((0.9)::double precision) WITHIN GROUP (ORDER BY value) AS p90_5m,
    count(*) AS n_5m
   FROM public.influx_hist
  GROUP BY (public.time_bucket('00:05:00'::interval, ts)), tag_name;


--
-- Name: compress_hyper_6_15_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal.compress_hyper_6_15_chunk (
    _ts_meta_count integer,
    tag_name text,
    _ts_meta_min_1 timestamp with time zone,
    _ts_meta_max_1 timestamp with time zone,
    ts _timescaledb_internal.compressed_data,
    value _timescaledb_internal.compressed_data,
    qc _timescaledb_internal.compressed_data,
    meta _timescaledb_internal.compressed_data
)
WITH (toast_tuple_target='128');
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_15_chunk ALTER COLUMN _ts_meta_count SET STATISTICS 1000;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_15_chunk ALTER COLUMN tag_name SET STATISTICS 1000;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_15_chunk ALTER COLUMN _ts_meta_min_1 SET STATISTICS 1000;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_15_chunk ALTER COLUMN _ts_meta_max_1 SET STATISTICS 1000;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_15_chunk ALTER COLUMN ts SET STATISTICS 0;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_15_chunk ALTER COLUMN value SET STATISTICS 0;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_15_chunk ALTER COLUMN qc SET STATISTICS 0;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_15_chunk ALTER COLUMN meta SET STATISTICS 0;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_15_chunk ALTER COLUMN meta SET STORAGE EXTENDED;


--
-- Name: compress_hyper_6_18_chunk; Type: TABLE; Schema: _timescaledb_internal; Owner: -
--

CREATE TABLE _timescaledb_internal.compress_hyper_6_18_chunk (
    _ts_meta_count integer,
    tag_name text,
    _ts_meta_min_1 timestamp with time zone,
    _ts_meta_max_1 timestamp with time zone,
    ts _timescaledb_internal.compressed_data,
    value _timescaledb_internal.compressed_data,
    qc _timescaledb_internal.compressed_data,
    meta _timescaledb_internal.compressed_data
)
WITH (toast_tuple_target='128');
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_18_chunk ALTER COLUMN _ts_meta_count SET STATISTICS 1000;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_18_chunk ALTER COLUMN tag_name SET STATISTICS 1000;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_18_chunk ALTER COLUMN _ts_meta_min_1 SET STATISTICS 1000;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_18_chunk ALTER COLUMN _ts_meta_max_1 SET STATISTICS 1000;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_18_chunk ALTER COLUMN ts SET STATISTICS 0;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_18_chunk ALTER COLUMN value SET STATISTICS 0;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_18_chunk ALTER COLUMN qc SET STATISTICS 0;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_18_chunk ALTER COLUMN meta SET STATISTICS 0;
ALTER TABLE ONLY _timescaledb_internal.compress_hyper_6_18_chunk ALTER COLUMN meta SET STORAGE EXTENDED;


--
-- Name: ai_conversations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_conversations (
    id integer NOT NULL,
    session_id character varying(100),
    user_query text,
    ai_response text,
    context_used jsonb,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: ai_conversations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ai_conversations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ai_conversations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ai_conversations_id_seq OWNED BY public.ai_conversations.id;


--
-- Name: ai_knowledge_base; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_knowledge_base (
    id integer NOT NULL,
    content text NOT NULL,
    content_type character varying(50),
    metadata jsonb,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: ai_knowledge_base_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ai_knowledge_base_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ai_knowledge_base_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ai_knowledge_base_id_seq OWNED BY public.ai_knowledge_base.id;


--
-- Name: features_5m; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.features_5m AS
 SELECT _materialized_hypertable_7.bucket,
    _materialized_hypertable_7.tag_name,
    _materialized_hypertable_7.mean_5m,
    _materialized_hypertable_7.std_5m,
    _materialized_hypertable_7.min_5m,
    _materialized_hypertable_7.max_5m,
    _materialized_hypertable_7.p10_5m,
    _materialized_hypertable_7.p90_5m,
    _materialized_hypertable_7.n_5m
   FROM _timescaledb_internal._materialized_hypertable_7
  WHERE (_materialized_hypertable_7.bucket < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(7)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT public.time_bucket('00:05:00'::interval, influx_hist.ts) AS bucket,
    influx_hist.tag_name,
    avg(influx_hist.value) AS mean_5m,
    stddev_samp(influx_hist.value) AS std_5m,
    min(influx_hist.value) AS min_5m,
    max(influx_hist.value) AS max_5m,
    percentile_disc((0.1)::double precision) WITHIN GROUP (ORDER BY influx_hist.value) AS p10_5m,
    percentile_disc((0.9)::double precision) WITHIN GROUP (ORDER BY influx_hist.value) AS p90_5m,
    count(*) AS n_5m
   FROM public.influx_hist
  WHERE (influx_hist.ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(7)), '-infinity'::timestamp with time zone))
  GROUP BY (public.time_bucket('00:05:00'::interval, influx_hist.ts)), influx_hist.tag_name;


--
-- Name: influx_agg_10m; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.influx_agg_10m AS
 SELECT _materialized_hypertable_4.bucket,
    _materialized_hypertable_4.tag_name,
    _materialized_hypertable_4.n,
    _materialized_hypertable_4.avg,
    _materialized_hypertable_4.sum,
    _materialized_hypertable_4.min,
    _materialized_hypertable_4.max,
    _materialized_hypertable_4.last,
    _materialized_hypertable_4.first,
    _materialized_hypertable_4.diff
   FROM _timescaledb_internal._materialized_hypertable_4
  WHERE (_materialized_hypertable_4.bucket < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(4)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT public.time_bucket('00:10:00'::interval, influx_hist.ts) AS bucket,
    influx_hist.tag_name,
    count(*) AS n,
    avg(influx_hist.value) AS avg,
    sum(influx_hist.value) AS sum,
    min(influx_hist.value) AS min,
    max(influx_hist.value) AS max,
    public.last(influx_hist.value, influx_hist.ts) AS last,
    public.first(influx_hist.value, influx_hist.ts) AS first,
    (public.last(influx_hist.value, influx_hist.ts) - public.first(influx_hist.value, influx_hist.ts)) AS diff
   FROM public.influx_hist
  WHERE (influx_hist.ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(4)), '-infinity'::timestamp with time zone))
  GROUP BY (public.time_bucket('00:10:00'::interval, influx_hist.ts)), influx_hist.tag_name;


--
-- Name: influx_agg_1d; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.influx_agg_1d AS
 SELECT bucket,
    tag_name,
    n,
    avg,
    sum,
    min,
    max,
    last,
    first,
    diff
   FROM _timescaledb_internal._materialized_hypertable_10;


--
-- Name: influx_agg_1h; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.influx_agg_1h AS
 SELECT _materialized_hypertable_5.bucket,
    _materialized_hypertable_5.tag_name,
    _materialized_hypertable_5.n,
    _materialized_hypertable_5.avg,
    _materialized_hypertable_5.sum,
    _materialized_hypertable_5.min,
    _materialized_hypertable_5.max,
    _materialized_hypertable_5.last,
    _materialized_hypertable_5.first,
    _materialized_hypertable_5.diff
   FROM _timescaledb_internal._materialized_hypertable_5
  WHERE (_materialized_hypertable_5.bucket < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(5)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT public.time_bucket('01:00:00'::interval, influx_hist.ts) AS bucket,
    influx_hist.tag_name,
    count(*) AS n,
    avg(influx_hist.value) AS avg,
    sum(influx_hist.value) AS sum,
    min(influx_hist.value) AS min,
    max(influx_hist.value) AS max,
    public.last(influx_hist.value, influx_hist.ts) AS last,
    public.first(influx_hist.value, influx_hist.ts) AS first,
    (public.last(influx_hist.value, influx_hist.ts) - public.first(influx_hist.value, influx_hist.ts)) AS diff
   FROM public.influx_hist
  WHERE (influx_hist.ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(5)), '-infinity'::timestamp with time zone))
  GROUP BY (public.time_bucket('01:00:00'::interval, influx_hist.ts)), influx_hist.tag_name;


--
-- Name: influx_agg_1m; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.influx_agg_1m AS
 SELECT _materialized_hypertable_3.bucket,
    _materialized_hypertable_3.tag_name,
    _materialized_hypertable_3.n,
    _materialized_hypertable_3.avg,
    _materialized_hypertable_3.sum,
    _materialized_hypertable_3.min,
    _materialized_hypertable_3.max,
    _materialized_hypertable_3.last,
    _materialized_hypertable_3.first,
    _materialized_hypertable_3.diff
   FROM _timescaledb_internal._materialized_hypertable_3
  WHERE (_materialized_hypertable_3.bucket < COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(3)), '-infinity'::timestamp with time zone))
UNION ALL
 SELECT public.time_bucket('00:01:00'::interval, influx_hist.ts) AS bucket,
    influx_hist.tag_name,
    count(*) AS n,
    avg(influx_hist.value) AS avg,
    sum(influx_hist.value) AS sum,
    min(influx_hist.value) AS min,
    max(influx_hist.value) AS max,
    public.last(influx_hist.value, influx_hist.ts) AS last,
    public.first(influx_hist.value, influx_hist.ts) AS first,
    (public.last(influx_hist.value, influx_hist.ts) - public.first(influx_hist.value, influx_hist.ts)) AS diff
   FROM public.influx_hist
  WHERE (influx_hist.ts >= COALESCE(_timescaledb_functions.to_timestamp(_timescaledb_functions.cagg_watermark(3)), '-infinity'::timestamp with time zone))
  GROUP BY (public.time_bucket('00:01:00'::interval, influx_hist.ts)), influx_hist.tag_name;


--
-- Name: influx_latest; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.influx_latest AS
 SELECT DISTINCT ON (tag_name) tag_name,
    value,
    ts
   FROM public.influx_hist
  ORDER BY tag_name, ts DESC;


--
-- Name: influx_op_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.influx_op_log (
    ts timestamp with time zone NOT NULL,
    state text NOT NULL
);


--
-- Name: influx_qc_rule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.influx_qc_rule (
    tag_name text NOT NULL,
    min_val double precision,
    max_val double precision,
    max_step double precision,
    max_gap_seconds integer DEFAULT 120,
    allow_negative boolean DEFAULT true,
    enabled boolean DEFAULT true,
    meta jsonb DEFAULT '{}'::jsonb,
    warn_min double precision,
    warn_max double precision,
    crit_min double precision,
    crit_max double precision,
    roc_max_per_min double precision,
    spike_zscore double precision,
    deadband_pct double precision
);


--
-- Name: influx_tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.influx_tag (
    key text NOT NULL,
    tag_id text,
    tag_name text NOT NULL,
    tag_type text NOT NULL,
    unit text,
    meta jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: pred_linreg_h15_w120; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pred_linreg_h15_w120 (
    ts timestamp with time zone NOT NULL,
    tag_name text NOT NULL,
    horizon interval NOT NULL,
    yhat double precision NOT NULL,
    pi_low double precision,
    pi_high double precision,
    model_id text NOT NULL,
    version text NOT NULL,
    features jsonb DEFAULT '{}'::jsonb
);


--
-- Name: pred_linreg_h5_w60; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pred_linreg_h5_w60 (
    ts timestamp with time zone NOT NULL,
    tag_name text NOT NULL,
    horizon interval NOT NULL,
    yhat double precision NOT NULL,
    pi_low double precision,
    pi_high double precision,
    model_id text NOT NULL,
    version text NOT NULL,
    features jsonb DEFAULT '{}'::jsonb
);


--
-- Name: tech_ind_10m_mv; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.tech_ind_10m_mv AS
 SELECT bucket,
    tag_name,
    avg,
    avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS sma_10,
    avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) AS sma_60,
    (avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) + ((2)::double precision * stddev_samp(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW))) AS bb_top,
    (avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) - ((2)::double precision * stddev_samp(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW))) AS bb_bot,
    (avg - lag(avg, 60) OVER (PARTITION BY tag_name ORDER BY bucket)) AS slope_60
   FROM public.influx_agg_10m;


--
-- Name: tech_ind_1d_mv; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.tech_ind_1d_mv AS
 SELECT bucket,
    tag_name,
    avg,
    avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS sma_10,
    avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) AS sma_60,
    (avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) + ((2)::double precision * stddev_samp(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW))) AS bb_top,
    (avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) - ((2)::double precision * stddev_samp(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW))) AS bb_bot,
    (avg - lag(avg, 60) OVER (PARTITION BY tag_name ORDER BY bucket)) AS slope_60
   FROM public.influx_agg_1d;


--
-- Name: tech_ind_1h_mv; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.tech_ind_1h_mv AS
 SELECT bucket,
    tag_name,
    avg,
    avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS sma_10,
    avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) AS sma_60,
    (avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) + ((2)::double precision * stddev_samp(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW))) AS bb_top,
    (avg(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) - ((2)::double precision * stddev_samp(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW))) AS bb_bot,
    (avg - lag(avg, 60) OVER (PARTITION BY tag_name ORDER BY bucket)) AS slope_60
   FROM public.influx_agg_1h;


--
-- Name: tech_ind_1m_mv; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.tech_ind_1m_mv AS
 SELECT bucket,
    tag_name,
    avg,
    avg(avg) OVER w10 AS sma_10,
    avg(avg) OVER w60 AS sma_60,
    (avg + ((2)::double precision * stddev_samp(avg) OVER w20)) AS bb_top,
    (avg - ((2)::double precision * stddev_samp(avg) OVER w20)) AS bb_bot,
    regr_slope(avg, (EXTRACT(epoch FROM bucket))::double precision) OVER w60 AS slope_60
   FROM public.influx_agg_1m
  WINDOW w10 AS (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 9 PRECEDING AND CURRENT ROW), w20 AS (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW), w60 AS (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 59 PRECEDING AND CURRENT ROW)
  WITH NO DATA;


--
-- Name: _hyper_2_10_chunk qc; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_10_chunk ALTER COLUMN qc SET DEFAULT 0;


--
-- Name: _hyper_2_10_chunk meta; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_10_chunk ALTER COLUMN meta SET DEFAULT '{}'::jsonb;


--
-- Name: _hyper_2_13_chunk qc; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_13_chunk ALTER COLUMN qc SET DEFAULT 0;


--
-- Name: _hyper_2_13_chunk meta; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_13_chunk ALTER COLUMN meta SET DEFAULT '{}'::jsonb;


--
-- Name: _hyper_2_16_chunk qc; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_16_chunk ALTER COLUMN qc SET DEFAULT 0;


--
-- Name: _hyper_2_16_chunk meta; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_16_chunk ALTER COLUMN meta SET DEFAULT '{}'::jsonb;


--
-- Name: _hyper_2_4_chunk qc; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_4_chunk ALTER COLUMN qc SET DEFAULT 0;


--
-- Name: _hyper_2_4_chunk meta; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_4_chunk ALTER COLUMN meta SET DEFAULT '{}'::jsonb;


--
-- Name: _hyper_8_9_chunk features; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_8_9_chunk ALTER COLUMN features SET DEFAULT '{}'::jsonb;


--
-- Name: _hyper_9_11_chunk context; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_9_11_chunk ALTER COLUMN context SET DEFAULT '{}'::jsonb;


--
-- Name: _hyper_9_14_chunk context; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_9_14_chunk ALTER COLUMN context SET DEFAULT '{}'::jsonb;


--
-- Name: _hyper_9_17_chunk context; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_9_17_chunk ALTER COLUMN context SET DEFAULT '{}'::jsonb;


--
-- Name: _hyper_9_7_chunk context; Type: DEFAULT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_9_7_chunk ALTER COLUMN context SET DEFAULT '{}'::jsonb;


--
-- Name: ai_conversations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_conversations ALTER COLUMN id SET DEFAULT nextval('public.ai_conversations_id_seq'::regclass);


--
-- Name: ai_knowledge_base id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_knowledge_base ALTER COLUMN id SET DEFAULT nextval('public.ai_knowledge_base_id_seq'::regclass);


--
-- Name: _hyper_2_10_chunk 10_11_influx_hist_pkey; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_10_chunk
    ADD CONSTRAINT "10_11_influx_hist_pkey" PRIMARY KEY (ts, tag_name);


--
-- Name: _hyper_9_11_chunk 11_12_anomalies_pkey; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_9_11_chunk
    ADD CONSTRAINT "11_12_anomalies_pkey" PRIMARY KEY (ts, tag_name);


--
-- Name: _hyper_2_13_chunk 13_14_influx_hist_pkey; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_13_chunk
    ADD CONSTRAINT "13_14_influx_hist_pkey" PRIMARY KEY (ts, tag_name);


--
-- Name: _hyper_9_14_chunk 14_15_anomalies_pkey; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_9_14_chunk
    ADD CONSTRAINT "14_15_anomalies_pkey" PRIMARY KEY (ts, tag_name);


--
-- Name: _hyper_2_16_chunk 16_17_influx_hist_pkey; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_16_chunk
    ADD CONSTRAINT "16_17_influx_hist_pkey" PRIMARY KEY (ts, tag_name);


--
-- Name: _hyper_9_17_chunk 17_18_anomalies_pkey; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_9_17_chunk
    ADD CONSTRAINT "17_18_anomalies_pkey" PRIMARY KEY (ts, tag_name);


--
-- Name: _hyper_2_4_chunk 4_6_influx_hist_pkey; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_4_chunk
    ADD CONSTRAINT "4_6_influx_hist_pkey" PRIMARY KEY (ts, tag_name);


--
-- Name: _hyper_9_7_chunk 7_7_anomalies_pkey; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_9_7_chunk
    ADD CONSTRAINT "7_7_anomalies_pkey" PRIMARY KEY (ts, tag_name);


--
-- Name: _hyper_8_9_chunk 9_9_predictions_pkey; Type: CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_8_9_chunk
    ADD CONSTRAINT "9_9_predictions_pkey" PRIMARY KEY (ts, tag_name, horizon, model_id, version);


--
-- Name: ai_conversations ai_conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_conversations
    ADD CONSTRAINT ai_conversations_pkey PRIMARY KEY (id);


--
-- Name: ai_knowledge_base ai_knowledge_base_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_knowledge_base
    ADD CONSTRAINT ai_knowledge_base_pkey PRIMARY KEY (id);


--
-- Name: anomalies anomalies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anomalies
    ADD CONSTRAINT anomalies_pkey PRIMARY KEY (ts, tag_name);


--
-- Name: influx_hist influx_hist_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.influx_hist
    ADD CONSTRAINT influx_hist_pkey PRIMARY KEY (ts, tag_name);


--
-- Name: influx_op_log influx_op_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.influx_op_log
    ADD CONSTRAINT influx_op_log_pkey PRIMARY KEY (ts);


--
-- Name: influx_qc_rule influx_qc_rule_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.influx_qc_rule
    ADD CONSTRAINT influx_qc_rule_pkey PRIMARY KEY (tag_name);


--
-- Name: influx_tag influx_tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.influx_tag
    ADD CONSTRAINT influx_tag_pkey PRIMARY KEY (key);


--
-- Name: influx_tag influx_tag_tag_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.influx_tag
    ADD CONSTRAINT influx_tag_tag_name_key UNIQUE (tag_name);


--
-- Name: pred_linreg_h15_w120 pred_linreg_h15_w120_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pred_linreg_h15_w120
    ADD CONSTRAINT pred_linreg_h15_w120_pkey PRIMARY KEY (ts, tag_name);


--
-- Name: pred_linreg_h5_w60 pred_linreg_h5_w60_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pred_linreg_h5_w60
    ADD CONSTRAINT pred_linreg_h5_w60_pkey PRIMARY KEY (ts, tag_name);


--
-- Name: predictions predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_pkey PRIMARY KEY (ts, tag_name, horizon, model_id, version);


--
-- Name: _hyper_10_12_chunk__materialized_hypertable_10_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_10_12_chunk__materialized_hypertable_10_bucket_idx ON _timescaledb_internal._hyper_10_12_chunk USING btree (bucket DESC);


--
-- Name: _hyper_10_12_chunk__materialized_hypertable_10_tag_name_bucket_; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_10_12_chunk__materialized_hypertable_10_tag_name_bucket_ ON _timescaledb_internal._hyper_10_12_chunk USING btree (tag_name, bucket DESC);


--
-- Name: _hyper_10_12_chunk_idx_agg1d_bucket_tag; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_10_12_chunk_idx_agg1d_bucket_tag ON _timescaledb_internal._hyper_10_12_chunk USING btree (bucket, tag_name);


--
-- Name: _hyper_2_10_chunk_idx_hist_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_10_chunk_idx_hist_tag_ts ON _timescaledb_internal._hyper_2_10_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_2_10_chunk_influx_hist_ts_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_10_chunk_influx_hist_ts_idx ON _timescaledb_internal._hyper_2_10_chunk USING btree (ts DESC);


--
-- Name: _hyper_2_10_chunk_ix_influx_hist_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_10_chunk_ix_influx_hist_tag_ts ON _timescaledb_internal._hyper_2_10_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_2_13_chunk_idx_hist_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_13_chunk_idx_hist_tag_ts ON _timescaledb_internal._hyper_2_13_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_2_13_chunk_influx_hist_ts_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_13_chunk_influx_hist_ts_idx ON _timescaledb_internal._hyper_2_13_chunk USING btree (ts DESC);


--
-- Name: _hyper_2_13_chunk_ix_influx_hist_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_13_chunk_ix_influx_hist_tag_ts ON _timescaledb_internal._hyper_2_13_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_2_16_chunk_idx_hist_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_16_chunk_idx_hist_tag_ts ON _timescaledb_internal._hyper_2_16_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_2_16_chunk_influx_hist_ts_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_16_chunk_influx_hist_ts_idx ON _timescaledb_internal._hyper_2_16_chunk USING btree (ts DESC);


--
-- Name: _hyper_2_16_chunk_ix_influx_hist_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_16_chunk_ix_influx_hist_tag_ts ON _timescaledb_internal._hyper_2_16_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_2_4_chunk_idx_hist_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_4_chunk_idx_hist_tag_ts ON _timescaledb_internal._hyper_2_4_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_2_4_chunk_influx_hist_ts_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_4_chunk_influx_hist_ts_idx ON _timescaledb_internal._hyper_2_4_chunk USING btree (ts DESC);


--
-- Name: _hyper_2_4_chunk_ix_influx_hist_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_2_4_chunk_ix_influx_hist_tag_ts ON _timescaledb_internal._hyper_2_4_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_3_2_chunk__materialized_hypertable_3_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_3_2_chunk__materialized_hypertable_3_bucket_idx ON _timescaledb_internal._hyper_3_2_chunk USING btree (bucket DESC);


--
-- Name: _hyper_3_2_chunk__materialized_hypertable_3_tag_name_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_3_2_chunk__materialized_hypertable_3_tag_name_bucket_idx ON _timescaledb_internal._hyper_3_2_chunk USING btree (tag_name, bucket DESC);


--
-- Name: _hyper_4_5_chunk__materialized_hypertable_4_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_4_5_chunk__materialized_hypertable_4_bucket_idx ON _timescaledb_internal._hyper_4_5_chunk USING btree (bucket DESC);


--
-- Name: _hyper_4_5_chunk__materialized_hypertable_4_tag_name_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_4_5_chunk__materialized_hypertable_4_tag_name_bucket_idx ON _timescaledb_internal._hyper_4_5_chunk USING btree (tag_name, bucket DESC);


--
-- Name: _hyper_5_6_chunk__materialized_hypertable_5_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_5_6_chunk__materialized_hypertable_5_bucket_idx ON _timescaledb_internal._hyper_5_6_chunk USING btree (bucket DESC);


--
-- Name: _hyper_5_6_chunk__materialized_hypertable_5_tag_name_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_5_6_chunk__materialized_hypertable_5_tag_name_bucket_idx ON _timescaledb_internal._hyper_5_6_chunk USING btree (tag_name, bucket DESC);


--
-- Name: _hyper_8_9_chunk_idx_pred_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_8_9_chunk_idx_pred_tag_ts ON _timescaledb_internal._hyper_8_9_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_8_9_chunk_predictions_ts_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_8_9_chunk_predictions_ts_idx ON _timescaledb_internal._hyper_8_9_chunk USING btree (ts DESC);


--
-- Name: _hyper_9_11_chunk_anomalies_tag_ts_desc; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_11_chunk_anomalies_tag_ts_desc ON _timescaledb_internal._hyper_9_11_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_9_11_chunk_anomalies_ts_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_11_chunk_anomalies_ts_idx ON _timescaledb_internal._hyper_9_11_chunk USING btree (ts DESC);


--
-- Name: _hyper_9_11_chunk_idx_anom_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_11_chunk_idx_anom_tag_ts ON _timescaledb_internal._hyper_9_11_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_9_14_chunk_anomalies_tag_ts_desc; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_14_chunk_anomalies_tag_ts_desc ON _timescaledb_internal._hyper_9_14_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_9_14_chunk_anomalies_ts_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_14_chunk_anomalies_ts_idx ON _timescaledb_internal._hyper_9_14_chunk USING btree (ts DESC);


--
-- Name: _hyper_9_14_chunk_idx_anom_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_14_chunk_idx_anom_tag_ts ON _timescaledb_internal._hyper_9_14_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_9_17_chunk_anomalies_tag_ts_desc; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_17_chunk_anomalies_tag_ts_desc ON _timescaledb_internal._hyper_9_17_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_9_17_chunk_anomalies_ts_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_17_chunk_anomalies_ts_idx ON _timescaledb_internal._hyper_9_17_chunk USING btree (ts DESC);


--
-- Name: _hyper_9_17_chunk_idx_anom_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_17_chunk_idx_anom_tag_ts ON _timescaledb_internal._hyper_9_17_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_9_7_chunk_anomalies_tag_ts_desc; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_7_chunk_anomalies_tag_ts_desc ON _timescaledb_internal._hyper_9_7_chunk USING btree (tag_name, ts DESC);


--
-- Name: _hyper_9_7_chunk_anomalies_ts_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_7_chunk_anomalies_ts_idx ON _timescaledb_internal._hyper_9_7_chunk USING btree (ts DESC);


--
-- Name: _hyper_9_7_chunk_idx_anom_tag_ts; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _hyper_9_7_chunk_idx_anom_tag_ts ON _timescaledb_internal._hyper_9_7_chunk USING btree (tag_name, ts DESC);


--
-- Name: _materialized_hypertable_10_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _materialized_hypertable_10_bucket_idx ON _timescaledb_internal._materialized_hypertable_10 USING btree (bucket DESC);


--
-- Name: _materialized_hypertable_10_tag_name_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _materialized_hypertable_10_tag_name_bucket_idx ON _timescaledb_internal._materialized_hypertable_10 USING btree (tag_name, bucket DESC);


--
-- Name: _materialized_hypertable_3_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _materialized_hypertable_3_bucket_idx ON _timescaledb_internal._materialized_hypertable_3 USING btree (bucket DESC);


--
-- Name: _materialized_hypertable_3_tag_name_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _materialized_hypertable_3_tag_name_bucket_idx ON _timescaledb_internal._materialized_hypertable_3 USING btree (tag_name, bucket DESC);


--
-- Name: _materialized_hypertable_4_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _materialized_hypertable_4_bucket_idx ON _timescaledb_internal._materialized_hypertable_4 USING btree (bucket DESC);


--
-- Name: _materialized_hypertable_4_tag_name_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _materialized_hypertable_4_tag_name_bucket_idx ON _timescaledb_internal._materialized_hypertable_4 USING btree (tag_name, bucket DESC);


--
-- Name: _materialized_hypertable_5_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _materialized_hypertable_5_bucket_idx ON _timescaledb_internal._materialized_hypertable_5 USING btree (bucket DESC);


--
-- Name: _materialized_hypertable_5_tag_name_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _materialized_hypertable_5_tag_name_bucket_idx ON _timescaledb_internal._materialized_hypertable_5 USING btree (tag_name, bucket DESC);


--
-- Name: _materialized_hypertable_7_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _materialized_hypertable_7_bucket_idx ON _timescaledb_internal._materialized_hypertable_7 USING btree (bucket DESC);


--
-- Name: _materialized_hypertable_7_tag_name_bucket_idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX _materialized_hypertable_7_tag_name_bucket_idx ON _timescaledb_internal._materialized_hypertable_7 USING btree (tag_name, bucket DESC);


--
-- Name: compress_hyper_6_15_chunk_tag_name__ts_meta_min_1__ts_meta__idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX compress_hyper_6_15_chunk_tag_name__ts_meta_min_1__ts_meta__idx ON _timescaledb_internal.compress_hyper_6_15_chunk USING btree (tag_name, _ts_meta_min_1 DESC, _ts_meta_max_1 DESC);


--
-- Name: compress_hyper_6_18_chunk_tag_name__ts_meta_min_1__ts_meta__idx; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX compress_hyper_6_18_chunk_tag_name__ts_meta_min_1__ts_meta__idx ON _timescaledb_internal.compress_hyper_6_18_chunk USING btree (tag_name, _ts_meta_min_1 DESC, _ts_meta_max_1 DESC);


--
-- Name: idx_agg1d_bucket_tag; Type: INDEX; Schema: _timescaledb_internal; Owner: -
--

CREATE INDEX idx_agg1d_bucket_tag ON _timescaledb_internal._materialized_hypertable_10 USING btree (bucket, tag_name);


--
-- Name: anomalies_tag_ts_desc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX anomalies_tag_ts_desc ON public.anomalies USING btree (tag_name, ts DESC);


--
-- Name: anomalies_ts_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX anomalies_ts_idx ON public.anomalies USING btree (ts DESC);


--
-- Name: idx_anom_tag_ts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_anom_tag_ts ON public.anomalies USING btree (tag_name, ts DESC);


--
-- Name: idx_conversations_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_session ON public.ai_conversations USING btree (session_id);


--
-- Name: idx_hist_tag_ts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hist_tag_ts ON public.influx_hist USING btree (tag_name, ts DESC);


--
-- Name: idx_knowledge_content_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_knowledge_content_search ON public.ai_knowledge_base USING gin (to_tsvector('english'::regconfig, content));


--
-- Name: idx_knowledge_content_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_knowledge_content_type ON public.ai_knowledge_base USING btree (content_type);


--
-- Name: idx_knowledge_metadata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_knowledge_metadata ON public.ai_knowledge_base USING gin (metadata);


--
-- Name: idx_pred_tag_ts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pred_tag_ts ON public.predictions USING btree (tag_name, ts DESC);


--
-- Name: influx_hist_ts_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX influx_hist_ts_idx ON public.influx_hist USING btree (ts DESC);


--
-- Name: ix_influx_hist_tag_ts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_influx_hist_tag_ts ON public.influx_hist USING btree (tag_name, ts DESC);


--
-- Name: pred_linreg_h15_w120_tag_ts_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX pred_linreg_h15_w120_tag_ts_idx ON public.pred_linreg_h15_w120 USING btree (tag_name, ts DESC);


--
-- Name: pred_linreg_h5_w60_tag_ts_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX pred_linreg_h5_w60_tag_ts_idx ON public.pred_linreg_h5_w60 USING btree (tag_name, ts DESC);


--
-- Name: predictions_ts_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX predictions_ts_idx ON public.predictions USING btree (ts DESC);


--
-- Name: uq_influx_tag_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_influx_tag_id ON public.influx_tag USING btree (tag_id);


--
-- Name: uq_influx_tag_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_influx_tag_name ON public.influx_tag USING btree (tag_name);


--
-- Name: uq_tech1m_tag_bucket; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_tech1m_tag_bucket ON public.tech_ind_1m_mv USING btree (tag_name, bucket);


--
-- Name: _hyper_2_10_chunk ts_cagg_invalidation_trigger; Type: TRIGGER; Schema: _timescaledb_internal; Owner: -
--

CREATE TRIGGER ts_cagg_invalidation_trigger AFTER INSERT OR DELETE OR UPDATE ON _timescaledb_internal._hyper_2_10_chunk FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.continuous_agg_invalidation_trigger('2');


--
-- Name: _hyper_2_13_chunk ts_cagg_invalidation_trigger; Type: TRIGGER; Schema: _timescaledb_internal; Owner: -
--

CREATE TRIGGER ts_cagg_invalidation_trigger AFTER INSERT OR DELETE OR UPDATE ON _timescaledb_internal._hyper_2_13_chunk FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.continuous_agg_invalidation_trigger('2');


--
-- Name: _hyper_2_16_chunk ts_cagg_invalidation_trigger; Type: TRIGGER; Schema: _timescaledb_internal; Owner: -
--

CREATE TRIGGER ts_cagg_invalidation_trigger AFTER INSERT OR DELETE OR UPDATE ON _timescaledb_internal._hyper_2_16_chunk FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.continuous_agg_invalidation_trigger('2');


--
-- Name: _hyper_2_4_chunk ts_cagg_invalidation_trigger; Type: TRIGGER; Schema: _timescaledb_internal; Owner: -
--

CREATE TRIGGER ts_cagg_invalidation_trigger AFTER INSERT OR DELETE OR UPDATE ON _timescaledb_internal._hyper_2_4_chunk FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.continuous_agg_invalidation_trigger('2');


--
-- Name: _compressed_hypertable_6 ts_insert_blocker; Type: TRIGGER; Schema: _timescaledb_internal; Owner: -
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON _timescaledb_internal._compressed_hypertable_6 FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- Name: _materialized_hypertable_10 ts_insert_blocker; Type: TRIGGER; Schema: _timescaledb_internal; Owner: -
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON _timescaledb_internal._materialized_hypertable_10 FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- Name: _materialized_hypertable_3 ts_insert_blocker; Type: TRIGGER; Schema: _timescaledb_internal; Owner: -
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON _timescaledb_internal._materialized_hypertable_3 FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- Name: _materialized_hypertable_4 ts_insert_blocker; Type: TRIGGER; Schema: _timescaledb_internal; Owner: -
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON _timescaledb_internal._materialized_hypertable_4 FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- Name: _materialized_hypertable_5 ts_insert_blocker; Type: TRIGGER; Schema: _timescaledb_internal; Owner: -
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON _timescaledb_internal._materialized_hypertable_5 FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- Name: _materialized_hypertable_7 ts_insert_blocker; Type: TRIGGER; Schema: _timescaledb_internal; Owner: -
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON _timescaledb_internal._materialized_hypertable_7 FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- Name: influx_hist ts_cagg_invalidation_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER ts_cagg_invalidation_trigger AFTER INSERT OR DELETE OR UPDATE ON public.influx_hist FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.continuous_agg_invalidation_trigger('2');


--
-- Name: anomalies ts_insert_blocker; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.anomalies FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- Name: influx_hist ts_insert_blocker; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.influx_hist FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- Name: predictions ts_insert_blocker; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER ts_insert_blocker BEFORE INSERT ON public.predictions FOR EACH ROW EXECUTE FUNCTION _timescaledb_functions.insert_blocker();


--
-- Name: _hyper_2_10_chunk 10_10_fk_hist_tag; Type: FK CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_10_chunk
    ADD CONSTRAINT "10_10_fk_hist_tag" FOREIGN KEY (tag_name) REFERENCES public.influx_tag(tag_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: _hyper_2_13_chunk 13_13_fk_hist_tag; Type: FK CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_13_chunk
    ADD CONSTRAINT "13_13_fk_hist_tag" FOREIGN KEY (tag_name) REFERENCES public.influx_tag(tag_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: _hyper_2_16_chunk 16_16_fk_hist_tag; Type: FK CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_16_chunk
    ADD CONSTRAINT "16_16_fk_hist_tag" FOREIGN KEY (tag_name) REFERENCES public.influx_tag(tag_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: _hyper_2_4_chunk 4_5_fk_hist_tag; Type: FK CONSTRAINT; Schema: _timescaledb_internal; Owner: -
--

ALTER TABLE ONLY _timescaledb_internal._hyper_2_4_chunk
    ADD CONSTRAINT "4_5_fk_hist_tag" FOREIGN KEY (tag_name) REFERENCES public.influx_tag(tag_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: influx_hist fk_hist_tag; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.influx_hist
    ADD CONSTRAINT fk_hist_tag FOREIGN KEY (tag_name) REFERENCES public.influx_tag(tag_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: influx_qc_rule influx_qc_rule_tag_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.influx_qc_rule
    ADD CONSTRAINT influx_qc_rule_tag_name_fkey FOREIGN KEY (tag_name) REFERENCES public.influx_tag(tag_name);


--
-- PostgreSQL database dump complete
--

\unrestrict SszDdotXNQoqxZGmdfe11cdIccjUa2pcgrnWjsxcsIBldeZ8zULNsFrlidGqg5e

