-- =====================================================
-- TimescaleDB 하이퍼테이블 및 연속 집계/뷰 생성 (toolkit 미의존)
-- =====================================================

-- 1) 하이퍼테이블 변환
SELECT create_hypertable('public.influx_hist', 'ts', if_not_exists => TRUE);

-- 2) 보조 인덱스/정책
CREATE INDEX IF NOT EXISTS idx_influx_hist_time ON public.influx_hist (ts DESC);
SELECT add_retention_policy('public.influx_hist', INTERVAL '365 days', if_not_exists => TRUE);

-- 3) 연속 집계: last/first는 array_agg로 대체 (toolkit 불필요)
CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_1m
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 minute', ts) AS bucket,
    tag_name,
    COUNT(*) AS n,
    AVG(value) AS avg,
    SUM(value) AS sum,
    MIN(value) AS min,
    MAX(value) AS max,
    (array_agg(value ORDER BY ts DESC))[1] AS last,
    (array_agg(value ORDER BY ts ASC))[1]  AS first,
    (array_agg(value ORDER BY ts DESC))[1] - (array_agg(value ORDER BY ts ASC))[1] AS diff
FROM public.influx_hist
GROUP BY bucket, tag_name
WITH NO DATA;

CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_5m
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('5 minutes', ts) AS bucket,
    tag_name,
    COUNT(*) AS n,
    AVG(value) AS avg,
    SUM(value) AS sum,
    MIN(value) AS min,
    MAX(value) AS max,
    (array_agg(value ORDER BY ts DESC))[1] AS last,
    (array_agg(value ORDER BY ts ASC))[1]  AS first,
    (array_agg(value ORDER BY ts DESC))[1] - (array_agg(value ORDER BY ts ASC))[1] AS diff
FROM public.influx_hist
GROUP BY bucket, tag_name
WITH NO DATA;

CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_10m
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('10 minutes', ts) AS bucket,
    tag_name,
    COUNT(*) AS n,
    AVG(value) AS avg,
    SUM(value) AS sum,
    MIN(value) AS min,
    MAX(value) AS max,
    (array_agg(value ORDER BY ts DESC))[1] AS last,
    (array_agg(value ORDER BY ts ASC))[1]  AS first,
    (array_agg(value ORDER BY ts DESC))[1] - (array_agg(value ORDER BY ts ASC))[1] AS diff
FROM public.influx_hist
GROUP BY bucket, tag_name
WITH NO DATA;

CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_1h
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', ts) AS bucket,
    tag_name,
    COUNT(*) AS n,
    AVG(value) AS avg,
    SUM(value) AS sum,
    MIN(value) AS min,
    MAX(value) AS max,
    (array_agg(value ORDER BY ts DESC))[1] AS last,
    (array_agg(value ORDER BY ts ASC))[1]  AS first,
    (array_agg(value ORDER BY ts DESC))[1] - (array_agg(value ORDER BY ts ASC))[1] AS diff
FROM public.influx_hist
GROUP BY bucket, tag_name
WITH NO DATA;

CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_1d
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', ts) AS bucket,
    tag_name,
    COUNT(*) AS n,
    AVG(value) AS avg,
    SUM(value) AS sum,
    MIN(value) AS min,
    MAX(value) AS max,
    (array_agg(value ORDER BY ts DESC))[1] AS last,
    (array_agg(value ORDER BY ts ASC))[1]  AS first,
    (array_agg(value ORDER BY ts DESC))[1] - (array_agg(value ORDER BY ts ASC))[1] AS diff
FROM public.influx_hist
GROUP BY bucket, tag_name
WITH NO DATA;

-- 4) 최신값 및 집계 뷰 (사용처와 동일 명칭)
CREATE OR REPLACE VIEW public.influx_latest AS
SELECT DISTINCT ON (tag_name)
    tag_name,
    value,
    ts,
    qc,
    meta
FROM public.influx_hist
ORDER BY tag_name, ts DESC;

CREATE OR REPLACE VIEW public.influx_hourly_stats AS
SELECT 
    time_bucket('1 hour', ts) AS bucket,
    tag_name,
    COUNT(*) as readings_count,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    STDDEV(value) as stddev_value,
    AVG(qc) as avg_qc
FROM public.influx_hist
GROUP BY bucket, tag_name
ORDER BY bucket DESC, tag_name;

CREATE OR REPLACE VIEW public.influx_daily_stats AS
SELECT 
    time_bucket('1 day', ts) AS bucket,
    tag_name,
    COUNT(*) as readings_count,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    STDDEV(value) as stddev_value,
    AVG(qc) as avg_qc
FROM public.influx_hist
GROUP BY bucket, tag_name
ORDER BY bucket DESC, tag_name;

CREATE OR REPLACE VIEW public.influx_latest_status AS
SELECT DISTINCT ON (tag_name)
    tag_name,
    value as latest_value,
    ts as latest_reading,
    qc as latest_qc,
    meta
FROM public.influx_hist
ORDER BY tag_name, ts DESC;

-- 5) 연속 집계 새로고침 정책
-- Align policy to bucket size (schedule = bucket, end_offset = bucket)
SELECT add_continuous_aggregate_policy('public.influx_agg_1m',
    start_offset => INTERVAL '2 hours',
    end_offset   => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute');

SELECT add_continuous_aggregate_policy('public.influx_agg_5m',
    start_offset => INTERVAL '1 day',
    end_offset   => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes');

SELECT add_continuous_aggregate_policy('public.influx_agg_10m',
    start_offset => INTERVAL '1 day',
    end_offset   => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '10 minutes');

SELECT add_continuous_aggregate_policy('public.influx_agg_1h',
    start_offset => INTERVAL '7 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('public.influx_agg_1d',
    start_offset => INTERVAL '30 days',
    end_offset   => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

-- 6) 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ 하이퍼테이블/집계/뷰 초기화 완료 (toolkit 미의존)';
END $$;

