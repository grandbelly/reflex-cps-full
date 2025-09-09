"""
Test correlation data collection
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Windows에서 asyncio 이벤트 루프 정책 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ksys_app.db import q


async def test_correlation_data():
    """상관분석 데이터 수집 테스트"""
    
    print("\n" + "="*60)
    print("Correlation Data Collection Test")
    print("="*60)
    
    sensor_tags = ['D100', 'D101']
    start_date = datetime.now() - timedelta(days=30)
    
    # 통계 쿼리 테스트
    print("\n[1] Testing statistics query...")
    placeholders = ', '.join(['%s'] * len(sensor_tags))
    hist_query = f'''
    SELECT tag_name, 
           COUNT(*) as count,
           MIN(value) as min_val, 
           MAX(value) as max_val,
           AVG(value) as avg_val,
           STDDEV(value) as std_val
    FROM public.influx_hist 
    WHERE ts >= %s AND tag_name IN ({placeholders})
    GROUP BY tag_name
    '''
    
    params = [start_date] + sensor_tags
    result = await q(hist_query, tuple(params))
    
    print(f"Statistics result: {len(result)} records")
    for row in result:
        print(f"  - {row}")
    
    # 샘플 데이터 쿼리 테스트
    print("\n[2] Testing sample data query...")
    for tag in sensor_tags:
        sample_query = '''
        SELECT tag_name, ts, value
        FROM public.influx_hist
        WHERE tag_name = %s AND ts >= %s
        ORDER BY ts DESC
        LIMIT 5
        '''
        sample_result = await q(sample_query, (tag, start_date))
        
        print(f"\nSample data for {tag}: {len(sample_result)} records")
        for row in sample_result[:3]:  # 처음 3개만 출력
            print(f"  - {row}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    asyncio.run(test_correlation_data())