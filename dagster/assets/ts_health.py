from dagster import asset, AssetExecutionContext
import os
import json
import psycopg


def _dsn() -> str:
    return os.getenv(
        "TS_DSN",
        "postgresql://ecoanp_user:ecoanp_password@ecoanp_timescaledb:5432/ecoanp",
    )


@asset
def ts_health(context: AssetExecutionContext):
    """Smoke-test Timescale + pgvector: extensions, simple vector query."""
    dsn = _dsn()
    context.log.info(f"Connecting to TimescaleDB: {dsn}")

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            # Extensions
            cur.execute("SELECT extname FROM pg_extension ORDER BY 1")
            exts = [r[0] for r in cur.fetchall()]

            # Vector create/insert/query
            cur.execute(
                "CREATE TABLE IF NOT EXISTS dagster_vec (id bigserial primary key, embedding vector(3))"
            )
            cur.execute("TRUNCATE dagster_vec")
            cur.execute("INSERT INTO dagster_vec (embedding) VALUES ('[1,2,3]'), ('[0,0,0]')")
            cur.execute(
                "SELECT id, embedding <-> '[1,2,3]'::vector AS dist FROM dagster_vec ORDER BY dist ASC LIMIT 1"
            )
            top = cur.fetchone()

    result = {
        "extensions": exts,
        "vector_query_top": {"id": top[0], "dist": float(top[1])},
        "ok": ("timescaledb" in exts and "vector" in exts and top[1] == 0.0),
    }
    context.log.info(json.dumps(result, ensure_ascii=False))
    return result

