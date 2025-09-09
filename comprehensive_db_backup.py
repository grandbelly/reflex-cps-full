#!/usr/bin/env python3
"""
종합 DB 백업 스크립트
TimescaleDB + pg_vector 도커 환경으로 마이그레이션하기 위한 모든 DB 객체 백업
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Windows asyncio 이벤트 루프 문제 해결
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def comprehensive_backup():
    """종합 데이터베이스 백업 실행"""
    try:
        print("💾 종합 DB 백업 시작!")
        print("=" * 60)
        
        # 백업 디렉토리 생성
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"ecoanp_comprehensive_backup_{timestamp}.sql"
        
        print(f"📁 백업 파일: {backup_file}")
        
        # psycopg 직접 import
        import psycopg
        from psycopg_pool import AsyncConnectionPool
        
        # 연결 문자열 설정
        dsn = "postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable"
        print(f"🔗 데이터베이스 연결: {dsn}")
        
        # 연결 풀 생성
        pool = AsyncConnectionPool(dsn, min_size=1, max_size=5)
        
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                print("✅ 데이터베이스 연결 성공!")
                
                # 1. 스키마 정보 백업
                print("\n📊 1단계: 스키마 정보 백업")
                await cur.execute("""
                    SELECT 
                        nspname as schema_name,
                        nspowner::regrole as owner
                    FROM pg_namespace 
                    WHERE nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                    ORDER BY nspname
                """)
                schemas = await cur.fetchall()
                print(f"   백업할 스키마: {len(schemas)}개")
                
                # 2. 테이블 정보 백업
                print("\n📊 2단계: 테이블 정보 백업")
                await cur.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        tableowner,
                        tablespace,
                        hasindexes,
                        hasrules,
                        hastriggers,
                        rowsecurity
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog', '_timescaledb_catalog', '_timescaledb_internal')
                    ORDER BY schemaname, tablename
                """)
                tables = await cur.fetchall()
                print(f"   백업할 테이블: {len(tables)}개")
                
                # 3. 뷰 정보 백업
                print("\n📊 3단계: 뷰 정보 백업")
                await cur.execute("""
                    SELECT 
                        schemaname,
                        viewname,
                        viewowner,
                        definition
                    FROM pg_views 
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY schemaname, viewname
                """)
                views = await cur.fetchall()
                print(f"   백업할 뷰: {len(views)}개")
                
                # 4. 함수 정보 백업
                print("\n📊 4단계: 함수 정보 백업")
                await cur.execute("""
                    SELECT 
                        n.nspname as schema,
                        p.proname as function_name,
                        pg_get_functiondef(p.oid) as function_definition,
                        p.proowner::regrole as owner
                    FROM pg_proc p
                    JOIN pg_namespace n ON p.pronamespace = n.oid
                    WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY n.nspname, p.proname
                """)
                functions = await cur.fetchall()
                print(f"   백업할 함수: {len(functions)}개")
                
                # 5. 인덱스 정보 백업
                print("\n📊 5단계: 인덱스 정보 백업")
                await cur.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes 
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY schemaname, tablename, indexname
                """)
                indexes = await cur.fetchall()
                print(f"   백업할 인덱스: {len(indexes)}개")
                
                # 6. 트리거 정보 백업
                print("\n📊 6단계: 트리거 정보 백업")
                await cur.execute("""
                    SELECT 
                        n.nspname as schema,
                        t.tgname as trigger_name,
                        c.relname as table_name,
                        p.proname as function_name,
                        t.tgenabled as enabled,
                        t.tgtype as trigger_type
                    FROM pg_trigger t
                    JOIN pg_class c ON t.tgrelid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    JOIN pg_proc p ON t.tgfoid = p.oid
                    WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
                    AND NOT t.tgisinternal
                    ORDER BY n.nspname, c.relname, t.tgname
                """)
                triggers = await cur.fetchall()
                print(f"   백업할 트리거: {len(triggers)}개")
                
                # 7. 정책(Policies) 정보 백업
                print("\n📊 7단계: 정책 정보 백업")
                await cur.execute("""
                    SELECT 
                        n.nspname as schema,
                        c.relname as table_name,
                        pol.polname as policy_name,
                        pol.polcmd as command,
                        pol.polroles as roles,
                        pol.polqual as using_expression,
                        pol.polwithcheck as with_check_expression
                    FROM pg_policy pol
                    JOIN pg_class c ON pol.polrelid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY n.nspname, c.relname, pol.polname
                """)
                policies = await cur.fetchall()
                print(f"   백업할 정책: {len(policies)}개")
                
                # 8. 제약조건 정보 백업
                print("\n📊 8단계: 제약조건 정보 백업")
                await cur.execute("""
                    SELECT 
                        n.nspname as schema,
                        c.relname as table_name,
                        con.conname as constraint_name,
                        con.contype as constraint_type,
                        pg_get_constraintdef(con.oid) as constraint_definition
                    FROM pg_constraint con
                    JOIN pg_class c ON con.conrelid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY n.nspname, c.relname, con.conname
                """)
                constraints = await cur.fetchall()
                print(f"   백업할 제약조건: {len(constraints)}개")
                
                # 9. 시퀀스 정보 백업
                print("\n📊 9단계: 시퀀스 정보 백업")
                await cur.execute("""
                    SELECT 
                        n.nspname as schema,
                        c.relname as sequence_name,
                        c.relowner::regrole as owner
                    FROM pg_class c
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE c.relkind = 'S'
                    AND n.nspname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY n.nspname, c.relname
                """)
                sequences = await cur.fetchall()
                print(f"   백업할 시퀀스: {len(sequences)}개")
                
                # 10. TimescaleDB 특화 정보 백업
                print("\n📊 10단계: TimescaleDB 특화 정보 백업")
                try:
                    await cur.execute("""
                        SELECT 
                            hypertable_name,
                            num_chunks,
                            compression_enabled,
                            is_distributed
                        FROM timescaledb_information.hypertables
                        ORDER BY hypertable_name
                    """)
                    hypertables = await cur.fetchall()
                    print(f"   TimescaleDB 하이퍼테이블: {len(hypertables)}개")
                    
                    await cur.execute("""
                        SELECT 
                            view_name,
                            materialization_hypertable_name,
                            view_definition
                        FROM timescaledb_information.continuous_aggregates
                        ORDER BY view_name
                    """)
                    caggs = await cur.fetchall()
                    print(f"   연속 집계: {len(caggs)}개")
                    
                except Exception as e:
                    print(f"   TimescaleDB 정보 조회 실패: {e}")
                
                # 11. 권한 정보 백업
                print("\n📊 11단계: 권한 정보 백업")
                await cur.execute("""
                    SELECT 
                        n.nspname as schema,
                        c.relname as object_name,
                        c.relkind as object_type,
                        array_agg(DISTINCT pr.privilege_type) as privileges,
                        array_agg(DISTINCT pr.grantee) as grantees
                    FROM pg_class c
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    LEFT JOIN information_schema.role_table_grants pr ON 
                        pr.table_schema = n.nspname AND pr.table_name = c.relname
                    WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
                    GROUP BY n.nspname, c.relname, c.relkind
                    ORDER BY n.nspname, c.relname
                """)
                permissions = await cur.fetchall()
                print(f"   백업할 권한 정보: {len(permissions)}개")
                
                print("\n🎉 종합 DB 백업 정보 수집 완료!")
                print(f"\n📋 백업 요약:")
                print(f"   스키마: {len(schemas)}개")
                print(f"   테이블: {len(tables)}개")
                print(f"   뷰: {len(views)}개")
                print(f"   함수: {len(functions)}개")
                print(f"   인덱스: {len(indexes)}개")
                print(f"   트리거: {len(triggers)}개")
                print(f"   정책: {len(policies)}개")
                print(f"   제약조건: {len(constraints)}개")
                print(f"   시퀀스: {len(sequences)}개")
                print(f"   권한: {len(permissions)}개")
                
                if 'hypertables' in locals():
                    print(f"   TimescaleDB 하이퍼테이블: {len(hypertables)}개")
                if 'caggs' in locals():
                    print(f"   연속 집계: {len(caggs)}개")
                
                print(f"\n💡 다음 단계:")
                print(f"   1. pg_dump로 전체 백업 실행 (권장)")
                print(f"   2. 새로운 TimescaleDB 환경에서 복원")
                print(f"   3. pg_vector 업그레이드 실행")
                print(f"   4. 정책 및 함수 검증")
                
        await pool.close()
        
    except Exception as e:
        print(f"❌ 백업 실패: {e}")

async def main():
    """메인 함수"""
    await comprehensive_backup()

if __name__ == "__main__":
    asyncio.run(main())

