"""
Test warning sensor query through AI system
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


async def test_warning_sensors():
    """AI 시스템으로 경고 센서 조회 테스트"""
    
    print("\n" + "="*60)
    print("AI System Warning Sensors Test")
    print("="*60)
    
    # AI 시스템 초기화
    print("\n[INIT] Initializing AI System...")
    await initialize_enhanced_multi_agent_system()
    
    # 경고 센서 조회 쿼리
    query = "경고 상태인 센서 있어?"
    
    print(f"\n[QUERY] {query}")
    print("-" * 40)
    
    try:
        response = await get_enhanced_multi_agent_response(query)
        
        if isinstance(response, dict):
            print(f"\n[RESPONSE]")
            print(response.get('text', 'No response'))
        else:
            print(f"\n[RESPONSE]")
            print(response)
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
    
    asyncio.run(test_warning_sensors())