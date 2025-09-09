# 🚀 종합 DB 마이그레이션 가이드
## TimescaleDB + pg_vector + 모든 DB 객체 마이그레이션

### 📋 **마이그레이션 대상**

#### **1. 기본 구조**
- ✅ **테이블** - 데이터 구조
- ✅ **뷰** - 가상 테이블
- ✅ **스키마** - 논리적 그룹화

#### **2. 고급 기능**
- 🔐 **정책(Policies)** - Row Level Security
- ⚡ **함수(Functions)** - 비즈니스 로직
- 🔔 **트리거(Triggers)** - 자동 실행 로직
- 📊 **인덱스(Indexes)** - 성능 최적화
- 🔗 **제약조건(Constraints)** - 데이터 무결성
- 🔢 **시퀀스(Sequences)** - 자동 증가 값

#### **3. TimescaleDB 특화**
- ⏰ **하이퍼테이블** - 시계열 데이터
- 📈 **연속 집계** - 자동 롤업
- 🗜️ **압축 정책** - 저장 공간 최적화

#### **4. 권한 및 보안**
- 👥 **사용자/역할** - 접근 제어
- 🔑 **권한** - 객체별 접근 권한
- 🛡️ **RLS 정책** - 행별 보안

### 🚀 **마이그레이션 단계**

#### **1단계: 종합 백업**
```bash
# 모든 DB 객체 정보 수집
python comprehensive_db_backup.py

# pg_dump로 전체 백업 (권장)
pg_dump -h 192.168.1.80 -U postgres -d EcoAnP \
  --schema-only \
  --no-owner \
  --no-privileges \
  > backups/ecoanp_schema_only.sql

# 데이터 백업 (필요시)
pg_dump -h 192.168.1.80 -U postgres -d EcoAnP \
  --data-only \
  --no-owner \
  --no-privileges \
  > backups/ecoanp_data_only.sql
```

#### **2단계: 새로운 환경 구축**
```bash
# 디렉토리 생성
mkdir -p data/postgresql backups logs

# TimescaleDB + pg_vector 도커 이미지 빌드
docker build -f Dockerfile.timescaledb -t ecoanp-timescaledb:latest .

# 서비스 시작
docker-compose -f docker-compose.timescaledb.yml up -d
```

#### **3단계: 스키마 복원**
```bash
# 스키마만 복원 (테이블, 뷰, 함수, 트리거, 정책 등)
docker exec -i ecoanp-timescaledb psql -U postgres -d EcoAnP < backups/ecoanp_schema_only.sql

# TimescaleDB 확장 설치 확인
docker exec -i ecoanp-timescaledb psql -U postgres -d EcoAnP -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';"
```

#### **4단계: 데이터 복원**
```bash
# 데이터 복원 (필요시)
docker exec -i ecoanp-timescaledb psql -U postgres -d EcoAnP < backups/ecoanp_data_only.sql
```

#### **5단계: pg_vector 업그레이드**
```bash
# pg_vector 확장 설치
docker exec -i ecoanp-timescaledb psql -U postgres -d EcoAnP -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 벡터 컬럼 추가
docker exec -i ecoanp-timescaledb psql -U postgres -d EcoAnP -c "
ALTER TABLE ai_knowledge_base 
ADD COLUMN IF NOT EXISTS content_embedding vector(1536);"

# 벡터 인덱스 생성
docker exec -i ecoanp-timescaledb psql -U postgres -d EcoAnP -c "
CREATE INDEX IF NOT EXISTS idx_ai_knowledge_vector 
ON ai_knowledge_base 
USING hnsw (content_embedding vector_cosine_ops);"
```

#### **6단계: 검증 및 테스트**
```bash
# 모든 객체 개수 확인
docker exec -i ecoanp-timescaledb psql -U postgres -d EcoAnP -c "
SELECT 
    'Tables' as object_type, COUNT(*) as count FROM pg_tables WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
UNION ALL
SELECT 'Views', COUNT(*) FROM pg_views WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
UNION ALL
SELECT 'Functions', COUNT(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
UNION ALL
SELECT 'Triggers', COUNT(*) FROM pg_trigger WHERE NOT tgisinternal
UNION ALL
SELECT 'Policies', COUNT(*) FROM pg_policy
UNION ALL
SELECT 'Indexes', COUNT(*) FROM pg_indexes WHERE schemaname NOT IN ('information_schema', 'pg_catalog');"

# TimescaleDB 정보 확인
docker exec -i ecoanp-timescaledb psql -U postgres -d EcoAnP -c "
SELECT * FROM timescaledb_information.hypertables;
SELECT * FROM timescaledb_information.continuous_aggregates;"

# pg_vector 확인
docker exec -i ecoanp-timescaledb psql -U postgres -d EcoAnP -c "
SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### 🔧 **문제 해결**

#### **정책 복원 실패**
```sql
-- RLS 활성화 확인
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE rowsecurity = true;

-- 정책 재생성
CREATE POLICY policy_name ON table_name
FOR ALL USING (condition);
```

#### **함수 복원 실패**
```sql
-- 함수 의존성 확인
SELECT 
    p.proname as function_name,
    pg_get_functiondef(p.oid) as definition
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public';

-- 함수 재생성
CREATE OR REPLACE FUNCTION function_name(...) 
RETURNS type AS $$
BEGIN
    -- function body
END;
$$ LANGUAGE plpgsql;
```

#### **트리거 복원 실패**
```sql
-- 트리거 확인
SELECT 
    t.tgname as trigger_name,
    c.relname as table_name,
    p.proname as function_name
FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE NOT t.tgisinternal;

-- 트리거 재생성
CREATE TRIGGER trigger_name
    BEFORE INSERT ON table_name
    FOR EACH ROW
    EXECUTE FUNCTION function_name();
```

#### **TimescaleDB 하이퍼테이블 복원 실패**
```sql
-- 하이퍼테이블 변환
SELECT create_hypertable('table_name', 'timestamp_column');

-- 압축 정책 설정
SELECT add_compression_policy('table_name', INTERVAL '7 days');

-- 연속 집계 재생성
CREATE MATERIALIZED VIEW view_name
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', timestamp_column), ...
FROM table_name
GROUP BY 1, ...;
```

### 📊 **성능 최적화**

#### **인덱스 최적화**
```sql
-- 사용하지 않는 인덱스 확인
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0;

-- 인덱스 재생성
REINDEX INDEX CONCURRENTLY index_name;
```

#### **통계 업데이트**
```sql
-- 테이블 통계 업데이트
ANALYZE table_name;

-- 전체 DB 통계 업데이트
VACUUM ANALYZE;
```

### 🎯 **마이그레이션 체크리스트**

- [ ] **종합 백업 완료**
  - [ ] 스키마 정보 수집
  - [ ] 모든 DB 객체 정보 수집
  - [ ] pg_dump 백업 파일 생성

- [ ] **새로운 환경 구축**
  - [ ] TimescaleDB + pg_vector 도커 이미지 빌드
  - [ ] 서비스 시작 및 헬스체크 통과

- [ ] **스키마 복원**
  - [ ] 테이블 구조 복원
  - [ ] 뷰 복원
  - [ ] 함수 복원
  - [ ] 트리거 복원
  - [ ] 정책 복원
  - [ ] 제약조건 복원
  - [ ] 인덱스 복원

- [ ] **TimescaleDB 설정**
  - [ ] 하이퍼테이블 변환
  - [ ] 압축 정책 설정
  - [ ] 연속 집계 재생성

- [ ] **pg_vector 업그레이드**
  - [ ] 확장 설치
  - [ ] 벡터 컬럼 추가
  - [ ] 벡터 인덱스 생성

- [ ] **검증 및 테스트**
  - [ ] 모든 객체 개수 확인
  - [ ] 기능 테스트
  - [ ] 성능 테스트

### 🚨 **주의사항**

1. **의존성 순서**: 함수 → 트리거 → 정책 순서로 복원
2. **권한 설정**: 소유자 및 권한 정보 별도 관리
3. **TimescaleDB**: 하이퍼테이블 변환 후 압축 정책 설정
4. **성능**: 대용량 데이터 복원 시 배치 처리 고려
5. **백업**: 각 단계별 백업 파일 보관

**성공적인 종합 DB 마이그레이션을 위한 완벽한 가이드입니다! 🚀**

