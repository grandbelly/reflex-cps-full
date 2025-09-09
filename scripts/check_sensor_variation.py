"""
센서 값 변동성 확인 스크립트
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


async def check_sensor_variation():
    """모든 D 시리즈 센서의 값 변동성 확인"""
    
    print("\n" + "="*60)
    print("Sensor Value Variation Check (Last 24 hours)")
    print("="*60)
    
    query = """
    SELECT 
        tag_name,
        COUNT(*) as count,
        MIN(value) as min_val,
        MAX(value) as max_val,
        AVG(value) as avg_val,
        STDDEV(value) as std_val,
        COUNT(DISTINCT value) as unique_values
    FROM public.influx_hist
    WHERE tag_name LIKE 'D%%'
        AND ts >= NOW() - INTERVAL '24 hours'
        AND value IS NOT NULL
    GROUP BY tag_name
    ORDER BY tag_name
    """
    
    result = await q(query, ())
    
    print("\n[Sensor Statistics]")
    print("-" * 80)
    print(f"{'Sensor':<10} {'Count':<8} {'Min':<10} {'Max':<10} {'Avg':<10} {'StdDev':<10} {'Unique':<8} {'Status':<15}")
    print("-" * 80)
    
    for row in result:
        tag = row['tag_name']
        count = row['count']
        min_val = row['min_val']
        max_val = row['max_val']
        avg_val = row['avg_val']
        std_val = row['std_val'] or 0
        unique = row['unique_values']
        
        # 상태 판단
        if unique == 1:
            status = "CONSTANT"
        elif std_val < 0.01:
            status = "NEARLY_CONST"
        elif std_val < 1:
            status = "LOW_VAR"
        else:
            status = "VARIABLE"
        
        print(f"{tag:<10} {count:<8} {min_val:<10.2f} {max_val:<10.2f} {avg_val:<10.2f} {std_val:<10.2f} {unique:<8} {status:<15}")
    
    # 상관분석 가능한 센서 쌍 찾기
    print("\n" + "="*60)
    print("Finding Sensor Pairs with Variation")
    print("="*60)
    
    variable_query = """
    SELECT 
        tag_name,
        STDDEV(value) as std_val
    FROM public.influx_hist
    WHERE tag_name LIKE 'D%%'
        AND ts >= NOW() - INTERVAL '24 hours'
        AND value IS NOT NULL
    GROUP BY tag_name
    HAVING STDDEV(value) > 0.1
    ORDER BY tag_name
    """
    
    variable_result = await q(variable_query, ())
    
    variable_sensors = [row['tag_name'] for row in variable_result]
    
    if len(variable_sensors) >= 2:
        print(f"\n[Variable Sensors Found]: {variable_sensors}")
        print(f"\nRecommended correlation pairs:")
        for i in range(len(variable_sensors)-1):
            for j in range(i+1, min(i+3, len(variable_sensors))):
                print(f"  - {variable_sensors[i]} vs {variable_sensors[j]}")
    else:
        print("\n[WARNING] Not enough variable sensors for correlation analysis")
        print(f"Variable sensors: {variable_sensors}")


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    asyncio.run(check_sensor_variation())