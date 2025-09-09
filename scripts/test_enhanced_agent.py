"""
Enhanced Agent Orchestrator 테스트 - 상관분석
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

from ksys_app.ai_engine.enhanced_agent_orchestrator import EnhancedResearchAgent, AgentContext


async def test_correlation_query():
    """상관분석 쿼리 테스트"""
    
    print("\n" + "="*60)
    print("Enhanced Agent Correlation Test")
    print("="*60)
    
    # 데이터 수집 에이전트 생성
    collector = EnhancedResearchAgent()
    
    # 테스트 쿼리들
    test_queries = [
        "D100과 D101의 상관성은?",
        "D100과 D101 상관분석",
        "D100 D101 관계",
        "D100만 보여줘",  # 단일 센서
        "전체 센서 상태"  # 전체
    ]
    
    for query in test_queries:
        print(f"\n[TEST] Query: {query}")
        print("-" * 40)
        
        # 컨텍스트 생성
        context = AgentContext(query=query)
        
        # 데이터 수집 실행
        result = await collector.process(context)
        
        # 결과 출력
        print(f"Query Type: {collector._classify_query(query)}")
        print(f"Data Keys: {list(result.raw_data.keys())}")
        
        # 상관분석 쿼리인 경우 상세 정보
        if "correlation_sensors" in result.raw_data:
            print(f"Correlation Sensors: {result.raw_data['correlation_sensors']}")
            
        if "target_sensors" in result.raw_data:
            print(f"Target Sensors: {result.raw_data['target_sensors']}")
            
        if "target_sensor" in result.raw_data:
            print(f"Target Sensor: {result.raw_data['target_sensor']}")
            
        if "sensor_data" in result.raw_data:
            print(f"Sensor Data Count: {len(result.raw_data['sensor_data'])}")
            
        if "correlation_stats" in result.raw_data:
            stats = result.raw_data['correlation_stats']
            print(f"Correlation Stats:")
            for stat in stats:
                print(f"  - {stat['tag_name']}: count={stat['count']}, std={stat.get('std_val', 0):.2f}")


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    asyncio.run(test_correlation_query())