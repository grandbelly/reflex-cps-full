#!/usr/bin/env python3
"""
현재 DB 구조 분석 스크립트
TimescaleDB + pg_vector 도커 환경 구축을 위한 정보 수집
"""

import asyncio
import os
import sys
from pathlib import Path

# Windows asyncio 이벤트 루프 문제 해결
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def analyze_database():
    """데이터베이스 구조 분석"""
    try:
        print("🔍 현재 DB 구조 분석 시작!")
        print("=" * 60)
        
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
                
                # 1. PostgreSQL 버전 및 확장 정보
                print("\n📊 1단계: PostgreSQL 버전 및 확장 정보")
                await cur.execute("SELECT version()")
                version = await cur.fetchone()
                print(f"   PostgreSQL 버전: {version[0]}")
                
                await cur.execute("SELECT * FROM pg_extension ORDER BY extname")
                extensions = await cur.fetchall()
                print(f"   설치된 확장: {[ext[0] for ext in extensions]}")
                
                # 2. 데이터베이스 크기 및 테이블 정보
                print("\n📊 2단계: 데이터베이스 크기 및 테이블 정보")
                await cur.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 20
                """)
                tables = await cur.fetchall()
                print(f"   주요 테이블 ({len(tables)}개):")
                for table in tables:
                    print(f"     {table[0]}.{table[1]} - {table[2]}")
                
                # 3. TimescaleDB 하이퍼테이블 정보
                print("\n📊 3단계: TimescaleDB 하이퍼테이블 정보")
                try:
                    await cur.execute("""
                        SELECT 
                            hypertable_name,
                            num_chunks,
                            compression_enabled,
                            is_distributed
                        FROM timescaledb_information.hypertables
                        ORDER BY num_chunks DESC
                    """)
                    hypertables = await cur.fetchall()
                    if hypertables:
                        print(f"   하이퍼테이블 ({len(hypertables)}개):")
                        for ht in hypertables:
                            print(f"     {ht[0]} - 청크: {ht[1]}, 압축: {ht[2]}, 분산: {ht[3]}")
                    else:
                        print("   하이퍼테이블 없음")
                except Exception as e:
                    print(f"   TimescaleDB 정보 조회 실패: {e}")
                
                # 4. 연속 집계 정보
                print("\n📊 4단계: 연속 집계 정보")
                try:
                    await cur.execute("""
                        SELECT 
                            view_name,
                            materialization_hypertable_name,
                            view_definition
                        FROM timescaledb_information.continuous_aggregates
                        ORDER BY view_name
                    """)
                    caggs = await cur.fetchall()
                    if caggs:
                        print(f"   연속 집계 ({len(caggs)}개):")
                        for cagg in caggs:
                            print(f"     {cagg[0]} -> {cagg[1]}")
                    else:
                        print("   연속 집계 없음")
                except Exception as e:
                    print(f"   연속 집계 정보 조회 실패: {e}")
                
                # 5. 뷰 정보
                print("\n📊 5단계: 뷰 정보")
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
                print(f"   뷰 ({len(views)}개):")
                for view in views:
                    print(f"     {view[0]}.{view[1]}")
                
                # 6. 함수 정보
                print("\n📊 6단계: 함수 정보")
                await cur.execute("""
                    SELECT 
                        n.nspname as schema,
                        p.proname as function_name,
                        pg_get_function_result(p.oid) as return_type
                    FROM pg_proc p
                    JOIN pg_namespace n ON p.pronamespace = n.oid
                    WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY p.proname
                """)
                functions = await cur.fetchall()
                print(f"   함수 ({len(functions)}개):")
                for func in functions:
                    print(f"     {func[0]}.{func[1]} -> {func[2]}")
                
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
                    ORDER BY tablename, indexname
                """)
                indexes = await cur.fetchall()
                print(f"   인덱스 ({len(indexes)}개):")
                for idx in indexes:
                    print(f"     {idx[0]}.{idx[1]}.{idx[2]}")
                
                # 8. 데이터베이스 크기
                print("\n📊 8단계: 데이터베이스 크기")
                await cur.execute("""
                    SELECT 
                        pg_size_pretty(pg_database_size(current_database())) as db_size
                """)
                db_size = await cur.fetchone()
                print(f"   데이터베이스 크기: {db_size[0]}")
                
                print("\n🎉 DB 구조 분석 완료!")
                print("\n📋 다음 단계:")
                print("1. TimescaleDB + pg_vector 도커 환경 구축")
                print("2. 현재 DB 백업 및 복원")
                print("3. 새로운 환경에서 테스트")
                
        await pool.close()
        
    except Exception as e:
        print(f"❌ DB 분석 실패: {e}")

async def main():
    """메인 함수"""
    await analyze_database()

if __name__ == "__main__":
    asyncio.run(main())
