"""
D100과 D101 간단한 상관분석 테스트
"""

import asyncio
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Windows에서 asyncio 이벤트 루프 정책 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ksys_app.db import q


async def simple_correlation_test():
    """D100과 D101 상관분석 - 간단 버전"""
    
    print("\n" + "="*60)
    print("D100-D101 Simple Correlation Test")
    print("="*60)
    
    # 1. 데이터 가져오기
    query = """
    SELECT 
        ts,
        tag_name,
        value
    FROM public.influx_hist
    WHERE tag_name IN ('D100', 'D101')
        AND ts >= NOW() - INTERVAL '30 days'
        AND value IS NOT NULL
    ORDER BY ts, tag_name
    """
    
    result = await q(query, ())
    
    if not result:
        print("[ERROR] No data returned")
        return
    
    # 2. DataFrame 만들기
    data = []
    for row in result:
        data.append({
            'timestamp': row['ts'],
            'sensor': row['tag_name'],
            'value': float(row['value'])
        })
    
    df = pd.DataFrame(data)
    
    # 3. 센서별 데이터 개수 확인
    print("\n[Data Count]")
    print(df.groupby('sensor')['value'].count())
    
    # 4. 피벗 테이블 만들기 (시간별로 D100, D101 값)
    pivot_df = df.pivot_table(
        index='timestamp',
        columns='sensor',
        values='value',
        aggfunc='mean'
    )
    
    print(f"\n[Pivot Table Shape]: {pivot_df.shape}")
    print(f"[Columns]: {list(pivot_df.columns)}")
    
    # 5. 두 센서가 모두 있는지 확인
    if 'D100' not in pivot_df.columns or 'D101' not in pivot_df.columns:
        print("\n[ERROR] Missing sensor data")
        print(f"Available columns: {list(pivot_df.columns)}")
        return
    
    # 6. NaN 제거
    clean_df = pivot_df[['D100', 'D101']].dropna()
    print(f"\n[After removing NaN]: {len(clean_df)} rows")
    
    if len(clean_df) < 3:
        print("[ERROR] Not enough data for correlation (need at least 3 points)")
        return
    
    # 7. 상관계수 계산
    correlation = clean_df['D100'].corr(clean_df['D101'])
    
    print("\n" + "="*60)
    print("[RESULT]")
    print(f"D100-D101 Correlation: {correlation:.4f}")
    print("="*60)
    
    # 8. 데이터 샘플 보여주기
    print("\n[Sample Data (first 5 rows)]")
    print(clean_df.head())
    
    print("\n[Statistics]")
    print(clean_df.describe())


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    asyncio.run(simple_correlation_test())