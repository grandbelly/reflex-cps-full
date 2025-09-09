#!/usr/bin/env python3
"""
AI Insights 테스트 시나리오
==========================
RAG 시스템의 다양한 질의를 테스트합니다.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List

# 프로젝트 경로 설정
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ksys_app.ksys_app import load_env
from ksys_app.ai_engine.rag_engine import RAGEngine


class AITestRunner:
    """AI 테스트 실행기"""
    
    def __init__(self):
        self.rag_engine = None
        self.test_results = []
        
    async def setup(self):
        """환경 설정"""
        print("\n" + "="*60)
        print("🧪 AI Insights 테스트 시나리오 실행")
        print("="*60)
        
        # 환경변수 로드
        load_env()
        
        # RAG 엔진 초기화
        self.rag_engine = RAGEngine()
        await self.rag_engine.initialize()
        print("✅ RAG 엔진 초기화 완료\n")
        
    async def run_test_scenario(self, scenario_name: str, query: str) -> Dict:
        """테스트 시나리오 실행"""
        print(f"\n{'='*60}")
        print(f"📝 시나리오: {scenario_name}")
        print(f"❓ 질문: {query}")
        print("="*60)
        
        start_time = datetime.now()
        
        try:
            # 컨텍스트 구축
            print("📚 컨텍스트 구축 중...")
            context = await self.rag_engine.build_context(query)
            
            print(f"\n📊 컨텍스트 요약:")
            print(f"  - 센서 태그: {context['sensor_tags']}")
            print(f"  - 현재 데이터: {len(context['current_data'])}개")
            print(f"  - QC 규칙: {len(context['qc_rules'])}개")
            print(f"  - 관련 지식: {len(context['relevant_knowledge'])}개")
            print(f"  - 센서별 지식: {len(context['sensor_specific_knowledge'])}개")
            
            # 응답 생성 (템플릿 방식)
            if context['current_data']:
                response = f"✅ 성공: 데이터 기반 응답 가능 ({len(context['current_data'])}개 센서)"
            elif context['relevant_knowledge']:
                response = f"📚 지식베이스 기반 응답 ({len(context['relevant_knowledge'])}개 지식)"
            else:
                response = "⚠️ 관련 데이터/지식 없음"
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'scenario': scenario_name,
                'query': query,
                'status': 'success',
                'response': response,
                'context_size': {
                    'sensors': len(context['sensor_tags']),
                    'data': len(context['current_data']),
                    'qc_rules': len(context['qc_rules']),
                    'knowledge': len(context['relevant_knowledge'])
                },
                'elapsed_time': elapsed_time
            }
            
            print(f"\n💬 응답: {response}")
            print(f"⏱️ 처리 시간: {elapsed_time:.2f}초")
            
        except Exception as e:
            result = {
                'scenario': scenario_name,
                'query': query,
                'status': 'error',
                'error': str(e),
                'elapsed_time': (datetime.now() - start_time).total_seconds()
            }
            print(f"\n❌ 오류 발생: {e}")
            
        self.test_results.append(result)
        return result
        
    async def run_all_scenarios(self):
        """모든 테스트 시나리오 실행"""
        
        test_scenarios = [
            {
                'name': '1. 현재 시스템 상태',
                'queries': [
                    "현재 시스템 상태는?",
                    "전체 센서 상태 요약해줘",
                    "지금 시스템이 정상인가요?"
                ]
            },
            {
                'name': '2. 특정 센서 데이터',
                'queries': [
                    "D100 센서 현재 값은?",
                    "D101 압력 센서 상태",
                    "온도 센서 D100의 최근 데이터"
                ]
            },
            {
                'name': '3. 이상 징후 탐지',
                'queries': [
                    "이상 징후가 있나요?",
                    "경고 상태인 센서는?",
                    "문제가 있는 센서 찾아줘"
                ]
            },
            {
                'name': '4. 트렌드 분석',
                'queries': [
                    "온도 트렌드는 어때?",
                    "압력이 증가하고 있나요?",
                    "최근 24시간 변화 패턴"
                ]
            },
            {
                'name': '5. 복합 질의',
                'queries': [
                    "D100 센서가 비정상이면 어떻게 해야 하나요?",
                    "압력이 높을 때 온도는 어떤가요?",
                    "센서 D100과 D101의 상관관계는?"
                ]
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n\n{'#'*60}")
            print(f"# {scenario['name']}")
            print('#'*60)
            
            for query in scenario['queries']:
                await self.run_test_scenario(
                    f"{scenario['name']} - Q{scenario['queries'].index(query)+1}",
                    query
                )
                await asyncio.sleep(1)  # API 부하 방지
                
    def print_summary(self):
        """테스트 결과 요약"""
        print("\n\n" + "="*60)
        print("📊 테스트 결과 요약")
        print("="*60)
        
        total = len(self.test_results)
        success = sum(1 for r in self.test_results if r['status'] == 'success')
        errors = sum(1 for r in self.test_results if r['status'] == 'error')
        
        print(f"\n총 테스트: {total}개")
        print(f"✅ 성공: {success}개 ({success/total*100:.1f}%)")
        print(f"❌ 실패: {errors}개 ({errors/total*100:.1f}%)")
        
        # 평균 처리 시간
        avg_time = sum(r['elapsed_time'] for r in self.test_results) / total
        print(f"\n⏱️ 평균 처리 시간: {avg_time:.2f}초")
        
        # 컨텍스트 크기 통계
        if success > 0:
            successful_results = [r for r in self.test_results if r['status'] == 'success']
            avg_data = sum(r['context_size']['data'] for r in successful_results) / len(successful_results)
            avg_knowledge = sum(r['context_size']['knowledge'] for r in successful_results) / len(successful_results)
            
            print(f"\n📊 평균 컨텍스트 크기:")
            print(f"  - 센서 데이터: {avg_data:.1f}개")
            print(f"  - 지식베이스: {avg_knowledge:.1f}개")
        
        # 오류 목록
        if errors > 0:
            print(f"\n❌ 오류 발생 시나리오:")
            for r in self.test_results:
                if r['status'] == 'error':
                    print(f"  - {r['scenario']}: {r.get('error', 'Unknown error')}")
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장: {filename}")
        

async def main():
    """메인 실행 함수"""
    runner = AITestRunner()
    
    try:
        await runner.setup()
        await runner.run_all_scenarios()
        runner.print_summary()
        
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())