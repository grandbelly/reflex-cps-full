"""
Test D101 sensor status
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

from ksys_app.queries.latest import latest_snapshot
from ksys_app.queries.qc import qc_rules


async def test_d101_sensor():
    """D101 센서 상태 테스트"""
    
    print("\n" + "="*60)
    print("D101 Sensor Status Test")
    print("="*60)
    
    # D101 현재 데이터 가져오기
    print("\n[1] Fetching D101 current data...")
    d101_data = await latest_snapshot('D101')
    
    if d101_data:
        for data in d101_data:
            print(f"  Tag: {data.get('tag_name')}")
            print(f"  Value: {data.get('value')}")
            print(f"  Timestamp: {data.get('ts')}")
    else:
        print("  No data found for D101")
    
    # D101 QC 규칙 가져오기
    print("\n[2] Fetching D101 QC rules...")
    d101_qc = await qc_rules('D101')
    
    if d101_qc:
        for rule in d101_qc:
            print(f"  Min: {rule.get('min_val')}, Max: {rule.get('max_val')}")
            print(f"  Warning: {rule.get('warn_min')} - {rule.get('warn_max')}")
            print(f"  Critical: {rule.get('crit_min')} - {rule.get('crit_max')}")
    else:
        print("  No QC rules found for D101")
    
    # 상태 판정
    if d101_data and d101_qc:
        value = d101_data[0].get('value', 0)
        rule = d101_qc[0]
        
        status = 'normal'
        if value < rule.get('crit_min', 0) or value > rule.get('crit_max', 200):
            status = 'critical'
        elif value < rule.get('warn_min', 10) or value > rule.get('warn_max', 180):
            status = 'warning'
        
        print(f"\n[3] D101 Status: {status.upper()}")
        print(f"  Current value: {value}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    asyncio.run(test_d101_sensor())