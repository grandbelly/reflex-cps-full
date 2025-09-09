import os
import sys
import json
from datetime import datetime, timedelta
import psycopg


def get_dsn() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    return os.getenv(
        "TS_DSN",
        "postgresql://ecoanp_user:ecoanp_password@localhost:5432/ecoanp",
    )


def run():
    dsn = get_dsn()
    now = datetime.utcnow()
    results = {"dsn": dsn, "steps": [], "ok": True}

    def step(name, fn):
        entry = {"name": name, "ok": False}
        try:
            entry.update(fn())
            entry["ok"] = True
        except Exception as e:
            entry["error"] = str(e)
            results["ok"] = False
        results["steps"].append(entry)

    with psycopg.connect(dsn) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            # 1) Extensions present
            def check_ext():
                cur.execute("SELECT extname FROM pg_extension ORDER BY 1")
                exts = [r[0] for r in cur.fetchall()]
                assert "timescaledb" in exts, "timescaledb extension missing"
                assert "vector" in exts, "pgvector extension missing"
                return {"extensions": exts}

            step("extensions", check_ext); conn.commit()

            # 2) Create test rows in influx_hist for a temp tag
            tag = "__smoke_tag__"
            start = now - timedelta(minutes=5)
            times = [start + timedelta(minutes=i) for i in range(6)]

            def seed_hist():
                records = [
                    (t, tag, float(i), 0, json.dumps({"src": "smoke"}))
                    for i, t in enumerate(times)
                ]
                for r in records:
                    cur.execute(
                        """
                        INSERT INTO public.influx_hist (ts, tag_name, value, qc, meta)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (ts, tag_name) DO UPDATE SET value=EXCLUDED.value
                        """,
                        r,
                    )
                return {"inserted": len(records), "tag": tag}

            try:
                step("seed_influx_hist", seed_hist)
                conn.commit()
            except Exception:
                conn.rollback(); raise

            # 3) Manual refresh CAGGs in test window (ignore failures if not needed)
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
                        # best-effort; policies will catch up
                        pass
                return {"refreshed": refreshed}

            try:
                step("refresh_caggs", refresh_caggs)
                conn.commit()
            except Exception:
                conn.rollback()

            # 4) Query matview + views for the tag
            def query_mv_and_views():
                cur.execute(
                    "SELECT count(*) FROM public.influx_agg_1m WHERE tag_name=%s AND bucket>= now() - interval '10 minutes'",
                    (tag,),
                )
                mv_cnt = cur.fetchone()[0]
                cur.execute(
                    "SELECT tag_name, latest_value FROM public.influx_latest_status WHERE tag_name=%s",
                    (tag,),
                )
                latest = cur.fetchall()
                return {"mv_1m_rows": int(mv_cnt), "latest_rows": len(latest)}

            step("query_views", query_mv_and_views); conn.commit()

            # 5) pgvector smoke
            def vector_smoke():
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS vec_smoke (id bigserial primary key, embedding vector(3))"
                )
                cur.execute("TRUNCATE vec_smoke")
                cur.execute("INSERT INTO vec_smoke (embedding) VALUES ('[1,2,3]'), ('[2,2,2]')")
                cur.execute(
                    "SELECT id, embedding <-> '[1,2,3]'::vector AS dist FROM vec_smoke ORDER BY dist ASC LIMIT 1"
                )
                row = cur.fetchone()
                return {"nearest_id": int(row[0]), "dist": float(row[1])}

            try:
                step("pgvector", vector_smoke)
                conn.commit()
            except Exception:
                conn.rollback(); raise

    print(json.dumps(results, ensure_ascii=False, indent=2))
    sys.exit(0 if results["ok"] else 1)


if __name__ == "__main__":
    run()
