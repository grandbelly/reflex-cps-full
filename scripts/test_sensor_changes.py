"""
Test sensor changes compared to yesterday
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


async def test_sensor_changes():
    """어제와 오늘 센서 변화 비교"""
    
    print("\n" + "="*60)
    print("Sensor Changes Analysis (Yesterday vs Today)")
    print("="*60)
    
    # 시간 범위 설정
    now = datetime.now()
    yesterday_start = now - timedelta(days=2)
    yesterday_end = now - timedelta(days=1)
    today_start = now - timedelta(days=1)
    
    # 어제와 오늘의 평균값 비교 쿼리
    query = """
    WITH yesterday_data AS (
        SELECT 
            tag_name,
            AVG(value) as yesterday_avg,
            MIN(value) as yesterday_min,
            MAX(value) as yesterday_max,
            COUNT(*) as yesterday_count
        FROM influx_hist
        WHERE ts >= %s AND ts < %s
        GROUP BY tag_name
    ),
    today_data AS (
        SELECT 
            tag_name,
            AVG(value) as today_avg,
            MIN(value) as today_min,
            MAX(value) as today_max,
            COUNT(*) as today_count
        FROM influx_hist
        WHERE ts >= %s AND ts < %s
        GROUP BY tag_name
    )
    SELECT 
        COALESCE(y.tag_name, t.tag_name) as tag_name,
        y.yesterday_avg,
        t.today_avg,
        t.today_avg - y.yesterday_avg as avg_change,
        ABS((t.today_avg - y.yesterday_avg) / NULLIF(y.yesterday_avg, 0) * 100) as pct_change,
        y.yesterday_min,
        y.yesterday_max,
        t.today_min,
        t.today_max
    FROM yesterday_data y
    FULL OUTER JOIN today_data t ON y.tag_name = t.tag_name
    WHERE y.yesterday_avg IS NOT NULL AND t.today_avg IS NOT NULL
    ORDER BY ABS((t.today_avg - y.yesterday_avg) / NULLIF(y.yesterday_avg, 0)) DESC NULLS LAST
    LIMIT 10
    """
    
    result = await q(query, (yesterday_start, yesterday_end, today_start, now))
    
    print("\n[Top 10 Changed Sensors]")
    print("-" * 60)
    
    for row in result:
        tag = row.get('tag_name')
        yesterday_avg = row.get('yesterday_avg', 0)
        today_avg = row.get('today_avg', 0)
        avg_change = row.get('avg_change', 0)
        pct_change = row.get('pct_change', 0)
        
        change_sign = "↑" if avg_change > 0 else "↓" if avg_change < 0 else "→"
        
        print(f"\n{tag}:")
        print(f"  Yesterday Avg: {yesterday_avg:.2f}")
        print(f"  Today Avg: {today_avg:.2f}")
        print(f"  Change: {avg_change:+.2f} ({change_sign} {pct_change:.1f}%)")
        print(f"  Yesterday Range: [{row.get('yesterday_min', 0):.1f} - {row.get('yesterday_max', 0):.1f}]")
        print(f"  Today Range: [{row.get('today_min', 0):.1f} - {row.get('today_max', 0):.1f}]")
    
    # 변화가 큰 센서 요약
    print("\n" + "="*60)
    print("[Summary]")
    if result:
        top_sensor = result[0]
        print(f"Most changed sensor: {top_sensor.get('tag_name')}")
        print(f"Change: {top_sensor.get('pct_change', 0):.1f}%")
    
    print("="*60)


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    asyncio.run(test_sensor_changes())