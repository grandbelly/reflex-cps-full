#!/usr/bin/env python3
"""
Simple RAG test with debug logging
"""

import asyncio
import sys
import os

# Add project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ksys_app.ksys_app import load_env
from ksys_app.ai_engine.rag_engine import RAGEngine

async def test_rag():
    """Test RAG with debug logs"""
    
    print("\n" + "="*60)
    print("🧪 RAG 시스템 간단 테스트")
    print("="*60)
    
    # Load environment
    load_env()
    print("✅ 환경변수 로드 완료")
    
    # Initialize RAG
    rag_engine = RAGEngine()
    await rag_engine.initialize()
    print("✅ RAG 엔진 초기화 완료")
    
    # Test queries
    test_queries = [
        "현재 시스템 상태는?",
        "D100 센서 값은?",
        "압력 센서 이상 징후"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"📝 질문: {query}")
        print("="*60)
        
        try:
            # Build context
            print("📚 컨텍스트 구축 중...")
            context = await rag_engine.build_context(query)
            
            print(f"\n📊 결과:")
            print(f"  - 센서 태그: {context['sensor_tags']}")
            print(f"  - 현재 데이터: {len(context['current_data'])}개")
            print(f"  - 관련 지식: {len(context['relevant_knowledge'])}개")
            
            # Check if we have data
            if context['current_data']:
                print(f"  ✅ 데이터 기반 응답 가능")
                for data in context['current_data'][:2]:
                    print(f"    - {data['tag_name']}: {data.get('value', 'N/A')}")
            elif context['relevant_knowledge']:
                print(f"  📚 지식베이스 기반 응답")
                for knowledge in context['relevant_knowledge'][:2]:
                    print(f"    - {knowledge['content'][:50]}...")
            else:
                print("  ⚠️ 관련 데이터/지식 없음")
                
        except Exception as e:
            print(f"❌ 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ 테스트 완료")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_rag())