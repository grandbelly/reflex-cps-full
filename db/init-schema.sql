-- =====================================================
-- 기본 스키마 및 테이블 초기화 스크립트
-- =====================================================

-- 스키마 생성 (필요 시 사용)
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS ai_engine;

-- 핵심 테이블: 시계열 원본, 태그, QC 규칙
CREATE TABLE IF NOT EXISTS public.influx_hist (
    ts        timestamptz    NOT NULL,
    tag_name  text           NOT NULL,
    value     double precision NOT NULL,
    qc        smallint       DEFAULT 0,
    meta      jsonb          DEFAULT '{}'::jsonb,
    CONSTRAINT influx_hist_pkey PRIMARY KEY (ts, tag_name)
);

CREATE TABLE IF NOT EXISTS public.influx_tag (
    key        text PRIMARY KEY,
    tag_id     text,
    tag_name   text NOT NULL UNIQUE,
    tag_type   text NOT NULL,
    unit       text,
    meta       jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.influx_qc_rule (
    tag_name   text PRIMARY KEY,
    min_val    double precision,
    max_val    double precision,
    max_step   double precision,
    max_gap_seconds integer DEFAULT 120,
    allow_negative boolean DEFAULT true,
    enabled    boolean DEFAULT true,
    meta       jsonb DEFAULT '{}'::jsonb,
    warn_min   double precision,
    warn_max   double precision,
    crit_min   double precision,
    crit_max   double precision,
    roc_max_per_min double precision,
    spike_zscore    double precision,
    deadband_pct    double precision
);

-- 유용한 보조 인덱스
CREATE INDEX IF NOT EXISTS idx_influx_hist_tag_time ON public.influx_hist (tag_name, ts DESC);

-- 성능 모니터링 뷰
CREATE OR REPLACE VIEW public.system_stats AS
SELECT 'Database Size' as metric, pg_size_pretty(pg_database_size(current_database())) as value
UNION ALL
SELECT 'Active Connections', count(*)::text FROM pg_stat_activity WHERE state = 'active'
UNION ALL
SELECT 'TimescaleDB Chunks', count(*)::text FROM timescaledb_information.chunks
UNION ALL
SELECT 'TimescaleDB Hypertables', count(*)::text FROM timescaledb_information.hypertables;

-- 성공 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ 기본 스키마/테이블 초기화 완료!';
END $$;
