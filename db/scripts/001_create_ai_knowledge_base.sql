-- =====================================================
-- TASK_001: DB_CREATE_KNOWLEDGE_TABLE
-- 목적: RAG 시스템용 지식 베이스 테이블 생성
-- 작성일: 2024-01-15
-- =====================================================

-- 기존 테이블이 있으면 백업
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'ai_knowledge_base') THEN
        -- 백업 테이블 생성
        EXECUTE 'CREATE TABLE IF NOT EXISTS ai_knowledge_base_backup_' || to_char(now(), 'YYYYMMDD_HH24MISS') || ' AS SELECT * FROM ai_knowledge_base';
        RAISE NOTICE 'Existing table backed up';
    END IF;
END $$;

-- 테이블 삭제 (필요시)
-- DROP TABLE IF EXISTS public.ai_knowledge_base CASCADE;

-- =====================================================
-- 1. 메인 테이블 생성
-- =====================================================
CREATE TABLE IF NOT EXISTS public.ai_knowledge_base (
    id SERIAL PRIMARY KEY,
    
    -- 핵심 컨텐츠
    content TEXT NOT NULL,
    content_type VARCHAR(50) NOT NULL DEFAULT 'general',
    
    -- 6하 원칙 구조화 데이터
    w5h1_data JSONB DEFAULT '{}',
    
    -- 메타데이터
    metadata JSONB DEFAULT '{}',
    
    -- 태그 (빠른 검색용)
    tags TEXT[] DEFAULT '{}',
    
    -- 우선순위 및 신뢰도
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    confidence_score DECIMAL(3,2) DEFAULT 1.0 CHECK (confidence_score BETWEEN 0 AND 1),
    
    -- 사용 통계
    usage_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    
    -- 버전 관리
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    
    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system',
    updated_by VARCHAR(100) DEFAULT 'system'
);

-- =====================================================
-- 2. 인덱스 생성 (검색 성능 최적화)
-- =====================================================

-- 전문 검색 인덱스 (GIN - Generalized Inverted Index)
CREATE INDEX IF NOT EXISTS idx_knowledge_content_gin 
    ON ai_knowledge_base USING gin(to_tsvector('english', content));

-- 한국어 검색을 위한 추가 인덱스
CREATE INDEX IF NOT EXISTS idx_knowledge_content_korean
    ON ai_knowledge_base USING gin(to_tsvector('simple', content));

-- 타입별 검색
CREATE INDEX IF NOT EXISTS idx_knowledge_type 
    ON ai_knowledge_base(content_type);

-- JSON 검색
CREATE INDEX IF NOT EXISTS idx_knowledge_metadata 
    ON ai_knowledge_base USING gin(metadata);

CREATE INDEX IF NOT EXISTS idx_knowledge_w5h1 
    ON ai_knowledge_base USING gin(w5h1_data);

-- 태그 검색
CREATE INDEX IF NOT EXISTS idx_knowledge_tags 
    ON ai_knowledge_base USING gin(tags);

-- 활성 레코드만 빠르게 조회
CREATE INDEX IF NOT EXISTS idx_knowledge_active 
    ON ai_knowledge_base(is_active) WHERE is_active = true;

-- 우선순위 기반 정렬
CREATE INDEX IF NOT EXISTS idx_knowledge_priority 
    ON ai_knowledge_base(priority DESC, confidence_score DESC);

-- 시간 기반 조회
CREATE INDEX IF NOT EXISTS idx_knowledge_created 
    ON ai_knowledge_base(created_at DESC);

-- =====================================================
-- 3. 트리거 함수 - 자동 업데이트
-- =====================================================
CREATE OR REPLACE FUNCTION update_knowledge_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 업데이트 시 자동으로 timestamp와 version 갱신
DROP TRIGGER IF EXISTS trigger_update_knowledge_timestamp ON ai_knowledge_base;
CREATE TRIGGER trigger_update_knowledge_timestamp
    BEFORE UPDATE ON ai_knowledge_base
    FOR EACH ROW
    EXECUTE FUNCTION update_knowledge_timestamp();

-- =====================================================
-- 4. 뷰 생성 - 자주 사용하는 쿼리 최적화
-- =====================================================

-- 활성 지식만 조회하는 뷰
CREATE OR REPLACE VIEW v_active_knowledge AS
SELECT 
    id,
    content,
    content_type,
    w5h1_data,
    metadata,
    tags,
    priority,
    confidence_score
FROM ai_knowledge_base
WHERE is_active = true
ORDER BY priority DESC, confidence_score DESC;

-- 6하 원칙별 지식 뷰
CREATE OR REPLACE VIEW v_knowledge_5w1h AS
SELECT 
    id,
    content_type,
    w5h1_data->>'what' as what,
    w5h1_data->>'why' as why,
    w5h1_data->>'when' as when_info,
    w5h1_data->>'where' as where_info,
    w5h1_data->>'who' as who,
    w5h1_data->>'how' as how,
    priority,
    confidence_score
FROM ai_knowledge_base
WHERE is_active = true AND w5h1_data IS NOT NULL;

-- =====================================================
-- 5. 초기 데이터 삽입
-- =====================================================

-- 센서 사양 지식
INSERT INTO ai_knowledge_base (content, content_type, w5h1_data, metadata, tags, priority, confidence_score)
VALUES 
(
    'D100-D199 센서는 온도 측정용입니다. 정상 범위는 20-80°C입니다. RTD 방식으로 ±0.5°C 정확도를 제공합니다.',
    'sensor_spec',
    '{
        "what": "온도 측정 센서 (RTD 방식)",
        "why": "프로세스 온도 모니터링 및 제어",
        "when": "실시간 측정 (응답시간 < 5초)",
        "where": "반응기, 열교환기, 저장 탱크",
        "who": "계측팀 관리",
        "how": "백금 저항체의 온도 변화에 따른 저항 측정"
    }'::jsonb,
    '{"sensor_range": "D100-D199", "type": "temperature", "unit": "°C", "accuracy": 0.5}'::jsonb,
    ARRAY['온도', 'temperature', 'RTD', 'D100'],
    9,
    1.0
),
(
    'D200-D299 센서는 압력 측정용입니다. 정상 범위는 1-10 bar입니다. 압력 센서는 ±0.1 bar의 정확도를 가집니다.',
    'sensor_spec',
    '{
        "what": "압력 측정 센서",
        "why": "시스템 압력 모니터링 및 안전 관리",
        "when": "실시간 측정",
        "where": "압력 용기, 배관 네트워크, 펌프 스테이션",
        "who": "기계팀 관리",
        "how": "압전 소자를 이용한 압력 측정"
    }'::jsonb,
    '{"sensor_range": "D200-D299", "type": "pressure", "unit": "bar", "accuracy": 0.1}'::jsonb,
    ARRAY['압력', 'pressure', 'D200'],
    9,
    1.0
),
(
    'D300-D399 센서는 유량 측정용입니다. 정상 범위는 10-1000 L/min입니다.',
    'sensor_spec',
    '{
        "what": "유량 측정 센서",
        "why": "프로세스 유량 제어 및 물질 수지 관리",
        "when": "실시간 측정",
        "where": "입구/출구 배관",
        "who": "운전팀 모니터링",
        "how": "전자기 유도 방식 유량 측정"
    }'::jsonb,
    '{"sensor_range": "D300-D399", "type": "flow", "unit": "L/min", "accuracy": 2}'::jsonb,
    ARRAY['유량', 'flow', 'D300'],
    8,
    1.0
);

-- 고장 진단 지식
INSERT INTO ai_knowledge_base (content, content_type, w5h1_data, metadata, tags, priority, confidence_score)
VALUES 
(
    '펌프 고장 시 유출 수량이 감소하고 전류값이 상승하며 진동이 증가합니다. 즉시 예비 펌프를 가동하고 정비팀에 연락하세요.',
    'troubleshooting',
    '{
        "what": "펌프 고장 - 유량 감소, 전류 상승, 진동 증가",
        "why": "임펠러 손상, 베어링 마모, 캐비테이션",
        "when": "유량 10% 이상 감소 시",
        "where": "메인 펌프, 부스터 펌프",
        "who": "기계팀 담당, 운전팀 1차 대응",
        "how": "1) 예비 펌프 가동 2) 진동/전류 확인 3) 정비팀 호출"
    }'::jsonb,
    '{"issue_type": "pump_failure", "severity": "high", "response_time": "immediate"}'::jsonb,
    ARRAY['펌프', '고장', 'pump', 'failure'],
    10,
    0.95
),
(
    '막파손 시 전도도가 급상승하고 염제거율이 급감합니다. 수질 오염 방지를 위해 즉시 Emergency Stop을 실행하세요.',
    'troubleshooting',
    '{
        "what": "RO 막파손 - 전도도 상승, 염제거율 하락",
        "why": "막 파열, 오링 손상, 과압 운전",
        "when": "전도도 500 μS/cm 초과 시",
        "where": "RO 모듈, 압력 용기",
        "who": "운전팀 즉시 대응, 수질팀 통보",
        "how": "1) Emergency Stop 2) 생산수 차단 3) 원인 조사"
    }'::jsonb,
    '{"issue_type": "membrane_damage", "severity": "critical", "response_time": "immediate"}'::jsonb,
    ARRAY['막파손', 'RO', 'membrane', '수질'],
    10,
    0.98
),
(
    '막오염 시 TMP가 지속적으로 상승하고 유량이 감소합니다. CIP 세척 주기를 단축하고 전처리 시스템을 점검하세요.',
    'troubleshooting',
    '{
        "what": "막오염 - TMP 상승, 유량 감소",
        "why": "스케일 형성, 생물막 성장, 콜로이드 축적",
        "when": "TMP 3 bar 초과 시",
        "where": "RO 멤브레인 표면",
        "who": "운전팀 모니터링, 수처리팀 분석",
        "how": "1) CIP 세척 실시 2) 전처리 약품 조정 3) 수질 분석"
    }'::jsonb,
    '{"issue_type": "membrane_fouling", "severity": "medium", "response_time": "30min"}'::jsonb,
    ARRAY['막오염', 'fouling', 'CIP', 'TMP'],
    8,
    0.92
);

-- 유지보수 지식
INSERT INTO ai_knowledge_base (content, content_type, w5h1_data, metadata, tags, priority, confidence_score)
VALUES 
(
    'RO 멤브레인은 3년 주기로 교체합니다. TMP 증가율과 염제거율 감소 추세를 모니터링하여 교체 시기를 결정합니다.',
    'maintenance',
    '{
        "what": "RO 멤브레인 정기 교체",
        "why": "성능 저하 방지, 수질 안정성 확보",
        "when": "3년 주기 또는 성능 저하 시",
        "where": "RO 압력 용기",
        "who": "정비팀 + 외부 전문업체",
        "how": "1) 운전 정지 2) 압력 용기 개방 3) 멤브레인 교체 4) 누출 테스트"
    }'::jsonb,
    '{"component": "RO_membrane", "period": "3_years", "cost_level": "high"}'::jsonb,
    ARRAY['RO', '멤브레인', '교체', 'maintenance'],
    7,
    0.90
),
(
    '센서 캘리브레이션은 분기별로 실시합니다. 3점 교정법(0%, 50%, 100%)을 사용하여 정확도를 유지합니다.',
    'maintenance',
    '{
        "what": "센서 정기 캘리브레이션",
        "why": "측정 정확도 유지, 드리프트 보정",
        "when": "분기별 (3개월 주기)",
        "where": "현장 또는 계측실",
        "who": "계측팀 전문 기술자",
        "how": "1) 센서 분리 2) 표준액 준비 3) 3점 교정 4) 인증서 발급"
    }'::jsonb,
    '{"task": "calibration", "frequency": "quarterly", "method": "3_point"}'::jsonb,
    ARRAY['캘리브레이션', 'calibration', '교정'],
    8,
    0.95
);

-- 운영 패턴 지식
INSERT INTO ai_knowledge_base (content, content_type, w5h1_data, metadata, tags, priority, confidence_score)
VALUES 
(
    '해수담수화 설비는 야간 전력 요금이 저렴한 시간대(23:00-07:00)에 최대 생산량으로 운전합니다.',
    'operational_pattern',
    '{
        "what": "야간 최대 생산 운전 패턴",
        "why": "전력 비용 절감",
        "when": "23:00 - 07:00",
        "where": "전체 RO 트레인",
        "who": "운전팀 자동 스케줄",
        "how": "SCADA 시간대별 설정값 자동 변경"
    }'::jsonb,
    '{"pattern_type": "production", "optimization": "cost"}'::jsonb,
    ARRAY['운전패턴', '야간운전', '전력요금'],
    6,
    0.88
);

-- 상관관계 지식
INSERT INTO ai_knowledge_base (content, content_type, w5h1_data, metadata, tags, priority, confidence_score)
VALUES 
(
    'TMP와 수온은 역상관 관계를 가집니다. 수온이 1°C 하락하면 TMP는 약 3% 상승합니다.',
    'correlation',
    '{
        "what": "TMP-수온 역상관 관계",
        "why": "온도에 따른 점도 변화",
        "when": "항시 적용",
        "where": "RO 시스템 전체",
        "who": "자동 보정 알고리즘",
        "how": "온도 보정 계수 적용"
    }'::jsonb,
    '{"correlation_type": "inverse", "coefficient": -0.03, "parameters": ["TMP", "temperature"]}'::jsonb,
    ARRAY['상관관계', 'TMP', '온도', 'correlation'],
    7,
    0.93
);

-- =====================================================
-- 6. 권한 설정
-- =====================================================

-- 읽기 전용 역할 (오퍼레이터용)
GRANT SELECT ON ai_knowledge_base TO readonly_user;
GRANT SELECT ON v_active_knowledge TO readonly_user;
GRANT SELECT ON v_knowledge_5w1h TO readonly_user;

-- 읽기/쓰기 역할 (관리자용)
-- GRANT SELECT, INSERT, UPDATE ON ai_knowledge_base TO readwrite_user;

-- =====================================================
-- 7. 통계 업데이트
-- =====================================================
ANALYZE ai_knowledge_base;

-- =====================================================
-- 8. 확인 쿼리
-- =====================================================
DO $$
DECLARE
    row_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO row_count FROM ai_knowledge_base;
    RAISE NOTICE 'ai_knowledge_base 테이블 생성 완료. 초기 데이터: % 건', row_count;
    
    -- 각 타입별 카운트
    FOR content_type, row_count IN 
        SELECT content_type, COUNT(*) 
        FROM ai_knowledge_base 
        GROUP BY content_type 
        ORDER BY content_type
    LOOP
        RAISE NOTICE '  - % : % 건', content_type, row_count;
    END LOOP;
END $$;

-- 생성된 구조 확인
SELECT 
    'Table created successfully' as status,
    COUNT(*) as total_records,
    COUNT(DISTINCT content_type) as content_types
FROM ai_knowledge_base;