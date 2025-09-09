-- =====================================================
-- TASK_001: ai_knowledge_base 테이블 업데이트
-- 목적: 기존 테이블에 6하원칙 지원을 위한 컬럼 추가
-- 작성일: 2025-09-08
-- =====================================================

-- 1. 기존 데이터 백업
CREATE TABLE IF NOT EXISTS ai_knowledge_base_backup_20250908 AS 
SELECT * FROM ai_knowledge_base;

-- 2. 누락된 컬럼 추가
ALTER TABLE ai_knowledge_base 
ADD COLUMN IF NOT EXISTS w5h1_data JSONB DEFAULT '{}';

ALTER TABLE ai_knowledge_base 
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

ALTER TABLE ai_knowledge_base 
ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10);

ALTER TABLE ai_knowledge_base 
ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(3,2) DEFAULT 1.0 CHECK (confidence_score BETWEEN 0 AND 1);

ALTER TABLE ai_knowledge_base 
ADD COLUMN IF NOT EXISTS usage_count INTEGER DEFAULT 0;

ALTER TABLE ai_knowledge_base 
ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMP WITH TIME ZONE;

ALTER TABLE ai_knowledge_base 
ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;

ALTER TABLE ai_knowledge_base 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

ALTER TABLE ai_knowledge_base 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- 3. 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_base_type ON ai_knowledge_base(content_type);
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_base_tags ON ai_knowledge_base USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_base_priority ON ai_knowledge_base(priority DESC);
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_base_active ON ai_knowledge_base(is_active);
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_base_w5h1 ON ai_knowledge_base USING gin(w5h1_data);

-- 4. 트리거 함수 생성
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5. 트리거 생성
DROP TRIGGER IF EXISTS update_ai_knowledge_base_updated_at ON ai_knowledge_base;
CREATE TRIGGER update_ai_knowledge_base_updated_at 
    BEFORE UPDATE ON ai_knowledge_base 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 6. 초기 데이터 삽입 (6하원칙 적용)
INSERT INTO ai_knowledge_base (content, content_type, w5h1_data, metadata, tags, priority, confidence_score)
VALUES 
(
    '온도 센서 D100-D199: RTD 방식, -50~500°C, 정확도 ±0.1°C',
    'sensor_spec',
    '{
        "what": "RTD 온도 센서",
        "why": "정밀한 온도 측정을 위한 센서",
        "when": "24시간 연속 모니터링",
        "where": "담수화 플랜트 전체",
        "who": "운영자, 엔지니어",
        "how": "RTD 방식으로 저항값 변화 측정"
    }'::jsonb,
    '{"sensor_range": "D100-D199", "accuracy": "±0.1°C"}'::jsonb,
    ARRAY['temperature', 'sensor', 'RTD'],
    8,
    1.0
),
(
    '고온 경보 발생 시: 1) 냉각수 유량 확인 2) 열교환기 상태 점검 3) 센서 교정 확인',
    'troubleshooting',
    '{
        "what": "고온 경보 트러블슈팅",
        "why": "시스템 과열 방지",
        "when": "경보 발생 즉시",
        "where": "열교환 시스템",
        "who": "현장 운영자",
        "how": "3단계 점검 프로세스"
    }'::jsonb,
    '{"alarm_type": "high_temperature", "steps": 3}'::jsonb,
    ARRAY['temperature', 'alarm', 'cooling'],
    9,
    1.0
),
(
    'RO 멤브레인 압력 모니터링: TMP (Trans-Membrane Pressure) = (Feed + Concentrate)/2 - Permeate',
    'calculation',
    '{
        "what": "TMP 계산식",
        "why": "멤브레인 상태 모니터링",
        "when": "실시간 계산",
        "where": "RO 시스템",
        "who": "시스템 자동 계산",
        "how": "압력 센서 데이터 기반 계산"
    }'::jsonb,
    '{"formula": "TMP = (Feed + Concentrate)/2 - Permeate", "unit": "bar"}'::jsonb,
    ARRAY['RO', 'membrane', 'pressure', 'TMP'],
    8,
    1.0
),
(
    '전도도 센서 교정: 표준용액 1413 μS/cm (25°C)로 월 1회 교정',
    'maintenance',
    '{
        "what": "전도도 센서 교정",
        "why": "측정 정확도 유지",
        "when": "월 1회",
        "where": "수질 측정 포인트",
        "who": "정비팀",
        "how": "표준용액 사용"
    }'::jsonb,
    '{"calibration_solution": "1413 μS/cm", "frequency": "monthly"}'::jsonb,
    ARRAY['conductivity', 'calibration', 'maintenance'],
    7,
    1.0
),
(
    '유량계 이상 진단: 1) 파이프 내 기포 확인 2) 센서 전극 청소 3) 접지 상태 점검',
    'troubleshooting',
    '{
        "what": "유량계 이상 진단",
        "why": "정확한 유량 측정 확보",
        "when": "이상 신호 감지 시",
        "where": "유량 측정 지점",
        "who": "유지보수팀",
        "how": "3단계 진단 프로세스"
    }'::jsonb,
    '{"diagnostic_steps": 3, "common_issues": ["bubbles", "dirty_electrodes", "grounding"]}'::jsonb,
    ARRAY['flow', 'diagnostic', 'maintenance'],
    8,
    1.0
)
ON CONFLICT (id) DO NOTHING;

-- 7. 검증 쿼리
SELECT 
    'Table Structure' as check_type,
    COUNT(*) as column_count,
    string_agg(column_name, ', ') as columns
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'ai_knowledge_base';

SELECT 
    'Data Count' as check_type,
    COUNT(*) as total_records
FROM ai_knowledge_base;

SELECT 
    'Sample Data' as check_type,
    id,
    content_type,
    LEFT(content, 50) as content_preview,
    w5h1_data->>'what' as what_field
FROM ai_knowledge_base
WHERE w5h1_data IS NOT NULL
LIMIT 3;