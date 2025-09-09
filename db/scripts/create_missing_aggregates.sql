-- ============================================
-- 로컬 TimescaleDB 누락 기능 구현 스크립트
-- 작성일: 2025-09-05
-- 용도: 리모트 DB와 동일한 기능 구현
-- ============================================

-- 1. 10분 연속 집계 생성
CREATE MATERIALIZED VIEW IF NOT EXISTS influx_agg_10m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('10 minutes', ts) AS bucket,
    tag_name,
    COUNT(*) AS n,
    AVG(value) AS avg,
    SUM(value) AS sum,
    MIN(value) AS min,
    MAX(value) AS max,
    LAST(value, ts) AS last,
    FIRST(value, ts) AS first,
    LAST(value, ts) - FIRST(value, ts) AS diff
FROM influx_hist
GROUP BY bucket, tag_name
WITH NO DATA;

-- 10분 집계 새로고침 정책
SELECT add_continuous_aggregate_policy('influx_agg_10m',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '0 minutes',
    schedule_interval => INTERVAL '10 minutes');

-- 2. 1시간 연속 집계 생성
CREATE MATERIALIZED VIEW IF NOT EXISTS influx_agg_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', ts) AS bucket,
    tag_name,
    COUNT(*) AS n,
    AVG(value) AS avg,
    SUM(value) AS sum,
    MIN(value) AS min,
    MAX(value) AS max,
    LAST(value, ts) AS last,
    FIRST(value, ts) AS first,
    LAST(value, ts) - FIRST(value, ts) AS diff
FROM influx_hist
GROUP BY bucket, tag_name
WITH NO DATA;

-- 1시간 집계 새로고침 정책
SELECT add_continuous_aggregate_policy('influx_agg_1h',
    start_offset => INTERVAL '24 hours',
    end_offset => INTERVAL '0 minutes',
    schedule_interval => INTERVAL '1 hour');

-- 3. 통계 기능 뷰 (5분)
CREATE OR REPLACE VIEW features_5m AS
SELECT
    time_bucket('5 minutes', ts) AS bucket,
    tag_name,
    COUNT(*) AS n,
    AVG(value) AS mean,
    STDDEV(value) AS std,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY value) AS q25,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY value) AS median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY value) AS q75,
    MIN(value) AS min,
    MAX(value) AS max,
    MAX(value) - MIN(value) AS range,
    -- 추가 통계
    VARIANCE(value) AS variance,
    MODE() WITHIN GROUP (ORDER BY value) AS mode,
    -- 시계열 특성
    FIRST(value, ts) AS first_value,
    LAST(value, ts) AS last_value,
    LAST(value, ts) - FIRST(value, ts) AS change
FROM influx_hist
GROUP BY bucket, tag_name;

-- 4. 통계 기능 뷰 (1시간)
CREATE OR REPLACE VIEW features_1h AS
SELECT
    time_bucket('1 hour', ts) AS bucket,
    tag_name,
    COUNT(*) AS n,
    AVG(value) AS mean,
    STDDEV(value) AS std,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY value) AS q25,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY value) AS median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY value) AS q75,
    MIN(value) AS min,
    MAX(value) AS max,
    MAX(value) - MIN(value) AS range,
    -- 추가 통계
    VARIANCE(value) AS variance,
    MODE() WITHIN GROUP (ORDER BY value) AS mode,
    -- 시계열 특성
    FIRST(value, ts) AS first_value,
    LAST(value, ts) AS last_value,
    LAST(value, ts) - FIRST(value, ts) AS change
FROM influx_hist
GROUP BY bucket, tag_name;

-- 5. 1분 기술 지표 Materialized View
CREATE MATERIALIZED VIEW IF NOT EXISTS tech_ind_1m_mv AS
SELECT
    bucket,
    tag_name,
    avg AS value,
    n AS count,
    min,
    max,
    sum,
    first,
    last,
    diff,
    -- 이동 평균
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS sma_5,
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS sma_10,
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma_20,
    -- 표준편차
    STDDEV(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS stddev_20,
    -- 볼린저 밴드
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS bb_middle,
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) 
        + 2 * STDDEV(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS bb_upper,
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) 
        - 2 * STDDEV(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS bb_lower,
    -- RSI 계산을 위한 변화량
    avg - LAG(avg, 1) OVER (PARTITION BY tag_name ORDER BY bucket) AS change,
    -- EMA 계산 (간단 버전)
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS ema_12,
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 25 PRECEDING AND CURRENT ROW) AS ema_26
FROM influx_agg_1m
WITH DATA;

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_tech_ind_1m_mv_bucket ON tech_ind_1m_mv (bucket DESC);
CREATE INDEX IF NOT EXISTS idx_tech_ind_1m_mv_tag ON tech_ind_1m_mv (tag_name);

-- 6. 1시간 기술 지표 Materialized View
CREATE MATERIALIZED VIEW IF NOT EXISTS tech_ind_1h_mv AS
SELECT
    bucket,
    tag_name,
    avg AS value,
    n AS count,
    min,
    max,
    sum,
    first,
    last,
    diff,
    -- 이동 평균
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS sma_5,
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS sma_10,
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 23 PRECEDING AND CURRENT ROW) AS sma_24,
    -- 표준편차
    STDDEV(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 23 PRECEDING AND CURRENT ROW) AS stddev_24,
    -- 볼린저 밴드
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 23 PRECEDING AND CURRENT ROW) AS bb_middle,
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 23 PRECEDING AND CURRENT ROW) 
        + 2 * STDDEV(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 23 PRECEDING AND CURRENT ROW) AS bb_upper,
    AVG(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 23 PRECEDING AND CURRENT ROW) 
        - 2 * STDDEV(avg) OVER (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 23 PRECEDING AND CURRENT ROW) AS bb_lower
FROM influx_agg_1h
WITH DATA;

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_tech_ind_1h_mv_bucket ON tech_ind_1h_mv (bucket DESC);
CREATE INDEX IF NOT EXISTS idx_tech_ind_1h_mv_tag ON tech_ind_1h_mv (tag_name);

-- 7. 압축 정책 추가 (7일 이상 데이터)
SELECT add_compression_policy('influx_hist', INTERVAL '7 days');

-- 8. 초기 데이터 새로고침 (트랜잭션 외부에서 실행 필요)
-- CALL refresh_continuous_aggregate('influx_agg_10m', NOW() - INTERVAL '7 days', NOW());
-- CALL refresh_continuous_aggregate('influx_agg_1h', NOW() - INTERVAL '30 days', NOW());
-- REFRESH MATERIALIZED VIEW tech_ind_1m_mv;
-- REFRESH MATERIALIZED VIEW tech_ind_1h_mv;

-- 9. 확장 기능 설치 (필요시)
-- CREATE EXTENSION IF NOT EXISTS pg_vector;
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
-- CREATE EXTENSION IF NOT EXISTS hstore;
-- CREATE EXTENSION IF NOT EXISTS ltree;

-- ============================================
-- 실행 후 확인 명령어
-- ============================================
-- SELECT * FROM timescaledb_information.continuous_aggregates;
-- SELECT * FROM timescaledb_information.jobs;
-- SELECT * FROM timescaledb_information.compression_settings;