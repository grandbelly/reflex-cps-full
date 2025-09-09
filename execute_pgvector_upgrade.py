#!/usr/bin/env python3
"""
pg_vector 업그레이드 실행 스크립트
Docker 환경의 PostgreSQL에 직접 연결하여 업그레이드를 수행합니다.
"""

import asyncio
import os
import sys
from pathlib import Path

# Windows asyncio 이벤트 루프 문제 해결
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ksys_app.db import q, execute_query


async def check_database_connection():
    """데이터베이스 연결 확인"""
    try:
        # 간단한 쿼리로 연결 테스트
        result = await q("SELECT version()", ())
        print(f"✅ 데이터베이스 연결 성공: {result[0]['version'][:50]}...")
        return True
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return False


async def check_pgvector_extension():
    """pg_vector 확장 설치 확인"""
    try:
        result = await q("SELECT * FROM pg_extension WHERE extname = 'vector'", ())
        if result:
            print("✅ pg_vector 확장이 이미 설치되어 있습니다.")
            return True
        else:
            print("⚠️ pg_vector 확장이 설치되지 않았습니다.")
            return False
    except Exception as e:
        print(f"❌ pg_vector 확장 확인 실패: {e}")
        return False


async def install_pgvector_extension():
    """pg_vector 확장 설치"""
    try:
        print("🔧 pg_vector 확장 설치 중...")
        await execute_query("CREATE EXTENSION IF NOT EXISTS vector", ())
        print("✅ pg_vector 확장 설치 완료!")
        return True
    except Exception as e:
        print(f"❌ pg_vector 확장 설치 실패: {e}")
        return False


async def check_ai_knowledge_base_table():
    """ai_knowledge_base 테이블 존재 확인"""
    try:
        result = await q("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'ai_knowledge_base'
        """, ())
        
        if result:
            print("✅ ai_knowledge_base 테이블이 존재합니다.")
            return True
        else:
            print("⚠️ ai_knowledge_base 테이블이 존재하지 않습니다.")
            return False
    except Exception as e:
        print(f"❌ 테이블 확인 실패: {e}")
        return False


async def add_vector_column():
    """벡터 컬럼 추가"""
    try:
        print("🔧 content_embedding 벡터 컬럼 추가 중...")
        
        # 컬럼이 이미 존재하는지 확인
        result = await q("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ai_knowledge_base' 
            AND column_name = 'content_embedding'
        """, ())
        
        if result:
            print("✅ content_embedding 컬럼이 이미 존재합니다.")
            return True
        
        # 벡터 컬럼 추가
        await execute_query("""
            ALTER TABLE ai_knowledge_base 
            ADD COLUMN content_embedding vector(1536)
        """, ())
        
        print("✅ content_embedding 벡터 컬럼 추가 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 벡터 컬럼 추가 실패: {e}")
        return False


async def create_vector_indexes():
    """벡터 인덱스 생성"""
    try:
        print("🔧 벡터 인덱스 생성 중...")
        
        # HNSW 벡터 인덱스
        await execute_query("""
            CREATE INDEX IF NOT EXISTS idx_ai_knowledge_vector 
            ON ai_knowledge_base 
            USING hnsw (content_embedding vector_cosine_ops)
        """, ())
        
        # 메타데이터 JSONB 인덱스
        await execute_query("""
            CREATE INDEX IF NOT EXISTS idx_ai_knowledge_metadata 
            ON ai_knowledge_base 
            USING GIN (metadata)
        """, ())
        
        # 컨텐츠 타입 인덱스
        await execute_query("""
            CREATE INDEX IF NOT EXISTS idx_ai_knowledge_content_type 
            ON ai_knowledge_base (content_type)
        """, ())
        
        # 하이브리드 검색을 위한 텍스트 인덱스
        await execute_query("""
            CREATE INDEX IF NOT EXISTS idx_ai_knowledge_hybrid 
            ON ai_knowledge_base 
            USING GIN (to_tsvector('english', content))
        """, ())
        
        print("✅ 벡터 인덱스 생성 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 벡터 인덱스 생성 실패: {e}")
        return False


async def create_search_functions():
    """검색 함수 생성"""
    try:
        print("🔧 검색 함수 생성 중...")
        
        # 벡터 검색 함수
        await execute_query("""
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
        """, ())
        
        # 하이브리드 검색 함수
        await execute_query("""
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
        """, ())
        
        print("✅ 검색 함수 생성 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 검색 함수 생성 실패: {e}")
        return False


async def create_monitoring_views():
    """모니터링 뷰 생성"""
    try:
        print("🔧 모니터링 뷰 생성 중...")
        
        # 지식베이스 통계 뷰
        await execute_query("""
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
        """, ())
        
        print("✅ 모니터링 뷰 생성 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 모니터링 뷰 생성 실패: {e}")
        return False


async def verify_upgrade():
    """업그레이드 검증"""
    try:
        print("🔍 업그레이드 검증 중...")
        
        # pg_vector 확장 확인
        ext_result = await q("SELECT * FROM pg_extension WHERE extname = 'vector'", ())
        if not ext_result:
            print("❌ pg_vector 확장이 설치되지 않았습니다.")
            return False
        
        # 벡터 컬럼 확인
        col_result = await q("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'ai_knowledge_base' 
            AND column_name = 'content_embedding'
        """, ())
        if not col_result:
            print("❌ content_embedding 컬럼이 생성되지 않았습니다.")
            return False
        
        # 인덱스 확인
        idx_result = await q("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'ai_knowledge_base' 
            AND indexname LIKE '%vector%'
        """, ())
        if not idx_result:
            print("❌ 벡터 인덱스가 생성되지 않았습니다.")
            return False
        
        # 함수 확인
        func_result = await q("""
            SELECT proname 
            FROM pg_proc 
            WHERE proname IN ('search_knowledge_vector', 'search_knowledge_hybrid')
        """, ())
        if len(func_result) < 2:
            print("❌ 검색 함수가 제대로 생성되지 않았습니다.")
            return False
        
        print("✅ 모든 업그레이드 항목이 성공적으로 완료되었습니다!")
        return True
        
    except Exception as e:
        print(f"❌ 업그레이드 검증 실패: {e}")
        return False


async def main():
    """메인 업그레이드 프로세스"""
    print("🚀 pg_vector RAG Knowledge Base 업그레이드 시작!")
    print("=" * 60)
    
    # 1. 데이터베이스 연결 확인
    if not await check_database_connection():
        print("❌ 데이터베이스 연결을 확인할 수 없습니다. 업그레이드를 중단합니다.")
        return
    
    # 2. ai_knowledge_base 테이블 확인
    if not await check_ai_knowledge_base_table():
        print("❌ ai_knowledge_base 테이블이 존재하지 않습니다. 업그레이드를 중단합니다.")
        return
    
    # 3. pg_vector 확장 설치
    if not await check_pgvector_extension():
        if not await install_pgvector_extension():
            print("❌ pg_vector 확장 설치에 실패했습니다. 업그레이드를 중단합니다.")
            return
    
    # 4. 벡터 컬럼 추가
    if not await add_vector_column():
        print("❌ 벡터 컬럼 추가에 실패했습니다. 업그레이드를 중단합니다.")
        return
    
    # 5. 벡터 인덱스 생성
    if not await create_vector_indexes():
        print("❌ 벡터 인덱스 생성에 실패했습니다. 업그레이드를 중단합니다.")
        return
    
    # 6. 검색 함수 생성
    if not await create_search_functions():
        print("❌ 검색 함수 생성에 실패했습니다. 업그레이드를 중단합니다.")
        return
    
    # 7. 모니터링 뷰 생성
    if not await create_monitoring_views():
        print("❌ 모니터링 뷰 생성에 실패했습니다. 업그레이드를 중단합니다.")
        return
    
    # 8. 업그레이드 검증
    if not await verify_upgrade():
        print("❌ 업그레이드 검증에 실패했습니다.")
        return
    
    print("=" * 60)
    print("🎉 pg_vector 업그레이드가 성공적으로 완료되었습니다!")
    print("\n📋 다음 단계:")
    print("1. OpenAI API 키 설정")
    print("2. 새로운 RAG 엔진 테스트")
    print("3. 기존 지식 임베딩 생성")
    print("4. 성능 테스트 및 비교")


if __name__ == "__main__":
    # 환경변수 설정 (필요시)
    if not os.getenv("TS_DSN"):
        print("⚠️ TS_DSN 환경변수가 설정되지 않았습니다.")
        print("Docker 환경의 DB 연결 정보를 사용합니다.")
        os.environ["TS_DSN"] = "postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable"
    
    asyncio.run(main())
