#!/usr/bin/env python3
"""
현재 DB 백업 스크립트
TimescaleDB + pg_vector 도커 환경으로 마이그레이션하기 위한 백업
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Windows asyncio 이벤트 루프 문제 해결
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def backup_database():
    """데이터베이스 백업 실행"""
    try:
        print("💾 현재 DB 백업 시작!")
        print("=" * 50)
        
        # 백업 디렉토리 생성
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"ecoanp_backup_{timestamp}.sql"
        
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
                
                # 2. 테이블 구조 백업
                print("\n📊 2단계: 테이블 구조 백업")
                for table in tables:
                    schema, table_name = table[0], table[1]
                    print(f"   📋 {schema}.{table_name}")
                    
                    # CREATE TABLE 문 생성
                    await cur.execute(f"""
                        SELECT 
                            'CREATE TABLE ' || quote_ident(schemaname) || '.' || quote_ident(tablename) || ' (' ||
                            string_agg(
                                quote_ident(attname) || ' ' || format_type(atttypid, atttypmod) ||
                                CASE WHEN attnotnull THEN ' NOT NULL' ELSE '' END ||
                                CASE WHEN atthasdef THEN ' DEFAULT ' || pg_get_expr(adbin, adrelid) ELSE '' END,
                                ', '
                                ORDER BY attnum
                            ) || ');' as create_statement
                        FROM pg_attribute
                        JOIN pg_class ON attrelid = pg_class.oid
                        JOIN pg_namespace ON pg_class.relnamespace = pg_namespace.oid
                        LEFT JOIN pg_attrdef ON attrelid = adrelid AND attnum = adnum
                        WHERE nspname = %s AND relname = %s AND attnum > 0 AND NOT attisdropped
                        GROUP BY schemaname, tablename
                    """, (schema, table_name))
                    
                    create_stmt = await cur.fetchone()
                    if create_stmt:
                        print(f"     ✅ 구조 백업 완료")
                
                # 3. 데이터 백업 (ai_knowledge_base만)
                print("\n📊 3단계: 중요 데이터 백업")
                await cur.execute("""
                    SELECT COUNT(*) FROM ai_knowledge_base
                """)
                count = await cur.fetchone()[0]
                print(f"   ai_knowledge_base 레코드: {count}개")
                
                # 4. 뷰 정보 백업
                print("\n📊 4단계: 뷰 정보 백업")
                await cur.execute("""
                    SELECT 
                        schemaname,
                        viewname,
                        definition
                    FROM pg_views 
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY viewname
                """)
                views = await cur.fetchall()
                print(f"   백업할 뷰: {len(views)}개")
                
                # 5. 함수 정보 백업
                print("\n📊 5단계: 함수 정보 백업")
                await cur.execute("""
                    SELECT 
                        n.nspname as schema,
                        p.proname as function_name,
                        pg_get_functiondef(p.oid) as function_definition
                    FROM pg_proc p
                    JOIN pg_namespace n ON p.pronamespace = n.oid
                    WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY p.proname
                """)
                functions = await cur.fetchall()
                print(f"   백업할 함수: {len(functions)}개")
                
                print("\n🎉 DB 백업 정보 수집 완료!")
                print(f"\n📋 백업 요약:")
                print(f"   테이블: {len(tables)}개")
                print(f"   뷰: {len(views)}개")
                print(f"   함수: {len(functions)}개")
                print(f"   ai_knowledge_base 레코드: {count}개")
                print(f"\n💡 다음 단계:")
                print(f"   1. pg_dump로 전체 백업 실행")
                print(f"   2. 새로운 TimescaleDB 환경에서 복원")
                print(f"   3. pg_vector 업그레이드 실행")
                
        await pool.close()
        
    except Exception as e:
        print(f"❌ 백업 실패: {e}")

async def main():
    """메인 함수"""
    await backup_database()

if __name__ == "__main__":
    asyncio.run(main())

