#!/usr/bin/env python3
"""
RAG 시스템 디버깅 도구
======================
RAG 시스템의 각 구성 요소를 단계별로 테스트하고 디버깅합니다.
"""

import asyncio
import os
import sys
from datetime import datetime
import json
from typing import Dict, Any, List

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ksys_app.ksys_app import load_env
from ksys_app.db import q
from ksys_app.ai_engine.rag_engine import RAGEngine
# from ksys_app.ai_engine.knowledge_builder import search_knowledge, get_sensor_knowledge
from ksys_app.ai_engine.hallucination_prevention import HallucinationPrevention


class RAGDebugger:
    """RAG 시스템 디버거"""
    
    def __init__(self):
        self.rag_engine = None
        self.results = {}
        
    async def initialize(self):
        """환경 초기화"""
        print("\n" + "="*60)
        print("🔧 RAG 시스템 디버거 시작")
        print("="*60)
        
        # 환경변수 로드
        load_env()
        print("✅ 환경변수 로드 완료")
        
        # RAG 엔진 초기화
        self.rag_engine = RAGEngine()
        await self.rag_engine.initialize()
        print("✅ RAG 엔진 초기화 완료")
        
    async def test_database_connection(self):
        """데이터베이스 연결 테스트"""
        print("\n" + "-"*60)
        print("📊 1. 데이터베이스 연결 테스트")
        print("-"*60)
        
        try:
            # 테이블 존재 확인
            sql = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%knowledge%'
            """
            tables = await q(sql, ())
            
            if tables:
                print(f"✅ 지식베이스 테이블 발견: {len(tables)}개")
                for table in tables:
                    print(f"   - {table['table_name']}")
            else:
                print("⚠️ 지식베이스 테이블 없음")
                
            self.results['db_connection'] = {'status': 'success', 'tables': tables}
            
        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            self.results['db_connection'] = {'status': 'failed', 'error': str(e)}
            
    async def test_knowledge_cache(self):
        """지식베이스 캐시 테스트"""
        print("\n" + "-"*60)
        print("💾 2. 지식베이스 캐시 테스트")
        print("-"*60)
        
        try:
            # 캐시 상태 확인
            cache_size = len(self.rag_engine.knowledge_cache)
            print(f"📚 캐시된 지식 항목: {cache_size}개")
            
            if cache_size > 0:
                # 샘플 출력
                sample = self.rag_engine.knowledge_cache[0]
                print(f"\n📝 샘플 지식:")
                print(f"   - ID: {sample.get('id')}")
                print(f"   - 타입: {sample.get('content_type')}")
                print(f"   - 내용: {sample.get('content')[:100]}...")
                
                # 타입별 통계
                types = {}
                for item in self.rag_engine.knowledge_cache:
                    t = item.get('content_type', 'unknown')
                    types[t] = types.get(t, 0) + 1
                
                print(f"\n📊 타입별 통계:")
                for t, count in types.items():
                    print(f"   - {t}: {count}개")
                    
            self.results['knowledge_cache'] = {
                'status': 'success',
                'size': cache_size,
                'types': types if cache_size > 0 else {}
            }
            
        except Exception as e:
            print(f"❌ 캐시 테스트 실패: {e}")
            self.results['knowledge_cache'] = {'status': 'failed', 'error': str(e)}
            
    async def test_vectorizer(self):
        """벡터화 테스트"""
        print("\n" + "-"*60)
        print("🔢 3. TF-IDF 벡터화 테스트")
        print("-"*60)
        
        try:
            if self.rag_engine.vectorizer:
                print("✅ TF-IDF 벡터라이저 활성화")
                print(f"   - 특성 수: {self.rag_engine.vectorizer.max_features}")
                print(f"   - N-gram 범위: {self.rag_engine.vectorizer.ngram_range}")
                
                # 테스트 쿼리 벡터화
                test_query = "압력 센서 이상 징후"
                vector = self.rag_engine.vectorizer.transform([test_query])
                print(f"\n🔍 테스트 쿼리: '{test_query}'")
                print(f"   - 벡터 차원: {vector.shape}")
                print(f"   - 0이 아닌 특성: {vector.nnz}개")
                
                self.results['vectorizer'] = {
                    'status': 'active',
                    'features': self.rag_engine.vectorizer.max_features,
                    'test_vector_dim': vector.shape
                }
            else:
                print("⚠️ 벡터라이저 비활성화")
                self.results['vectorizer'] = {'status': 'inactive'}
                
        except Exception as e:
            print(f"❌ 벡터화 테스트 실패: {e}")
            self.results['vectorizer'] = {'status': 'failed', 'error': str(e)}
            
    async def test_semantic_search(self):
        """의미론적 검색 테스트"""
        print("\n" + "-"*60)
        print("🔍 4. 의미론적 검색 테스트")
        print("-"*60)
        
        test_queries = [
            "압력 센서 이상",
            "온도가 높을 때",
            "시스템 정상 범위",
            "D100 센서"
        ]
        
        search_results = {}
        
        for query in test_queries:
            try:
                print(f"\n🔍 쿼리: '{query}'")
                results = await self.rag_engine.semantic_search(query, top_k=3)
                
                if results:
                    print(f"   ✅ {len(results)}개 결과 발견")
                    for i, result in enumerate(results[:2], 1):
                        print(f"   {i}. 유사도: {result.get('similarity', 0):.3f}")
                        print(f"      내용: {result.get('content', '')[:50]}...")
                else:
                    print("   ⚠️ 검색 결과 없음")
                    
                search_results[query] = len(results)
                
            except Exception as e:
                print(f"   ❌ 검색 실패: {e}")
                search_results[query] = f"error: {e}"
                
        self.results['semantic_search'] = search_results
        
    async def test_openai_integration(self):
        """OpenAI 통합 테스트"""
        print("\n" + "-"*60)
        print("🤖 5. OpenAI API 통합 테스트")
        print("-"*60)
        
        try:
            if self.rag_engine.openai_client:
                print("✅ OpenAI 클라이언트 활성화")
                
                # API 키 마스킹 출력
                from ksys_app.utils.secure_config import get_api_key_manager
                api_manager = get_api_key_manager()
                api_key = api_manager.get_openai_key()
                if api_key:
                    masked = api_manager.secure_config.mask_api_key(api_key)
                    print(f"   - API 키: {masked}")
                    
                    # 간단한 테스트 요청
                    test_prompt = "Say 'RAG test successful' if you can read this."
                    response = await self.rag_engine.openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": test_prompt}],
                        max_tokens=50
                    )
                    
                    if response.choices:
                        print(f"   - 테스트 응답: {response.choices[0].message.content}")
                        self.results['openai'] = {'status': 'active', 'test': 'success'}
                    else:
                        print("   ⚠️ 응답 없음")
                        self.results['openai'] = {'status': 'active', 'test': 'no_response'}
                else:
                    print("⚠️ API 키 없음")
                    self.results['openai'] = {'status': 'no_key'}
            else:
                print("⚠️ OpenAI 클라이언트 비활성화")
                self.results['openai'] = {'status': 'inactive'}
                
        except Exception as e:
            print(f"❌ OpenAI 테스트 실패: {e}")
            self.results['openai'] = {'status': 'failed', 'error': str(e)}
            
    async def test_hallucination_prevention(self):
        """할루시네이션 방지 테스트"""
        print("\n" + "-"*60)
        print("🛡️ 6. 할루시네이션 방지 시스템 테스트")
        print("-"*60)
        
        try:
            if self.rag_engine.hallucination_prevention:
                print("✅ 할루시네이션 방지 시스템 활성화")
                
                # 테스트 응답
                test_responses = [
                    "D100 센서의 압력이 150 kPa입니다.",  # 정상적인 응답
                    "D999 센서가 고장났습니다.",  # 존재하지 않는 센서
                    "압력이 -500 kPa입니다.",  # 불가능한 값
                ]
                
                for response in test_responses:
                    print(f"\n📝 테스트: '{response[:50]}...'")
                    result = await self.rag_engine.hallucination_prevention.validate_response(
                        response, {"query": "센서 상태 확인"}
                    )
                    
                    if result.is_valid:
                        print(f"   ✅ 검증 통과 (신뢰도: {result.confidence:.2f})")
                    else:
                        print(f"   ⚠️ 검증 실패: {', '.join(result.issues)}")
                        
                self.results['hallucination'] = {'status': 'active', 'tests': len(test_responses)}
                
            else:
                print("⚠️ 할루시네이션 방지 시스템 비활성화")
                self.results['hallucination'] = {'status': 'inactive'}
                
        except Exception as e:
            print(f"❌ 할루시네이션 테스트 실패: {e}")
            self.results['hallucination'] = {'status': 'failed', 'error': str(e)}
            
    async def test_rag_response(self):
        """RAG 응답 생성 테스트"""
        print("\n" + "-"*60)
        print("💬 7. RAG 응답 생성 테스트")
        print("-"*60)
        
        test_queries = [
            "현재 시스템 상태는?",
            "D100 센서의 압력은?",
            "이상 징후가 있나요?"
        ]
        
        for query in test_queries:
            try:
                print(f"\n❓ 질문: '{query}'")
                
                # 컨텍스트 구축
                context = await self.rag_engine.build_context(query)
                
                if context:
                    print(f"   📚 컨텍스트 구축 완료:")
                    print(f"      - 센서 데이터: {len(context.get('sensors', []))}개")
                    print(f"      - QC 규칙: {len(context.get('qc_rules', []))}개")
                    print(f"      - 지식베이스: {len(context.get('knowledge', []))}개")
                    
                    # 응답 생성
                    response = await self.rag_engine.generate(query, context)
                    
                    if response:
                        print(f"   💬 응답: {response[:100]}...")
                    else:
                        print("   ⚠️ 응답 생성 실패")
                else:
                    print("   ⚠️ 컨텍스트 구축 실패")
                    
            except Exception as e:
                print(f"   ❌ 테스트 실패: {e}")
                
    def print_summary(self):
        """테스트 요약 출력"""
        print("\n" + "="*60)
        print("📊 테스트 요약")
        print("="*60)
        
        for test_name, result in self.results.items():
            status = result.get('status', 'unknown')
            
            if status == 'success' or status == 'active':
                symbol = "✅"
            elif status == 'inactive' or status == 'no_key':
                symbol = "⚠️"
            else:
                symbol = "❌"
                
            print(f"{symbol} {test_name}: {status}")
            
            # 상세 정보 출력
            if test_name == 'knowledge_cache' and 'size' in result:
                print(f"   - 캐시 크기: {result['size']}개")
            elif test_name == 'semantic_search' and isinstance(result, dict):
                for q, r in result.items():
                    if isinstance(r, int):
                        print(f"   - '{q}': {r}개 결과")
                        
        print("\n" + "="*60)
        print("🔧 디버깅 완료")
        print("="*60)


async def main():
    """메인 실행 함수"""
    debugger = RAGDebugger()
    
    try:
        # 초기화
        await debugger.initialize()
        
        # 각 구성 요소 테스트
        await debugger.test_database_connection()
        await debugger.test_knowledge_cache()
        await debugger.test_vectorizer()
        await debugger.test_semantic_search()
        await debugger.test_openai_integration()
        await debugger.test_hallucination_prevention()
        await debugger.test_rag_response()
        
        # 요약 출력
        debugger.print_summary()
        
    except Exception as e:
        print(f"\n❌ 디버거 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())