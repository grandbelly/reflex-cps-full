#!/usr/bin/env python3
"""
시스템 전체 디버깅 스크립트
각 컴포넌트를 개별적으로 테스트하여 문제점을 식별합니다.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_environment():
    """환경 변수 테스트"""
    print("🔍 1. 환경 변수 테스트")
    print("-" * 40)
    
    required_vars = [
        'TS_DSN',
        'POSTGRES_CONNECTION_STRING', 
        'OPENAI_API_KEY',
        'APP_ENV',
        'TZ'
    ]
    
    all_good = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            display_value = "***" if "key" in var.lower() or "dsn" in var.lower() else value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: Not set")
            all_good = False
    
    print(f"\n환경 변수 상태: {'✅ 정상' if all_good else '❌ 문제 있음'}\n")
    return all_good

async def test_database():
    """데이터베이스 연결 테스트"""
    print("🗄️ 2. 데이터베이스 연결 테스트")
    print("-" * 40)
    
    try:
        # Load environment first
        from ksys_app.ksys_app import load_env
        load_env()
        
        from ksys_app.db import q
        
        # Test basic connection
        result = await q("SELECT 1 as test", ())
        if result and result[0]['test'] == 1:
            print("✅ 기본 데이터베이스 연결 성공")
        else:
            print("❌ 데이터베이스 연결 실패")
            return False
        
        # Test table existence
        tables_to_check = [
            'public.influx_latest',
            'public.influx_qc_rule'
        ]
        
        for table in tables_to_check:
            try:
                result = await q(f"SELECT COUNT(*) as count FROM {table} LIMIT 1", ())
                count = result[0]['count'] if result else 0
                print(f"✅ {table}: {count}개 레코드")
            except Exception as e:
                print(f"❌ {table}: 테이블 없음 또는 접근 불가 - {e}")
        
        print("✅ 데이터베이스 연결 테스트 완료\n")
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}\n")
        return False

async def test_rag_engine():
    """RAG 엔진 테스트"""
    print("🧠 3. RAG 엔진 테스트")
    print("-" * 40)
    
    try:
        from ksys_app.ai_engine.rag_engine import rag_engine, initialize_rag_engine
        
        # Initialize RAG engine
        print("RAG 엔진 초기화 중...")
        await initialize_rag_engine()
        print("✅ RAG 엔진 초기화 성공")
        
        # Test OpenAI client
        if rag_engine.openai_client:
            print("✅ OpenAI 클라이언트 연결됨")
        else:
            print("⚠️ OpenAI 클라이언트 없음 (템플릿 모드)")
        
        # Test knowledge cache
        if rag_engine.knowledge_cache:
            print(f"✅ 지식베이스: {len(rag_engine.knowledge_cache)}개 항목")
        else:
            print("⚠️ 지식베이스 비어있음 (OpenAI 전용 모드)")
            
        print("✅ RAG 엔진 테스트 완료\n")
        return True
        
    except Exception as e:
        print(f"❌ RAG 엔진 테스트 실패: {e}\n")
        return False

async def test_multi_agent():
    """Multi-Agent 시스템 테스트"""
    print("🤖 4. Multi-Agent 시스템 테스트")
    print("-" * 40)
    
    try:
        from ksys_app.ai_engine.agent_orchestrator import orchestrator, initialize_multi_agent_system
        from ksys_app.ai_engine.rag_engine import rag_engine
        
        # Initialize Multi-Agent system
        print("Multi-Agent 시스템 초기화 중...")
        await initialize_multi_agent_system(rag_engine)
        print("✅ Multi-Agent 시스템 초기화 성공")
        
        # Test OpenAI client
        if orchestrator.openai_client:
            print("✅ Multi-Agent OpenAI 클라이언트 연결됨")
        else:
            print("⚠️ Multi-Agent OpenAI 클라이언트 없음")
        
        print("✅ Multi-Agent 시스템 테스트 완료\n")
        return True
        
    except Exception as e:
        print(f"❌ Multi-Agent 시스템 테스트 실패: {e}\n")
        return False

async def test_sensor_data():
    """센서 데이터 쿼리 테스트"""
    print("📊 5. 센서 데이터 쿼리 테스트")
    print("-" * 40)
    
    try:
        from ksys_app.queries.latest import latest_snapshot
        from ksys_app.queries.qc import qc_rules
        
        # Test latest snapshot
        latest_data = await latest_snapshot(None)
        if latest_data:
            print(f"✅ 최신 센서 데이터: {len(latest_data)}개")
            print(f"   샘플: {latest_data[0]['tag_name']} = {latest_data[0].get('value', 'N/A')}")
        else:
            print("❌ 센서 데이터 없음")
        
        # Test QC rules
        qc_data = await qc_rules(None)
        if qc_data:
            print(f"✅ QC 규칙: {len(qc_data)}개")
        else:
            print("⚠️ QC 규칙 없음")
            
        print("✅ 센서 데이터 쿼리 테스트 완료\n")
        return True
        
    except Exception as e:
        print(f"❌ 센서 데이터 쿼리 테스트 실패: {e}\n")
        return False

async def test_ai_response():
    """AI 응답 생성 테스트"""
    print("💬 6. AI 응답 생성 테스트")
    print("-" * 40)
    
    try:
        from ksys_app.ai_engine.agent_orchestrator import get_multi_agent_response
        
        test_query = "D101 센서 현재 상태는?"
        print(f"테스트 쿼리: {test_query}")
        
        response = await get_multi_agent_response(test_query)
        if response and len(response) > 10:
            print("✅ AI 응답 생성 성공")
            print(f"응답 길이: {len(response)} 문자")
            print(f"응답 미리보기: {response[:100]}...")
        else:
            print(f"⚠️ AI 응답이 너무 짧거나 비어있음: {response}")
            
        print("✅ AI 응답 생성 테스트 완료\n")
        return True
        
    except Exception as e:
        print(f"❌ AI 응답 생성 테스트 실패: {e}\n")
        return False

async def main():
    """메인 디버깅 함수"""
    print("🚀 KSys AI System 전체 디버깅 시작")
    print("=" * 50)
    
    tests = [
        ("환경 변수", test_environment),
        ("데이터베이스", test_database), 
        ("RAG 엔진", test_rag_engine),
        ("Multi-Agent", test_multi_agent),
        ("센서 데이터", test_sensor_data),
        ("AI 응답", test_ai_response)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 예외 발생: {e}")
            results[test_name] = False
    
    print("📋 최종 디버깅 결과")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\n전체 시스템 상태: {'✅ 정상' if all_passed else '❌ 문제 있음'}")
    
    if not all_passed:
        print("\n🔧 권장사항:")
        print("- 실패한 컴포넌트를 개별적으로 수정")
        print("- 환경 변수 및 데이터베이스 연결 확인")
        print("- OpenAI API 키 유효성 검증")

if __name__ == "__main__":
    asyncio.run(main())