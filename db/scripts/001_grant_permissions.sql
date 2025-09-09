-- TASK_001: 테이블 접근 권한 설정
-- 작성일: 2025-09-08
-- 목적: ai_knowledge_base 테이블에 대한 접근 권한 설정

-- 애플리케이션 사용자 역할 생성 (이미 존재하는 경우 무시)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ksys_app_user') THEN
        CREATE ROLE ksys_app_user;
    END IF;
END
$$;

-- ai_knowledge_base 테이블 권한 부여
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_knowledge_base TO ksys_app_user;
GRANT USAGE, SELECT ON SEQUENCE ai_knowledge_base_id_seq TO ksys_app_user;

-- 읽기 전용 역할 생성
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ksys_readonly') THEN
        CREATE ROLE ksys_readonly;
    END IF;
END
$$;

-- 읽기 전용 권한 부여
GRANT SELECT ON ai_knowledge_base TO ksys_readonly;
GRANT USAGE ON SEQUENCE ai_knowledge_base_id_seq TO ksys_readonly;

-- 관리자 역할에 모든 권한 부여
GRANT ALL PRIVILEGES ON ai_knowledge_base TO postgres;
GRANT ALL PRIVILEGES ON SEQUENCE ai_knowledge_base_id_seq TO postgres;

-- 권한 확인 쿼리
SELECT 
    grantee,
    table_name,
    privilege_type
FROM 
    information_schema.role_table_grants
WHERE 
    table_name = 'ai_knowledge_base'
ORDER BY 
    grantee, privilege_type;