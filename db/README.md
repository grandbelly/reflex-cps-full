## TimescaleDB (with pgvector) — Declarative Setup

This folder provides a fully reproducible, Docker-based TimescaleDB setup with pgvector (and optional PL/Python). Initialization is fully declarative via entrypoint scripts; no manual docker exec steps are required.

### Files
- `Dockerfile.timescaledb`: Based on `timescale/timescaledb:latest-pg16`. Installs `pgvector` (apt or source fallback) and `plpython3u` when available; copies `postgresql.conf` and init SQL.
- `docker-compose.timescaledb-only.yml`: Single service with a named volume `timescale_data` to avoid Windows bind-mount permission issues.
- `init-extensions.sql`: Creates `timescaledb`, `vector`, and optional extensions if present.
- `init-schema.sql`: Core tables/indexes (`public.influx_hist`, `public.influx_tag`, `public.influx_qc_rule`).
- `init-timescale.sql`: Converts to hypertable, creates continuous aggregates (1m/5m/1h/1d) and views, adds retention policy.

### Quick Start
1) Fresh start (declarative)
- `docker compose -f db/docker-compose.timescaledb-only.yml down -v`
- `docker compose -f db/docker-compose.timescaledb-only.yml up -d --build`

2) Connection (host)
- `postgresql://ecoanp_user:ecoanp_password@localhost:5432/ecoanp?sslmode=disable`

### Validate
- Extensions: `docker exec ecoanp_timescaledb psql -U ecoanp_user -d ecoanp -c "SELECT extname FROM pg_extension"`
- Objects: `\d+ influx_hist`, `SELECT matviewname FROM pg_matviews WHERE schemaname='public'`.
- pgvector smoke test:
  - `CREATE TABLE items (id bigserial primary key, embedding vector(3));`
  - `INSERT INTO items (embedding) VALUES ('[1,2,3]');`
  - `SELECT id FROM items ORDER BY embedding <-> '[1,2,3]'::vector LIMIT 1;`

### Notes
- License: `postgresql.conf` sets `timescaledb.license = 'timescale'` to enable free community features (retention, continuous aggregates).
- Persistence: Uses Docker named volume `timescale_data`. Reset by composing with `-v` as shown.
- Windows: Named volume avoids file-permission issues from bind mounts.

### Dagster Integration
- Set `TS_DSN` to the DSN above. The sample compose `dagster/simple-dagster.yml` loads `../.env` and forwards `TS_DSN` to assets.
- Influx→Timescale assets: `dagster/assets/influx_timescale_assets.py` use `INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_RAW_BUCKET`, `INFLUX_META_BUCKET`.

Everything is rebuilt via Dockerfile + Compose + init SQL. No manual container edits are required.
