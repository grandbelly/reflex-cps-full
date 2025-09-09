## TimescaleDB Aggregation & Refresh Policy

### Overview
- Source: `public.influx_hist` (hypertable).
- Continuous aggregates: `influx_agg_1m`, `influx_agg_5m`, `influx_agg_10m`, `influx_agg_1h`, `influx_agg_1d`.
- Each CAGG is computed directly from `influx_hist` for accuracy and simplicity (no chained rollups).
- First/last are computed without toolkit using ordered `array_agg`.

### Why Direct From Source (Not Chained)
- Correct math: averages need weighting; min/max and first/last require timestamp-aware merge. Direct (source → every bucket) avoids rollup errors.
- Freshness: each CAGG reflects latest source promptly.
- Simplicity: one policy per CAGG; fewer dependencies.

### Refresh Policies (Bucket-Aligned)
- 1m: schedule 1 minute, end_offset 1 minute, start_offset 2 hours.
- 5m: schedule 5 minutes, end_offset 5 minutes, start_offset 1 day.
- 10m: schedule 10 minutes, end_offset 10 minutes, start_offset 1 day.
- 1h: schedule 1 hour, end_offset 1 hour, start_offset 7 days.
- 1d: schedule 1 day, end_offset 1 day, start_offset 30 days.
- Principle: schedule == bucket, end_offset == bucket. Only closed buckets refresh, ensuring consistency.

### Data Lifecycle & Safety
- Policies change background job timing, not data. CAGG data is preserved unless a view is dropped.
- Source retention: `add_retention_policy('influx_hist', '365 days')`. Aggregates remain even if older source rows are pruned.

### Timeline Simulation
- New points arrive in `influx_hist` at 10:06.
- 1m CAGG runs every minute; with end_offset=1m it materializes up to 10:05.
- 5m CAGG runs at 10:05/10:10…; materializes [10:00–10:05), [10:05–10:10)…
- 10m CAGG runs at 10:10…; materializes the previous 10‑minute bucket.
- 1h CAGG runs hourly; 1d runs daily. Each updates the previous closed bucket.

### Verification
- List CAGGs: `SELECT view_name FROM timescaledb_information.continuous_aggregates ORDER BY 1;`
- Inspect policy jobs: `SELECT job_id, schedule_interval FROM timescaledb_information.jobs WHERE proc_name='policy_refresh_continuous_aggregate';`
- Manual backfill: `SELECT refresh_continuous_aggregate('public.influx_agg_1m', now()-interval '30 minutes', now());`

### Operations
- Change policy safely:
  - `SELECT remove_continuous_aggregate_policy('<view>');`
  - `SELECT add_continuous_aggregate_policy('<view>', start_offset=>'..', end_offset=>'..', schedule_interval=>'..');`
- Do not drop CAGG views unless you intend to delete their data.
