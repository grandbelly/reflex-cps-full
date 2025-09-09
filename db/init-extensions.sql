
-- 핵심 확장 설치
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb_toolkit') THEN
    EXECUTE 'CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'plpython3u') THEN
    EXECUTE 'CREATE EXTENSION IF NOT EXISTS plpython3u';
  END IF;
END $$;

-- Python 확장 설치 (사용 가능한 것만)
-- plpython3u는 Alpine 패키지에서 지원되지 않을 수 있음

-- 금융 분석용 확장 설치
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 확장 정보 확인
SELECT 
    extname,
    extversion,
    extrelocatable
FROM pg_extension 
WHERE extname IN ('timescaledb', 'timescaledb_toolkit', 'vector', 'plpython3u', 'pg_stat_statements', 'uuid-ossp', 'pgcrypto')
ORDER BY extname;

-- TimescaleDB 버전 정보
SELECT default_version, installed_version 
FROM pg_available_extensions 
WHERE name = 'timescaledb';

-- pg_vector 버전 정보
SELECT default_version, installed_version 
FROM pg_available_extensions 
WHERE name = 'vector';

-- Python 확장 버전 정보
SELECT default_version, installed_version 
FROM pg_available_extensions 
WHERE name IN ('plpython3u', 'plpython3');

-- 금융 확장 버전 정보
SELECT default_version, installed_version 
FROM pg_available_extensions 
WHERE name IN ('pg_stat_statements', 'uuid-ossp', 'pgcrypto');

-- 확장 설정 확인
SHOW shared_preload_libraries;

-- Python 함수는 plpython3u 확장이 사용 가능할 때만 생성

-- 성공 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ TimescaleDB + pg_vector 확장 초기화 완료!';
    RAISE NOTICE '📊 TimescaleDB: %', (SELECT installed_version FROM pg_available_extensions WHERE name = 'timescaledb');
    RAISE NOTICE '🔍 pg_vector: %', (SELECT installed_version FROM pg_available_extensions WHERE name = 'vector');
    RAISE NOTICE '💰 추가 확장: pg_stat_statements, uuid-ossp, pgcrypto 설치됨';
END $$;
