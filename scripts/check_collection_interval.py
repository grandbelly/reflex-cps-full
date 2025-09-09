"""
Check actual data collection interval
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


async def check_interval():
    """Check actual collection interval"""
    
    query = """
    WITH time_diffs AS (
        SELECT 
            tag_name,
            ts,
            LAG(ts) OVER (PARTITION BY tag_name ORDER BY ts) as prev_ts,
            EXTRACT(EPOCH FROM (ts - LAG(ts) OVER (PARTITION BY tag_name ORDER BY ts))) as seconds_diff
        FROM influx_hist
        WHERE ts >= NOW() - INTERVAL '1 hour'
        AND tag_name = 'D100'
        ORDER BY ts DESC
        LIMIT 100
    )
    SELECT 
        AVG(seconds_diff) as avg_interval,
        MIN(seconds_diff) as min_interval,
        MAX(seconds_diff) as max_interval,
        COUNT(*) as sample_count
    FROM time_diffs
    WHERE seconds_diff IS NOT NULL
    """
    
    result = await q(query, ())
    
    if result:
        data = result[0]
        print(f"Average interval: {data['avg_interval']:.2f} seconds")
        print(f"Min interval: {data['min_interval']:.2f} seconds")
        print(f"Max interval: {data['max_interval']:.2f} seconds")
        print(f"Sample count: {data['sample_count']}")
        
        # Calculate expected records per hour
        if data['avg_interval']:
            expected_per_hour = 3600 / data['avg_interval']
            expected_per_day = 86400 / data['avg_interval']
            print(f"\nExpected records per hour: {expected_per_hour:.0f}")
            print(f"Expected records per day: {expected_per_day:.0f}")


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    asyncio.run(check_interval())