"""
Debug correlation analysis context
"""

import asyncio
import os
import sys
from pathlib import Path
import json

# Windows에서 asyncio 이벤트 루프 정책 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ksys_app.ai_engine.enhanced_agent_orchestrator import EnhancedResearchAgent, AgentContext


async def test_correlation_debug():
    """상관분석 컨텍스트 디버깅"""
    
    print("\n" + "="*60)
    print("Correlation Context Debug")
    print("="*60)
    
    # 데이터 수집 에이전트 생성
    collector = EnhancedResearchAgent()
    
    # 테스트 쿼리
    query = "D100과 D101의 상관성은?"
    
    print(f"\n[QUERY] {query}")
    print("-" * 40)
    
    # 컨텍스트 생성
    context = AgentContext(query=query)
    
    # 데이터 수집 실행
    result = await collector.process(context)
    
    print("\n[RAW DATA COLLECTED]")
    for key, value in result.raw_data.items():
        if key == 'correlation_stats' and value:
            print(f"\n{key}:")
            for stat in value:
                print(f"  - {stat}")
        elif key == 'correlation_samples' and value:
            print(f"\n{key}: {len(value)} samples")
            for sample in value[:3]:
                print(f"  - {sample}")
        elif key == 'error':
            print(f"\n{key}: {value}")
        else:
            print(f"\n{key}: {value}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    asyncio.run(test_correlation_debug())