-- =====================================================
-- 이력 뷰테이블 재생성 (하이퍼테이블 기반)
-- =====================================================

-- 1. 기존 오류 뷰들 삭제
DROP VIEW IF EXISTS influx_agg_1m CASCADE;
DROP VIEW IF EXISTS influx_agg_5m CASCADE;
DROP VIEW IF EXISTS influx_agg_1h CASCADE;
DROP VIEW IF EXISTS influx_agg_1d CASCADE;
DROP VIEW IF EXISTS influx_latest CASCADE;

-- 2. 새로운 뷰 생성 (연속 집계 기반)
CREATE OR REPLACE VIEW influx_agg_1m AS
SELECT * FROM influx_agg_1m;

CREATE OR REPLACE VIEW influx_agg_5m AS
SELECT * FROM influx_agg_5m;

CREATE OR REPLACE VIEW influx_agg_1h AS
SELECT * FROM influx_agg_1h;

CREATE OR REPLACE VIEW influx_agg_1d AS
SELECT * FROM influx_agg_1d;

-- 3. 최신값 뷰 재생성
CREATE OR REPLACE VIEW influx_latest AS
SELECT DISTINCT ON (tag_name)
    tag_name,
    value,
    ts,
    qc,
    meta
FROM influx_hist
ORDER BY tag_name, ts DESC;

-- 4. 기술적 지표 뷰 생성
CREATE OR REPLACE VIEW tech_ind_10m_mv AS
SELECT 
    time_bucket('10 minutes', ts) AS bucket,
    tag_name,
    AVG(value) AS avg_value,
    STDDEV(value) AS std_value,
    COUNT(*) AS sample_count
FROM influx_hist
WHERE ts >= NOW() - INTERVAL '7 days'
GROUP BY bucket, tag_name
ORDER BY bucket DESC, tag_name;

CREATE OR REPLACE VIEW tech_ind_1h_mv AS
SELECT 
    time_bucket('1 hour', ts) AS bucket,
    tag_name,
    AVG(value) AS avg_value,
    STDDEV(value) AS std_value,
    COUNT(*) AS sample_count
FROM influx_hist
WHERE ts >= NOW() - INTERVAL '30 days'
GROUP BY bucket, tag_name
ORDER BY bucket DESC, tag_name;

CREATE OR REPLACE VIEW tech_ind_1d_mv AS
SELECT 
    time_bucket('1 day', ts) AS bucket,
    tag_name,
    AVG(value) AS avg_value,
    STDDEV(value) AS std_value,
    COUNT(*) AS sample_count
FROM influx_hist
WHERE ts >= NOW() - INTERVAL '365 days'
GROUP BY bucket, tag_name
ORDER BY bucket DESC, tag_name;

-- 5. 시스템 통계 뷰 생성
CREATE OR REPLACE VIEW system_stats AS
SELECT 
    tag_name,
    COUNT(*) as total_records,
    MIN(ts) as first_record,
    MAX(ts) as last_record,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value
FROM influx_hist
GROUP BY tag_name
ORDER BY tag_name;

-- 6. 성공 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ 이력 뷰테이블 재생성 완료!';
    RAISE NOTICE '📊 시계열 집계: 1m, 5m, 1h, 1d';
    RAISE NOTICE '📈 기술적 지표: 10m, 1h, 1d';
    RAISE NOTICE '🔍 최신값 뷰: influx_latest';
    RAISE NOTICE '📋 시스템 통계: system_stats';
END $$;

