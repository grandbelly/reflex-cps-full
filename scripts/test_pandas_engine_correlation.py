"""
PandasAnalysisEngine 상관분석 테스트 - 30일 데이터
"""

import asyncio
import os
import sys
from pathlib import Path
import logging

# Windows에서 asyncio 이벤트 루프 정책 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ksys_app.ai_engine.pandas_analysis_engine import PandasAnalysisEngine

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_pandas_correlation():
    """PandasAnalysisEngine으로 D100-D101 상관분석 테스트"""
    
    print("\n" + "="*60)
    print("PandasAnalysisEngine Correlation Test (30 days)")
    print("="*60)
    
    engine = PandasAnalysisEngine()
    
    # 30일(720시간) 데이터로 상관분석
    result = await engine.analyze_sensor_data(
        sensors=['D100', 'D101'],
        analysis_type='correlation',
        hours=720  # 30 days
    )
    
    print(f"\n[Analysis Result]")
    print(f"Title: {result.title}")
    print(f"Description: {result.description}")
    print(f"Confidence Score: {result.confidence_score:.2f}")
    print(f"Data Quality Score: {result.data_quality_score:.2f}")
    
    if result.correlations:
        print(f"\n[Correlations]")
        for key, value in result.correlations.items():
            print(f"  {key}: {value:.4f}")
    
    if result.insights:
        print(f"\n[Insights]")
        for i, insight in enumerate(result.insights, 1):
            print(f"  {i}. {insight}")
    
    if result.heatmap_data:
        print(f"\n[Heatmap Data]")
        if 'sensors' in result.heatmap_data:
            sensors = result.heatmap_data['sensors']
            print(f"  Sensors included: {sensors}")
            
            if 'pearson' in result.heatmap_data and len(sensors) >= 2:
                pearson = result.heatmap_data['pearson']
                print(f"\n  Pearson Correlations:")
                for s1 in sensors:
                    for s2 in sensors:
                        if s1 != s2 and s1 in pearson and s2 in pearson[s1]:
                            print(f"    {s1} <-> {s2}: {pearson[s1][s2]:.4f}")
                            break
            
            if 'spearman' in result.heatmap_data and len(sensors) >= 2:
                spearman = result.heatmap_data['spearman']
                print(f"\n  Spearman Correlations:")
                for s1 in sensors:
                    for s2 in sensors:
                        if s1 != s2 and s1 in spearman and s2 in spearman[s1]:
                            print(f"    {s1} <-> {s2}: {spearman[s1][s2]:.4f}")
                            break
    
    # 성공/실패 판정
    print("\n" + "="*60)
    if result.heatmap_data and 'sensors' in result.heatmap_data:
        sensors = result.heatmap_data['sensors']
        if 'D100' in sensors and 'D101' in sensors:
            print("[SUCCESS] Both D100 and D101 are included in the analysis!")
            if 'pearson' in result.heatmap_data:
                pearson = result.heatmap_data['pearson']
                if 'D100' in pearson and 'D101' in pearson['D100']:
                    print(f"D100-D101 Correlation: {pearson['D100']['D101']:.4f}")
        else:
            missing = []
            if 'D100' not in sensors:
                missing.append('D100')
            if 'D101' not in sensors:
                missing.append('D101')
            print(f"[WARNING] Missing sensors: {missing}")
    else:
        print("[FAIL] No correlation analysis results")
    print("="*60)


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    asyncio.run(test_pandas_correlation())