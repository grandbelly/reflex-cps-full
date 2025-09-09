#!/usr/bin/env python3
"""
판다스 분석 엔진 통합 테스트
Docker 빌드 완료 전 로컬 테스트용
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from ksys_app.ai_engine.pandas_analysis_engine import PandasAnalysisEngine
    from ksys_app.ai_engine.visualization_generator import generate_visualization_data, _convert_analysis_to_viz
    print("✅ 판다스 분석 엔진 임포트 성공")
except ImportError as e:
    print(f"❌ 임포트 오류: {e}")
    print("Docker 빌드 완료 후 테스트하세요.")
    exit(1)


async def test_pandas_analysis():
    """판다스 분석 엔진 기본 테스트"""
    print("\n🧪 판다스 분석 엔진 테스트 시작...")
    
    # 1. 엔진 초기화 테스트
    engine = PandasAnalysisEngine()
    print(f"✅ 엔진 초기화 완료: {engine.name}")
    
    # 2. 분석 시뮬레이션 (실제 DB 연결 없이)
    print("📊 분석 유형별 키워드 매핑 테스트...")
    
    # 키워드 매핑 테스트
    test_queries = [
        ("D101과 D102의 상관관계가 어떻게 되나요?", "correlation"),
        ("센서들의 시간대별 패턴을 히트맵으로 보여주세요", "heatmap"), 
        ("내일 D101 센서 값을 예측해주세요", "prediction"),
        ("이상한 센서 값이 있나 확인해주세요", "anomaly"),
        ("전체 시스템 종합 분석 결과를 알려주세요", "comprehensive")
    ]
    
    advanced_keywords = {
        'correlation': ['상관', '관계', '연관', '영향'],
        'prediction': ['예측', '미래', '추정', '예상'],
        'heatmap': ['히트맵', '패턴', '시간대', '분포'],
        'anomaly': ['이상', '비정상', '특이', '이상치'],
        'comprehensive': ['종합', '전체', '완전한', '모든']
    }
    
    for query, expected_type in test_queries:
        query_lower = query.lower()
        detected_type = None
        
        for analysis_type, keywords in advanced_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_type = analysis_type
                break
        
        result = "✅" if detected_type == expected_type else "❌"
        print(f"  {result} '{query}' → {detected_type} (예상: {expected_type})")
    
    print("\n🎯 키워드 매핑 테스트 완료")
    
    # 3. 시각화 데이터 변환 테스트 
    print("📈 시각화 데이터 변환 테스트...")
    
    # 가상의 분석 결과 생성
    from ksys_app.ai_engine.pandas_analysis_engine import AnalysisResult
    from datetime import datetime
    
    mock_result = AnalysisResult(
        analysis_type="correlation",
        title="테스트 상관관계 분석",
        description="D101-D102 상관관계 분석",
        insights=["높은 양의 상관관계 발견", "동시 증감 패턴 확인"],
        confidence_score=0.85,
        data_quality_score=0.92
    )
    
    # 히트맵 데이터 추가
    mock_result.heatmap_data = {
        'pearson': {
            'D101': {'D101': 1.0, 'D102': 0.78},
            'D102': {'D101': 0.78, 'D102': 1.0}
        },
        'sensors': ['D101', 'D102']
    }
    
    try:
        viz_data = await _convert_analysis_to_viz(mock_result)
        print("✅ 시각화 데이터 변환 성공")
        print(f"  - 데이터 키: {list(viz_data.keys())}")
        if 'correlation_heatmap' in viz_data:
            print(f"  - 상관관계 매트릭스: {len(viz_data['correlation_heatmap']['matrix'])}개 데이터")
        if 'analysis_metadata' in viz_data:
            print(f"  - 메타데이터: {viz_data['analysis_metadata']['type']}")
    except Exception as e:
        print(f"❌ 시각화 변환 오류: {e}")
    
    print("\n🎉 판다스 분석 엔진 기본 테스트 완료!")
    print("Docker 컨테이너 실행 후 실제 데이터베이스 연동 테스트를 진행하세요.")


if __name__ == "__main__":
    asyncio.run(test_pandas_analysis())