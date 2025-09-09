#!/usr/bin/env python3
"""
스키마 전용 백업 스크립트
데이터는 제외하고 모든 DB 객체를 백업 (확장, 스키마, 테이블, 뷰, 함수, 트리거, 정책 등)
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Windows asyncio 이벤트 루프 문제 해결
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def schema_only_backup():
    """스키마 전용 백업 실행"""
    try:
        print("💾 스키마 전용 백업 시작! (데이터 제외)")
        print("=" * 60)
        
        # 백업 디렉토리 생성
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"ecoanp_schema_only_{timestamp}.sql"
        
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
                
                # 1. 설치된 확장 프로그램 정보
                print("\n📊 1단계: 설치된 확장 프로그램 정보")
                await cur.execute("""
                    SELECT 
                        extname as extension_name,
                        extversion as version,
                        extrelocatable as relocatable,
                        extowner::regrole as owner
                    FROM pg_extension 
                    ORDER BY extname
                """)
                extensions = await cur.fetchall()
                print(f"   설치된 확장: {len(extensions)}개")
                for ext in extensions:
                    print(f"     🔧 {ext[0]} v{ext[1]} (소유자: {ext[3]})")
                
                # 2. 사용 가능한 확장 프로그램
                print("\n📊 2단계: 사용 가능한 확장 프로그램")
                await cur.execute("""
                    SELECT 
                        name,
                        default_version,
                        installed_version,
                        comment
                    FROM pg_available_extensions 
                    WHERE name IN ('timescaledb', 'vector', 'plpython3u', 'plpython3', 'pg_stat_statements', 'uuid-ossp', 'pgcrypto')
                    ORDER BY name
                """)
                available_exts = await cur.fetchall()
                print(f"   주요 확장 정보:")
                for ext in available_exts:
                    status = "✅ 설치됨" if ext[2] else "❌ 미설치"
                    print(f"     {ext[0]}: {status} (기본: {ext[1]}, 설치: {ext[2] or 'N/A'})")
                
                # 3. 스키마 정보
                print("\n📊 3단계: 스키마 정보")
                await cur.execute("""
                    SELECT 
                        nspname as schema_name,
                        nspowner::regrole as owner,
                        nspacl as privileges
                    FROM pg_namespace 
                    WHERE nspname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                    ORDER BY nspname
                """)
                schemas = await cur.fetchall()
                print(f"   백업할 스키마: {len(schemas)}개")
                for schema in schemas:
                    print(f"     📁 {schema[0]} (소유자: {schema[1]})")
                
                # 4. 테이블 구조 (데이터 제외) - pg_get_tabledef 대신 간단한 정보만
                print("\n📊 4단계: 테이블 구조 정보")
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
                for table in tables:
                    print(f"     📋 {table[0]}.{table[1]} (소유자: {table[2]})")
                
                # 5. 뷰 정보
                print("\n📊 5단계: 뷰 정보")
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
                for view in views:
                    print(f"     👁️ {view[0]}.{view[1]} (소유자: {view[2]})")
                
                # 6. 함수 정보 (Python 함수 포함)
                print("\n📊 6단계: 함수 정보")
                await cur.execute("""
                    SELECT 
                        n.nspname as schema,
                        p.proname as function_name,
                        pg_get_functiondef(p.oid) as function_definition,
                        p.proowner::regrole as owner,
                        l.lanname as language
                    FROM pg_proc p
                    JOIN pg_namespace n ON p.pronamespace = n.oid
                    JOIN pg_language l ON p.prolang = l.oid
                    WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
                    AND p.prokind = 'f'  -- 일반 함수만 (집계 함수 제외)
                    ORDER BY n.nspname, p.proname
                """)
                functions = await cur.fetchall()
                print(f"   백업할 함수: {len(functions)}개")
                
                # Python 함수 개수 확인
                python_functions = [f for f in functions if f[4] in ['plpython3u', 'plpython3']]
                print(f"     🐍 Python 함수: {len(python_functions)}개")
                
                # 집계 함수 정보 (별도로 조회)
                print("\n📊 6-1단계: 집계 함수 정보")
                await cur.execute("""
                    SELECT 
                        n.nspname as schema,
                        p.proname as function_name,
                        p.proowner::regrole as owner,
                        l.lanname as language
                    FROM pg_proc p
                    JOIN pg_namespace n ON p.pronamespace = n.oid
                    JOIN pg_language l ON p.prolang = l.oid
                    WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
                    AND p.prokind = 'a'  -- 집계 함수만
                    ORDER BY n.nspname, p.proname
                """)
                aggregate_functions = await cur.fetchall()
                print(f"   백업할 집계 함수: {len(aggregate_functions)}개")
                for agg_func in aggregate_functions:
                    print(f"     📊 {agg_func[0]}.{agg_func[1]} (언어: {agg_func[3]})")
                
                # 7. 인덱스 정보
                print("\n📊 7단계: 인덱스 정보")
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
                
                # 8. 트리거 정보
                print("\n📊 8단계: 트리거 정보")
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
                
                # 9. 정책(Policies) 정보
                print("\n📊 9단계: 정책 정보")
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
                
                # 10. 제약조건 정보
                print("\n📊 10단계: 제약조건 정보")
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
                
                # 11. 시퀀스 정보
                print("\n📊 11단계: 시퀀스 정보")
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
                
                # 12. TimescaleDB 특화 정보
                print("\n📊 12단계: TimescaleDB 특화 정보")
                try:
                    await cur.execute("""
                        SELECT 
                            hypertable_name,
                            num_chunks,
                            compression_enabled
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
                
                # 13. 권한 정보
                print("\n📊 13단계: 권한 정보")
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
                
                print("\n🎉 스키마 전용 백업 정보 수집 완료!")
                print(f"\n📋 백업 요약:")
                print(f"   확장 프로그램: {len(extensions)}개")
                print(f"   스키마: {len(schemas)}개")
                print(f"   테이블: {len(tables)}개")
                print(f"   뷰: {len(views)}개")
                print(f"   함수: {len(functions)}개 (Python: {len(python_functions)}개)")
                print(f"   집계 함수: {len(aggregate_functions)}개")
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
                print(f"   1. pg_dump로 스키마만 백업 실행")
                print(f"   2. 새로운 TimescaleDB 환경에서 복원")
                print(f"   3. pg_vector 업그레이드 실행")
                print(f"   4. Python 함수 및 확장 프로그램 검증")
                
        await pool.close()
        
        # pg_dump로 실제 스키마 백업 실행
        print(f"\n🚀 pg_dump로 스키마 백업 실행 중...")
        pg_dump_cmd = [
            "pg_dump",
            "--host=192.168.1.80",
            "--port=5432",
            "--username=postgres",
            "--dbname=EcoAnP",
            "--schema-only",
            "--no-owner",
            "--no-privileges",
            f"--file={backup_file}"
        ]
        
        # 환경변수 설정
        env = os.environ.copy()
        env["PGPASSWORD"] = "admin"
        
        result = subprocess.run(pg_dump_cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ pg_dump 스키마 백업 성공!")
            print(f"📁 백업 파일: {backup_file}")
            print(f"📊 파일 크기: {backup_file.stat().st_size / 1024:.1f} KB")
        else:
            print(f"❌ pg_dump 실패:")
            print(f"   오류: {result.stderr}")
            print(f"   출력: {result.stdout}")
        
    except Exception as e:
        print(f"❌ 백업 실패: {e}")

async def main():
    """메인 함수"""
    await schema_only_backup()

if __name__ == "__main__":
    asyncio.run(main())
