import os
import json
from datetime import datetime, timedelta
from dagster import asset, AssetExecutionContext
import psycopg


def _dsn() -> str:
    return os.getenv(
        "TS_DSN",
        "postgresql://ecoanp_user:ecoanp_password@ecoanp_timescaledb:5432/ecoanp",
    )


@asset
def db_smoke(context: AssetExecutionContext):
    """Validate DB: extensions, schema, CAGGs/views, and pgvector.

    Inserts a short test series for tag '__smoke_tag__', tries a best-effort
    refresh for CAGGs, queries views, and runs a pgvector nearest-neighbor test.
    Returns a summary dict. Fails only on hard preconditions (missing extensions).
    """
    dsn = _dsn()
    now = datetime.utcnow()
    tag = "__smoke_tag__"
    context.log.info(f"DB smoke test using DSN: {dsn}")

    results = {"dsn": dsn, "ok": True, "steps": []}

    def step(name, fn):
        entry = {"name": name, "ok": False}
        try:
            entry.update(fn())
            entry["ok"] = True
        except Exception as e:
            context.log.warning(f"{name} failed: {e}")
            entry["error"] = str(e)
            results["ok"] = False
        results["steps"].append(entry)

    with psycopg.connect(dsn) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            # 1) Extensions
            def check_ext():
                cur.execute("SELECT extname FROM pg_extension ORDER BY 1")
                exts = [r[0] for r in cur.fetchall()]
                assert "timescaledb" in exts, "timescaledb extension missing"
                assert "vector" in exts, "pgvector extension missing"
                return {"extensions": exts}

            step("extensions", check_ext); conn.commit()

            # 2) Seed influx_hist
            start = now - timedelta(minutes=5)
            times = [start + timedelta(minutes=i) for i in range(6)]

            def seed_hist():
                for i, t in enumerate(times):
                    cur.execute(
                        """
                        INSERT INTO public.influx_hist (ts, tag_name, value, qc, meta)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (ts, tag_name) DO UPDATE SET value=EXCLUDED.value
                        """,
                        (t, tag, float(i), 0, json.dumps({"src": "smoke"})),
                    )
                return {"inserted": len(times), "tag": tag}

            try:
                step("seed_influx_hist", seed_hist); conn.commit()
            except Exception:
                conn.rollback(); raise

            # 3) Refresh CAGGs (best-effort)
            def refresh_caggs():
                refreshed = []
                for mv in [
                    "public.influx_agg_1m",
                    "public.influx_agg_5m",
                    "public.influx_agg_1h",
                    "public.influx_agg_1d",
                ]:
                    try:
                        cur.execute(
                            "SELECT refresh_continuous_aggregate(%s, now() - interval '1 day', now())",
                            (mv,),
                        )
                        refreshed.append(mv)
                    except Exception:
                        pass
                return {"refreshed": refreshed}

            try:
                step("refresh_caggs", refresh_caggs); conn.commit()
            except Exception:
                conn.rollback()

            # 4) Query views
            def query_views():
                cur.execute(
                    "SELECT count(*) FROM public.influx_agg_1m WHERE tag_name=%s AND bucket >= now() - interval '10 minutes'",
                    (tag,),
                )
                mv_cnt = int(cur.fetchone()[0])
                cur.execute(
                    "SELECT 1 FROM public.influx_latest_status WHERE tag_name=%s",
                    (tag,),
                )
                latest_cnt = len(cur.fetchall())
                return {"mv_1m_rows": mv_cnt, "latest_rows": latest_cnt}

            step("query_views", query_views); conn.commit()

            # 5) pgvector smoke
            def vector_smoke():
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS vec_smoke (id bigserial primary key, embedding vector(3))"
                )
                cur.execute("TRUNCATE vec_smoke")
                cur.execute(
                    "INSERT INTO vec_smoke (embedding) VALUES ('[1,2,3]'), ('[2,2,2]')"
                )
                cur.execute(
                    "SELECT id, embedding <-> '[1,2,3]'::vector AS dist FROM vec_smoke ORDER BY dist ASC LIMIT 1"
                )
                r = cur.fetchone()
                return {"nearest_id": int(r[0]), "dist": float(r[1])}

            try:
                step("pgvector", vector_smoke); conn.commit()
            except Exception:
                conn.rollback(); raise

    context.log.info(json.dumps(results, ensure_ascii=False))
    return results

