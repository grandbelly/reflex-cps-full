-- =====================================================
-- RAG Knowledge Base pg_vector 업그레이드 스크립트
-- =====================================================

-- 1. pg_vector 확장 설치 (관리자 권한 필요)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 기존 테이블에 벡터 컬럼 추가
ALTER TABLE ai_knowledge_base 
ADD COLUMN IF NOT EXISTS content_embedding vector(1536); -- OpenAI text-embedding-ada-002 차원

-- 3. 벡터 인덱스 생성 (HNSW - 고속 근사 검색)
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_vector 
ON ai_knowledge_base 
USING hnsw (content_embedding vector_cosine_ops);

-- 4. 메타데이터 JSONB 인덱스 최적화
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_metadata 
ON ai_knowledge_base 
USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_ai_knowledge_content_type 
ON ai_knowledge_base (content_type);

-- 5. 하이브리드 검색을 위한 복합 인덱스
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_hybrid 
ON ai_knowledge_base 
USING GIN (to_tsvector('english', content));

-- 6. 벡터 검색 함수 생성
CREATE OR REPLACE FUNCTION search_knowledge_vector(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    content_types text[] DEFAULT NULL
)
RETURNS TABLE (
    id int,
    content text,
    content_type text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        akb.id,
        akb.content,
        akb.content_type,
        akb.metadata,
        1 - (akb.content_embedding <=> query_embedding) AS similarity
    FROM ai_knowledge_base akb
    WHERE 
        akb.content_embedding IS NOT NULL
        AND 1 - (akb.content_embedding <=> query_embedding) > match_threshold
        AND (content_types IS NULL OR akb.content_type = ANY(content_types))
    ORDER BY akb.content_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 7. 하이브리드 검색 함수 (벡터 + 텍스트)
CREATE OR REPLACE FUNCTION search_knowledge_hybrid(
    query_text text,
    query_embedding vector(1536),
    vector_weight float DEFAULT 0.7,
    text_weight float DEFAULT 0.3,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id int,
    content text,
    content_type text,
    metadata jsonb,
    combined_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        akb.id,
        akb.content,
        akb.content_type,
        akb.metadata,
        (vector_weight * (1 - (akb.content_embedding <=> query_embedding))) + 
        (text_weight * ts_rank(to_tsvector('english', akb.content), plainto_tsquery('english', query_text))) AS combined_score
    FROM ai_knowledge_base akb
    WHERE 
        akb.content_embedding IS NOT NULL
        AND to_tsvector('english', akb.content) @@ plainto_tsquery('english', query_text)
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

-- 8. 센서별 벡터 검색 함수
CREATE OR REPLACE FUNCTION search_sensor_knowledge_vector(
    sensor_tag text,
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.6,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id int,
    content text,
    content_type text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        akb.id,
        akb.content,
        akb.content_type,
        akb.metadata,
        1 - (akb.content_embedding <=> query_embedding) AS similarity
    FROM ai_knowledge_base akb
    WHERE 
        akb.content_embedding IS NOT NULL
        AND 1 - (akb.content_embedding <=> query_embedding) > match_threshold
        AND (
            akb.metadata->>'sensor_tag' = sensor_tag
            OR akb.metadata->>'primary_sensor' = sensor_tag
            OR akb.metadata->>'secondary_sensor' = sensor_tag
        )
    ORDER BY akb.content_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 9. 성능 모니터링 뷰
CREATE OR REPLACE VIEW knowledge_base_stats AS
SELECT 
    content_type,
    COUNT(*) as total_items,
    COUNT(content_embedding) as vectorized_items,
    ROUND(
        COUNT(content_embedding)::float / COUNT(*) * 100, 2
    ) as vectorization_rate
FROM ai_knowledge_base
GROUP BY content_type
ORDER BY total_items DESC;

-- 10. 벡터 품질 검증 함수
CREATE OR REPLACE FUNCTION validate_vector_quality()
RETURNS TABLE (
    metric text,
    value numeric,
    status text
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 벡터화 비율
    RETURN QUERY
    SELECT 
        'Vectorization Rate'::text,
        ROUND(
            (COUNT(content_embedding)::float / COUNT(*)) * 100, 2
        )::numeric,
        CASE 
            WHEN COUNT(content_embedding)::float / COUNT(*) > 0.9 THEN 'Excellent'
            WHEN COUNT(content_embedding)::float / COUNT(*) > 0.7 THEN 'Good'
            WHEN COUNT(content_embedding)::float / COUNT(*) > 0.5 THEN 'Fair'
            ELSE 'Poor'
        END::text
    FROM ai_knowledge_base;
    
    -- 인덱스 사용 통계
    RETURN QUERY
    SELECT 
        'Index Usage'::text,
        COALESCE(idx_scan, 0)::numeric,
        CASE 
            WHEN idx_scan > 1000 THEN 'High'
            WHEN idx_scan > 100 THEN 'Medium'
            ELSE 'Low'
        END::text
    FROM pg_stat_user_indexes 
    WHERE indexrelname = 'idx_ai_knowledge_vector';
END;
$$;

-- =====================================================
-- 업그레이드 완료 후 확인 명령어
-- =====================================================

-- 확장 설치 확인
-- SELECT * FROM pg_extension WHERE extname = 'vector';

-- 벡터 컬럼 확인
-- SELECT column_name, data_type FROM information_schema.columns 
-- WHERE table_name = 'ai_knowledge_base' AND column_name = 'content_embedding';

-- 인덱스 확인
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'ai_knowledge_base';

-- 통계 확인
-- SELECT * FROM knowledge_base_stats;

-- 벡터 품질 검증
-- SELECT * FROM validate_vector_quality();

