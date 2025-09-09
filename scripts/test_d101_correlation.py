"""
D101 상관분석 테스트 스크립트
센서 데이터 필터링 문제 해결 확인
"""

import asyncio
import os
import sys
from pathlib import Path
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ksys_app.ai_engine.pandas_analysis_engine import PandasAnalysisEngine
from ksys_app.db import q

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_d101_correlation():
    """D100과 D101 상관분석 테스트"""
    
    print("\n" + "="*60)
    print("[TEST] D101 Correlation Analysis Test Start")
    print("="*60)
    
    # 1. 먼저 데이터베이스에서 직접 데이터 확인
    print("\n[Step 1] Database Direct Query")
    print("-" * 40)
    
    check_query = """
    SELECT 
        tag_name,
        COUNT(*) as count,
        MIN(value) as min_val,
        MAX(value) as max_val,
        AVG(value) as avg_val
    FROM public.influx_hist
    WHERE tag_name IN ('D100', 'D101')
        AND ts >= NOW() - INTERVAL '24 hours'
        AND value IS NOT NULL
    GROUP BY tag_name
    ORDER BY tag_name
    """
    
    result = await q(check_query, ())
    
    print("DB에서 직접 조회한 결과:")
    for row in result:
        print(f"  - {row['tag_name']}: {row['count']}개 레코드")
        print(f"    범위: {row['min_val']:.2f} ~ {row['max_val']:.2f}")
        print(f"    평균: {row['avg_val']:.2f}")
    
    # 2. 필터링 조건 적용 후 데이터 확인
    print("\n[Step 2] After Filtering Conditions")
    print("-" * 40)
    
    filtered_query = """
    SELECT 
        tag_name,
        COUNT(*) as count,
        MIN(value) as min_val,
        MAX(value) as max_val,
        AVG(value) as avg_val
    FROM public.influx_hist
    WHERE tag_name IN ('D100', 'D101')
        AND ts >= NOW() - INTERVAL '24 hours'
        AND value IS NOT NULL
        AND (
            (tag_name LIKE 'D1%' AND value >= -50 AND value <= 500)
        )
    GROUP BY tag_name
    ORDER BY tag_name
    """
    
    filtered_result = await q(filtered_query, ())
    
    print("필터링 후 결과:")
    for row in filtered_result:
        print(f"  - {row['tag_name']}: {row['count']}개 레코드")
        print(f"    범위: {row['min_val']:.2f} ~ {row['max_val']:.2f}")
    
    # 3. PandasAnalysisEngine 테스트
    print("\n[Step 3] PandasAnalysisEngine Correlation Test")
    print("-" * 40)
    
    engine = PandasAnalysisEngine()
    
    # 상관분석 실행
    result = await engine.analyze_sensor_data(
        sensors=['D100', 'D101'],
        analysis_type='correlation',
        hours=24
    )
    
    print(f"\n분석 결과:")
    print(f"  - 제목: {result.title}")
    print(f"  - 설명: {result.description}")
    
    if result.correlations:
        print(f"\n상관계수:")
        for key, value in result.correlations.items():
            print(f"  - {key}: {value:.3f}")
    
    if result.insights:
        print(f"\n인사이트:")
        for insight in result.insights:
            print(f"  - {insight}")
    
    if result.heatmap_data:
        print(f"\n히트맵 데이터:")
        if 'sensors' in result.heatmap_data:
            print(f"  - 포함된 센서: {result.heatmap_data['sensors']}")
        if 'pearson' in result.heatmap_data:
            pearson = result.heatmap_data['pearson']
            if 'D100' in pearson and 'D101' in pearson.get('D100', {}):
                print(f"  - D100-D101 상관계수: {pearson['D100']['D101']:.3f}")
    
    # 4. 최종 검증
    print("\n" + "="*60)
    print("[FINAL] Verification Result:")
    print("-" * 40)
    
    if result.heatmap_data and 'sensors' in result.heatmap_data:
        sensors = result.heatmap_data['sensors']
        if 'D100' in sensors and 'D101' in sensors:
            print("[SUCCESS] Both D100 and D101 are included in correlation analysis!")
            print(f"   포함된 센서: {sensors}")
        elif 'D100' in sensors:
            print("[WARNING] Only D100 is included, D101 is missing")
        elif 'D101' in sensors:
            print("[WARNING] Only D101 is included, D100 is missing")
        else:
            print("[FAIL] Both D100 and D101 are missing")
    else:
        print("[FAIL] No correlation analysis result")
    
    print("="*60)


async def test_value_ranges():
    """센서별 실제 값 범위 확인"""
    
    print("\n" + "="*60)
    print("[CHECK] Sensor Value Ranges")
    print("="*60)
    
    query = """
    SELECT 
        SUBSTRING(tag_name, 1, 2) as sensor_prefix,
        COUNT(DISTINCT tag_name) as sensor_count,
        MIN(value) as min_val,
        MAX(value) as max_val,
        AVG(value) as avg_val,
        STDDEV(value) as std_val
    FROM public.influx_hist
    WHERE tag_name LIKE 'D%'
        AND ts >= NOW() - INTERVAL '7 days'
        AND value IS NOT NULL
    GROUP BY SUBSTRING(tag_name, 1, 2)
    ORDER BY sensor_prefix
    """
    
    result = await q(query, ())
    
    print("\n센서 프리픽스별 값 범위 (최근 7일):")
    print("-" * 40)
    for row in result:
        print(f"\n{row['sensor_prefix']}xx 시리즈 ({row['sensor_count']}개 센서):")
        print(f"  - 최소값: {row['min_val']:.2f}")
        print(f"  - 최대값: {row['max_val']:.2f}")
        print(f"  - 평균값: {row['avg_val']:.2f}")
        print(f"  - 표준편차: {row['std_val']:.2f}")
        
        # 권장 필터 범위 제안
        suggested_min = row['min_val'] - (row['std_val'] * 3)
        suggested_max = row['max_val'] + (row['std_val'] * 3)
        print(f"  [RECOMMEND] Filter range: {suggested_min:.0f} ~ {suggested_max:.0f}")


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['POSTGRES_CONNECTION_STRING'] = os.getenv(
        'POSTGRES_CONNECTION_STRING',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    # 테스트 실행
    asyncio.run(test_d101_correlation())
    asyncio.run(test_value_ranges())