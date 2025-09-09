"""
집계 테이블에서 변동성 있는 데이터 확인
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

from ksys_app.db import q


async def check_aggregated_data():
    """집계 테이블에서 데이터 변동성 확인"""
    
    print("\n" + "="*60)
    print("Checking Aggregated Tables for Data Variation")
    print("="*60)
    
    # 1분 집계 테이블 확인
    print("\n[1-Minute Aggregation Table: influx_agg_1m]")
    print("-" * 60)
    
    query_1m = """
    SELECT 
        tag_name,
        COUNT(*) as count,
        MIN(avg) as min_avg,
        MAX(avg) as max_avg,
        AVG(avg) as mean_avg,
        STDDEV(avg) as std_avg,
        COUNT(DISTINCT avg) as unique_values
    FROM influx_agg_1m
    WHERE tag_name LIKE 'D%%'
        AND bucket >= NOW() - INTERVAL '24 hours'
        AND avg IS NOT NULL
    GROUP BY tag_name
    ORDER BY tag_name
    LIMIT 20
    """
    
    result_1m = await q(query_1m, ())
    
    if result_1m:
        print(f"{'Sensor':<10} {'Count':<8} {'Min':<10} {'Max':<10} {'StdDev':<10} {'Unique':<8}")
        print("-" * 60)
        for row in result_1m:
            tag = row['tag_name']
            count = row['count']
            min_val = row['min_avg'] or 0
            max_val = row['max_avg'] or 0
            std_val = row['std_avg'] or 0
            unique = row['unique_values']
            
            print(f"{tag:<10} {count:<8} {min_val:<10.2f} {max_val:<10.2f} {std_val:<10.2f} {unique:<8}")
    else:
        print("No data found in influx_agg_1m")
    
    # 10분 집계 테이블 확인
    print("\n[10-Minute Aggregation Table: influx_agg_10m]")
    print("-" * 60)
    
    query_10m = """
    SELECT 
        tag_name,
        COUNT(*) as count,
        MIN(avg) as min_avg,
        MAX(avg) as max_avg,
        STDDEV(avg) as std_avg
    FROM influx_agg_10m
    WHERE tag_name LIKE 'D%%'
        AND bucket >= NOW() - INTERVAL '7 days'
        AND avg IS NOT NULL
    GROUP BY tag_name
    HAVING STDDEV(avg) > 0
    ORDER BY STDDEV(avg) DESC
    LIMIT 10
    """
    
    result_10m = await q(query_10m, ())
    
    if result_10m:
        print("Sensors with variation (StdDev > 0):")
        for row in result_10m:
            print(f"  - {row['tag_name']}: StdDev={row['std_avg']:.2f}, Range=[{row['min_avg']:.2f}, {row['max_avg']:.2f}]")
    else:
        print("No sensors with variation found in influx_agg_10m")
    
    # 최신 데이터 테이블 확인
    print("\n[Latest Values Table: influx_latest]")
    print("-" * 60)
    
    query_latest = """
    SELECT 
        tag_name,
        value,
        ts
    FROM influx_latest
    WHERE tag_name LIKE 'D%%'
    ORDER BY tag_name
    LIMIT 20
    """
    
    result_latest = await q(query_latest, ())
    
    if result_latest:
        print(f"{'Sensor':<10} {'Value':<15} {'Timestamp':<30}")
        print("-" * 60)
        for row in result_latest:
            print(f"{row['tag_name']:<10} {row['value']:<15.2f} {str(row['ts']):<30}")
    else:
        print("No data found in influx_latest")
    
    # 실시간 변동 테스트를 위한 짧은 시간 간격 체크
    print("\n[Real-time Variation Check (Last 1 hour)]")
    print("-" * 60)
    
    query_realtime = """
    SELECT 
        tag_name,
        MIN(value) as min_val,
        MAX(value) as max_val,
        COUNT(DISTINCT value) as unique_vals,
        MAX(ts) - MIN(ts) as time_range
    FROM influx_hist
    WHERE tag_name IN ('D100', 'D101', 'D102')
        AND ts >= NOW() - INTERVAL '1 hour'
    GROUP BY tag_name
    """
    
    result_rt = await q(query_realtime, ())
    
    if result_rt:
        for row in result_rt:
            print(f"{row['tag_name']}: {row['unique_vals']} unique values in {row['time_range']}")
            print(f"  Range: [{row['min_val']:.2f}, {row['max_val']:.2f}]")


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    asyncio.run(check_aggregated_data())