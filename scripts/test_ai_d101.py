"""
Test D101 sensor through AI system
"""

import asyncio
import os
import sys
from pathlib import Path

# Windows에서 asyncio 이벤트 루프 정책 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ksys_app.ai_engine.enhanced_agent_orchestrator import get_enhanced_multi_agent_response, initialize_enhanced_multi_agent_system


async def test_ai_d101():
    """AI 시스템으로 D101 센서 상태 테스트"""
    
    print("\n" + "="*60)
    print("AI System D101 Sensor Test")
    print("="*60)
    
    # AI 시스템 초기화
    print("\n[INIT] Initializing AI System...")
    await initialize_enhanced_multi_agent_system()
    
    # D101 센서 상태 조회
    queries = [
        "D101 센서 현재 상태는?",
        "D101 센서 값 보여줘",
        "D101 상태 확인"
    ]
    
    for query in queries:
        print(f"\n[QUERY] {query}")
        print("-" * 40)
        
        try:
            response = await get_enhanced_multi_agent_response(query)
            
            if isinstance(response, dict):
                print(f"[TEXT] {response.get('text', 'No text')[:200]}")
                if 'visualizations' in response:
                    viz = response['visualizations']
                    if 'analysis_metadata' in viz:
                        meta = viz['analysis_metadata']
                        print(f"[META] Type: {meta.get('type')}, Score: {meta.get('confidence_score')}")
            else:
                print(f"[RESPONSE] {response[:200]}")
        except Exception as e:
            print(f"[ERROR] {e}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    # OpenAI API 키 설정
    os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', 'dummy-key')
    
    asyncio.run(test_ai_d101())