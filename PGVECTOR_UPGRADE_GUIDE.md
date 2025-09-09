# 🚀 pg_vector RAG Knowledge Base 업그레이드 가이드

## 📋 **업그레이드 개요**

기존 TF-IDF 기반 RAG 시스템을 **pg_vector 확장**을 사용한 고성능 벡터 검색으로 업그레이드합니다.

### **🎯 주요 개선사항**
- **검색 성능**: TF-IDF 대비 **10-100배 빠른** 벡터 검색
- **정확도**: OpenAI 임베딩 모델 기반 **의미론적 유사도**
- **확장성**: 대용량 지식베이스에서도 **일정한 응답 시간**
- **하이브리드 검색**: 벡터 + 텍스트 검색의 **최적 조합**

## 🔧 **1단계: pg_vector 확장 설치**

### **Docker 환경 (권장)**
```bash
# PostgreSQL 컨테이너에 접속
docker exec -it postgres-container psql -U postgres -d EcoAnP

# pg_vector 확장 설치
CREATE EXTENSION vector;
```

### **로컬 PostgreSQL**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-14-pgvector

# macOS
brew install pgvector

# 확장 설치
psql -U postgres -d your_database
CREATE EXTENSION vector;
```

## 🗄️ **2단계: 데이터베이스 스키마 업그레이드**

### **SQL 스크립트 실행**
```bash
# upgrade_to_pgvector.sql 실행
psql -U postgres -d EcoAnP -f upgrade_to_pgvector.sql
```

### **수동 실행 (필요시)**
```sql
-- 1. 벡터 컬럼 추가
ALTER TABLE ai_knowledge_base 
ADD COLUMN content_embedding vector(1536);

-- 2. 벡터 인덱스 생성
CREATE INDEX idx_ai_knowledge_vector 
ON ai_knowledge_base 
USING hnsw (content_embedding vector_cosine_ops);

-- 3. 메타데이터 인덱스
CREATE INDEX idx_ai_knowledge_metadata 
ON ai_knowledge_base 
USING GIN (metadata);
```

## 🤖 **3단계: Python 코드 업데이트**

### **새로운 RAG 엔진 사용**
```python
from ksys_app.ai_engine.rag_engine_pgvector import PgVectorRAGEngine

# OpenAI API 키 설정
openai_api_key = "your-api-key-here"

# RAG 엔진 초기화
rag_engine = PgVectorRAGEngine(openai_api_key)
await rag_engine.initialize()

# 벡터 검색 사용
results = await rag_engine.semantic_search_vector(
    query="온도 센서 D100의 정상 범위는?",
    top_k=5,
    threshold=0.7
)
```

### **기존 코드와의 호환성**
- **자동 폴백**: OpenAI API 없으면 TF-IDF 검색 사용
- **점진적 업그레이드**: 기존 시스템과 병행 운영 가능
- **성능 모니터링**: 벡터화 비율 및 검색 성능 추적

## 📊 **4단계: 성능 테스트 및 검증**

### **벡터 품질 검증**
```sql
-- 통계 확인
SELECT * FROM knowledge_base_stats;

-- 벡터 품질 검증
SELECT * FROM validate_vector_quality();
```

### **검색 성능 비교**
```python
import time

# TF-IDF 검색 시간 측정
start_time = time.time()
tfidf_results = await rag_engine.semantic_search_tfidf(query, top_k=5)
tfidf_time = time.time() - start_time

# 벡터 검색 시간 측정
start_time = time.time()
vector_results = await rag_engine.semantic_search_vector(query, top_k=5)
vector_time = time.time() - start_time

print(f"TF-IDF: {tfidf_time:.3f}초")
print(f"Vector: {vector_time:.3f}초")
print(f"성능 향상: {tfidf_time/vector_time:.1f}배")
```

## 🔍 **5단계: 고급 기능 활용**

### **하이브리드 검색**
```python
# 벡터 + 텍스트 검색의 최적 조합
results = await rag_engine.hybrid_search(
    query="압력 센서 고장 진단",
    top_k=10,
    vector_weight=0.7,  # 벡터 검색 가중치
    text_weight=0.3     # 텍스트 검색 가중치
)
```

### **센서별 특화 검색**
```python
# 특정 센서에 대한 지식 검색
sensor_results = await rag_engine.search_sensor_knowledge_vector(
    sensor_tag="D100",
    query="온도 상승 문제",
    top_k=10
)
```

### **인덱스 최적화**
```python
# 벡터 인덱스 최적화
await rag_engine.optimize_vector_indexes()

# 오래된 임베딩 정리
await rag_engine.cleanup_old_embeddings(days=30)
```

## 📈 **6단계: 모니터링 및 유지보수**

### **성능 지표 모니터링**
```sql
-- 인덱스 사용 통계
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE tablename = 'ai_knowledge_base';

-- 벡터 검색 통계
SELECT 
    content_type,
    COUNT(*) as total,
    COUNT(content_embedding) as vectorized,
    ROUND(COUNT(content_embedding)::float / COUNT(*) * 100, 2) as rate
FROM ai_knowledge_base 
GROUP BY content_type;
```

### **정기 유지보수**
```bash
# 주간 인덱스 최적화
psql -U postgres -d EcoAnP -c "ANALYZE ai_knowledge_base;"

# 월간 벡터 인덱스 재구축
psql -U postgres -d EcoAnP -c "REINDEX INDEX CONCURRENTLY idx_ai_knowledge_vector;"
```

## 🚨 **문제 해결**

### **일반적인 오류**

#### **1. pg_vector 확장 설치 실패**
```bash
# PostgreSQL 버전 확인
psql --version

# pgvector 패키지 재설치
sudo apt-get remove postgresql-14-pgvector
sudo apt-get install postgresql-14-pgvector
```

#### **2. 벡터 컬럼 타입 오류**
```sql
-- 기존 컬럼 삭제 후 재생성
ALTER TABLE ai_knowledge_base DROP COLUMN IF EXISTS content_embedding;
ALTER TABLE ai_knowledge_base ADD COLUMN content_embedding vector(1536);
```

#### **3. OpenAI API 오류**
```python
# API 키 확인
import openai
openai.api_key = "your-api-key"

# 모델 가용성 확인
models = openai.Model.list()
print([model.id for model in models.data if 'embedding' in model.id])
```

### **성능 문제 해결**

#### **검색 속도가 느린 경우**
```sql
-- 인덱스 통계 확인
SELECT * FROM pg_stat_user_indexes WHERE indexname = 'idx_ai_knowledge_vector';

-- 쿼리 계획 분석
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM search_knowledge_vector(
    '[0.1, 0.2, ...]'::vector, 0.7, 5
);
```

#### **메모리 사용량이 높은 경우**
```sql
-- PostgreSQL 메모리 설정 조정
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET work_mem = '4MB';
SELECT pg_reload_conf();
```

## 🎉 **업그레이드 완료 체크리스트**

- [ ] pg_vector 확장 설치 완료
- [ ] 벡터 컬럼 추가 완료
- [ ] 벡터 인덱스 생성 완료
- [ ] 새로운 RAG 엔진 코드 적용 완료
- [ ] OpenAI API 키 설정 완료
- [ ] 기존 지식 임베딩 생성 완료
- [ ] 성능 테스트 완료
- [ ] 모니터링 설정 완료

## 📞 **지원 및 문의**

업그레이드 과정에서 문제가 발생하면:

1. **로그 확인**: PostgreSQL 및 Python 애플리케이션 로그
2. **성능 분석**: `EXPLAIN ANALYZE` 결과 분석
3. **단계별 테스트**: 각 단계별로 개별 테스트 실행

**성공적인 pg_vector 업그레이드로 RAG 시스템의 성능을 대폭 향상시키세요! 🚀**

