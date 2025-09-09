#!/usr/bin/env python3
"""
간단한 pg_vector 업그레이드 스크립트
직접 psycopg를 사용하여 PostgreSQL에 연결하고 업그레이드를 수행합니다.
"""

import asyncio
import os
import sys
from pathlib import Path

# Windows asyncio 이벤트 루프 문제 해결
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def upgrade_pgvector():
    """pg_vector 업그레이드 실행"""
    try:
        print("🚀 pg_vector 업그레이드 시작!")
        print("=" * 50)
        
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
                
                # 1. pg_vector 확장 설치
                print("\n🔧 1단계: pg_vector 확장 설치")
                try:
                    await cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    print("✅ pg_vector 확장 설치 완료")
                except Exception as e:
                    print(f"⚠️ pg_vector 확장 설치 실패 (이미 설치됨): {e}")
                
                # 2. ai_knowledge_base 테이블 확인
                print("\n🔍 2단계: ai_knowledge_base 테이블 확인")
                await cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = 'ai_knowledge_base'
                """)
                result = await cur.fetchone()
                if result:
                    print("✅ ai_knowledge_base 테이블 존재 확인")
                else:
                    print("❌ ai_knowledge_base 테이블이 존재하지 않습니다.")
                    return
                
                # 3. 벡터 컬럼 추가
                print("\n🔧 3단계: content_embedding 벡터 컬럼 추가")
                try:
                    await cur.execute("""
                        ALTER TABLE ai_knowledge_base 
                        ADD COLUMN IF NOT EXISTS content_embedding vector(1536)
                    """)
                    print("✅ content_embedding 벡터 컬럼 추가 완료")
                except Exception as e:
                    print(f"⚠️ 벡터 컬럼 추가 실패 (이미 존재): {e}")
                
                # 4. 벡터 인덱스 생성
                print("\n🔧 4단계: 벡터 인덱스 생성")
                try:
                    await cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_ai_knowledge_vector 
                        ON ai_knowledge_base 
                        USING hnsw (content_embedding vector_cosine_ops)
                    """)
                    print("✅ HNSW 벡터 인덱스 생성 완료")
                except Exception as e:
                    print(f"⚠️ 벡터 인덱스 생성 실패 (이미 존재): {e}")
                
                # 5. 메타데이터 인덱스 생성
                print("\n🔧 5단계: 메타데이터 인덱스 생성")
                try:
                    await cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_ai_knowledge_metadata 
                        ON ai_knowledge_base 
                        USING GIN (metadata)
                    """)
                    print("✅ 메타데이터 GIN 인덱스 생성 완료")
                except Exception as e:
                    print(f"⚠️ 메타데이터 인덱스 생성 실패 (이미 존재): {e}")
                
                # 6. 검색 함수 생성
                print("\n🔧 6단계: 벡터 검색 함수 생성")
                try:
                    await cur.execute("""
                        CREATE OR REPLACE FUNCTION search_knowledge_vector(
                            query_embedding vector(1536),
                            match_threshold float DEFAULT 0.7,
                            match_count int DEFAULT 5
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
                            ORDER BY akb.content_embedding <=> query_embedding
                            LIMIT match_count;
                        END;
                        $$;
                    """)
                    print("✅ 벡터 검색 함수 생성 완료")
                except Exception as e:
                    print(f"⚠️ 검색 함수 생성 실패: {e}")
                
                # 7. 업그레이드 검증
                print("\n🔍 7단계: 업그레이드 검증")
                
                # pg_vector 확장 확인
                await cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
                if await cur.fetchone():
                    print("✅ pg_vector 확장 확인됨")
                else:
                    print("❌ pg_vector 확장이 설치되지 않음")
                    return
                
                # 벡터 컬럼 확인
                await cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'ai_knowledge_base' 
                    AND column_name = 'content_embedding'
                """)
                if await cur.fetchone():
                    print("✅ content_embedding 벡터 컬럼 확인됨")
                else:
                    print("❌ content_embedding 컬럼이 생성되지 않음")
                    return
                
                # 인덱스 확인
                await cur.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'ai_knowledge_base' 
                    AND indexname LIKE '%vector%'
                """)
                if await cur.fetchone():
                    print("✅ 벡터 인덱스 확인됨")
                else:
                    print("❌ 벡터 인덱스가 생성되지 않음")
                    return
                
                print("\n🎉 pg_vector 업그레이드가 성공적으로 완료되었습니다!")
                print("\n📋 다음 단계:")
                print("1. OpenAI API 키 설정")
                print("2. 새로운 RAG 엔진 테스트")
                print("3. 기존 지식 임베딩 생성")
                print("4. 성능 테스트 및 비교")
                
        await pool.close()
        
    except Exception as e:
        print(f"❌ 업그레이드 실패: {e}")
        print("\n💡 해결 방법:")
        print("1. PostgreSQL 서버가 실행 중인지 확인")
        print("2. IP 주소 192.168.1.80:5432에 접근 가능한지 확인")
        print("3. 사용자명/비밀번호가 올바른지 확인")

async def main():
    """메인 함수"""
    await upgrade_pgvector()

if __name__ == "__main__":
    asyncio.run(main())

