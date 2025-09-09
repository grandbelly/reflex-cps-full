# CHAIN OF THINGS 기반 태스크 실행 규칙

## 문서 정보
- **작성일**: 2024-01-15
- **버전**: 1.0
- **목적**: 체계적이고 추적 가능한 태스크 실행 체인 구축
- **원칙**: 각 단계가 명확하고 검증 가능한 실행 규칙

---

## 1. CHAIN OF THINGS 개념

### 1.1 정의
```
CHAIN OF THINGS = 연결된 작업 사슬
- 각 "Thing"은 독립적으로 실행 가능한 최소 단위
- Thing들이 연결되어 전체 목표 달성
- 각 Thing의 출력이 다음 Thing의 입력
```

### 1.2 핵심 원칙
1. **원자성**: 각 Thing은 더 이상 나눌 수 없는 단위
2. **추적성**: 모든 Thing의 실행 이력 기록
3. **검증성**: 각 Thing의 성공/실패 명확히 판단
4. **회복성**: 실패 시 해당 Thing부터 재시작 가능

---

## 2. Thing 정의 규칙

### 2.1 Thing 구조
```yaml
Thing:
  id: THING_001
  name: "데이터 수집"
  type: COLLECT | ANALYZE | DECIDE | ACT | VERIFY
  
  input:
    - source: 이전 Thing ID 또는 외부 소스
    - format: 데이터 형식
    - validation: 입력 검증 규칙
  
  process:
    - step1: 구체적 작업
    - step2: 구체적 작업
    
  output:
    - data: 출력 데이터
    - format: 데이터 형식
    - destination: 다음 Thing ID 또는 저장소
    
  validation:
    - criteria: 성공 기준
    - threshold: 임계값
    
  error_handling:
    - retry: 재시도 횟수
    - fallback: 대체 경로
    - alert: 알림 대상
```

### 2.2 Thing 타입
| 타입 | 설명 | 예시 |
|------|------|------|
| COLLECT | 데이터 수집 | 센서값 읽기, DB 조회 |
| ANALYZE | 데이터 분석 | 패턴 분석, 통계 계산 |
| DECIDE | 의사 결정 | 임계값 비교, 규칙 평가 |
| ACT | 실행 | 알람 발생, 제어 명령 |
| VERIFY | 검증 | 결과 확인, 피드백 |

---

## 3. 실행 체인 구성

### 3.1 기본 체인 패턴
```
[COLLECT] → [ANALYZE] → [DECIDE] → [ACT] → [VERIFY]
     ↑                                          ↓
     └──────────── 피드백 루프 ─────────────────┘
```

### 3.2 AI 인사이트 체인 예시

#### 3.2.1 센서 이상 감지 체인
```yaml
Chain: SENSOR_ANOMALY_DETECTION
Things:
  - THING_001:
      name: "센서 데이터 수집"
      type: COLLECT
      process:
        - TimescaleDB에서 최근 10분 데이터 조회
        - 센서별 데이터 정규화
      output: normalized_data
      
  - THING_002:
      name: "이상 패턴 분석"
      type: ANALYZE
      input: normalized_data
      process:
        - 이동 평균 계산
        - Z-score 이상치 감지
        - 상관관계 분석
      output: anomaly_scores
      
  - THING_003:
      name: "위험도 판단"
      type: DECIDE
      input: anomaly_scores
      process:
        - QC 규칙 적용
        - 심각도 레벨 결정
        - 에스컬레이션 필요 여부
      output: risk_decision
      
  - THING_004:
      name: "대응 조치"
      type: ACT
      input: risk_decision
      process:
        - 알람 발생
        - 6하 원칙 리포트 생성
        - 담당자 통보
      output: action_result
      
  - THING_005:
      name: "결과 검증"
      type: VERIFY
      input: action_result
      process:
        - 알람 전달 확인
        - 오퍼레이터 확인 여부
        - 조치 완료 확인
      output: verification_status
```

#### 3.2.2 예지보수 체인
```yaml
Chain: PREDICTIVE_MAINTENANCE
Things:
  - THING_101:
      name: "운전 이력 수집"
      type: COLLECT
      schedule: "매일 00:00"
      
  - THING_102:
      name: "열화 모델 실행"
      type: ANALYZE
      dependency: THING_101
      
  - THING_103:
      name: "잔여 수명 계산"
      type: ANALYZE
      dependency: THING_102
      
  - THING_104:
      name: "정비 시기 결정"
      type: DECIDE
      dependency: THING_103
      
  - THING_105:
      name: "정비 계획 생성"
      type: ACT
      dependency: THING_104
      
  - THING_106:
      name: "계획 승인 확인"
      type: VERIFY
      dependency: THING_105
```

---

## 4. 실행 규칙

### 4.1 실행 조건
```python
class ThingExecutor:
    def can_execute(self, thing):
        """Thing 실행 가능 여부 판단"""
        return all([
            self.check_dependencies(thing),      # 선행 Thing 완료
            self.check_input_ready(thing),       # 입력 데이터 준비
            self.check_resources(thing),         # 리소스 가용
            self.check_schedule(thing)           # 스케줄 확인
        ])
```

### 4.2 실행 순서 제어
1. **순차 실행**: 이전 Thing 완료 후 다음 Thing 시작
2. **병렬 실행**: 독립적인 Thing들 동시 실행
3. **조건부 실행**: 특정 조건 만족 시만 실행
4. **주기적 실행**: 정해진 스케줄에 따라 실행

### 4.3 상태 관리
```
Thing 상태 전이:
PENDING → READY → RUNNING → SUCCESS
                      ↓         ↓
                   FAILED → RETRY
                      ↓
                   SKIPPED
```

---

## 5. 에러 처리 및 복구

### 5.1 에러 처리 전략
| 에러 타입 | 처리 방법 | 예시 |
|-----------|-----------|------|
| 일시적 | 자동 재시도 | 네트워크 타임아웃 |
| 데이터 | 대체값 사용 | 센서 누락값 |
| 로직 | 대체 경로 | 계산 실패 |
| 시스템 | 에스컬레이션 | DB 다운 |

### 5.2 복구 시나리오
```yaml
Recovery_Scenario:
  trigger: THING_002 실패
  
  steps:
    1. 에러 로그 기록:
       - timestamp
       - error_type
       - error_message
       
    2. 재시도 판단:
       if retry_count < max_retry:
         - wait(exponential_backoff)
         - retry THING_002
       
    3. 대체 경로:
       if retry_failed:
         - execute THING_002_FALLBACK
         
    4. 에스컬레이션:
       if fallback_failed:
         - alert_operator
         - pause_chain
```

---

## 6. 모니터링 및 추적

### 6.1 실행 로그 형식
```json
{
  "chain_id": "SENSOR_ANOMALY_001",
  "thing_id": "THING_002",
  "timestamp": "2024-01-15T10:30:00Z",
  "status": "SUCCESS",
  "duration_ms": 234,
  "input": {
    "data_points": 120,
    "sensors": ["D101", "D102"]
  },
  "output": {
    "anomalies_found": 2,
    "max_score": 3.2
  },
  "metrics": {
    "cpu_usage": 45,
    "memory_mb": 128
  }
}
```

### 6.2 성능 지표
```yaml
KPIs:
  - 체인 완료율: 완료된 체인 / 시작된 체인
  - Thing 성공률: 성공 Thing / 전체 Thing
  - 평균 실행 시간: 체인별, Thing별
  - 에러율: 에러 발생 / 전체 실행
  - 재시도율: 재시도 / 전체 실행
```

### 6.3 추적 대시보드
```
┌─────────────────────────────────┐
│     체인 실행 현황              │
├─────────────────────────────────┤
│ 실행중: 3                       │
│ 대기중: 5                       │
│ 완료: 127                      │
│ 실패: 2                        │
├─────────────────────────────────┤
│     최근 실행 이력              │
├─────────────────────────────────┤
│ 10:30 SENSOR_ANOMALY ✓          │
│ 10:25 PREDICTIVE_MAINT ✓        │
│ 10:20 WATER_QUALITY ✗           │
└─────────────────────────────────┘
```

---

## 7. 구현 예제

### 7.1 Python 구현
```python
from dataclasses import dataclass
from typing import Any, Dict, List
from enum import Enum
import asyncio

class ThingType(Enum):
    COLLECT = "COLLECT"
    ANALYZE = "ANALYZE"
    DECIDE = "DECIDE"
    ACT = "ACT"
    VERIFY = "VERIFY"

@dataclass
class Thing:
    id: str
    name: str
    type: ThingType
    process: callable
    validation: callable
    
    async def execute(self, input_data: Any) -> Dict:
        """Thing 실행"""
        try:
            # 입력 검증
            if not self.validate_input(input_data):
                raise ValueError("Invalid input")
            
            # 프로세스 실행
            result = await self.process(input_data)
            
            # 출력 검증
            if not self.validation(result):
                raise ValueError("Validation failed")
                
            return {
                "status": "SUCCESS",
                "output": result
            }
            
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }

class Chain:
    def __init__(self, chain_id: str):
        self.chain_id = chain_id
        self.things: List[Thing] = []
        self.context = {}
        
    def add_thing(self, thing: Thing):
        """체인에 Thing 추가"""
        self.things.append(thing)
        
    async def execute(self):
        """체인 실행"""
        previous_output = None
        
        for thing in self.things:
            print(f"Executing {thing.name}...")
            
            result = await thing.execute(previous_output)
            
            if result["status"] == "FAILED":
                print(f"Failed: {result['error']}")
                return False
                
            previous_output = result["output"]
            self.context[thing.id] = result
            
        return True

# 사용 예제
async def collect_sensor_data(input_data):
    """센서 데이터 수집"""
    # DB 조회 로직
    return {"sensors": ["D101", "D102"], "values": [23.5, 67.8]}

async def analyze_anomaly(sensor_data):
    """이상 분석"""
    # 분석 로직
    return {"anomaly_score": 2.5, "is_anomaly": True}

# Thing 생성
thing1 = Thing(
    id="THING_001",
    name="센서 데이터 수집",
    type=ThingType.COLLECT,
    process=collect_sensor_data,
    validation=lambda x: x is not None
)

thing2 = Thing(
    id="THING_002", 
    name="이상 패턴 분석",
    type=ThingType.ANALYZE,
    process=analyze_anomaly,
    validation=lambda x: "anomaly_score" in x
)

# 체인 구성 및 실행
chain = Chain("SENSOR_ANOMALY_001")
chain.add_thing(thing1)
chain.add_thing(thing2)

# 실행
asyncio.run(chain.execute())
```

### 7.2 설정 파일 (chain_config.yaml)
```yaml
chains:
  - id: SENSOR_ANOMALY_DETECTION
    name: "센서 이상 감지"
    schedule: "*/5 * * * *"  # 5분마다
    things:
      - id: COLLECT_001
        module: ksys_app.chains.collect
        function: collect_sensor_data
        params:
          window: "10m"
          sensors: ["D101", "D102", "D103"]
          
      - id: ANALYZE_001
        module: ksys_app.chains.analyze
        function: detect_anomaly
        params:
          method: "zscore"
          threshold: 3.0
          
      - id: DECIDE_001
        module: ksys_app.chains.decide
        function: evaluate_risk
        params:
          rules: "qc_rules.json"
          
      - id: ACT_001
        module: ksys_app.chains.act
        function: send_alert
        params:
          channels: ["dashboard", "email"]
          
      - id: VERIFY_001
        module: ksys_app.chains.verify
        function: confirm_delivery
        params:
          timeout: 60
```

---

## 8. 테스트 및 검증

### 8.1 단위 테스트
```python
import pytest

@pytest.mark.asyncio
async def test_thing_execution():
    """Thing 실행 테스트"""
    thing = Thing(
        id="TEST_001",
        name="테스트",
        type=ThingType.COLLECT,
        process=lambda x: {"result": "ok"},
        validation=lambda x: True
    )
    
    result = await thing.execute(None)
    assert result["status"] == "SUCCESS"
    assert result["output"]["result"] == "ok"
```

### 8.2 통합 테스트
```python
@pytest.mark.asyncio
async def test_chain_execution():
    """체인 실행 테스트"""
    chain = Chain("TEST_CHAIN")
    # Thing 추가
    # ...
    success = await chain.execute()
    assert success == True
```

### 8.3 시나리오 테스트
| 시나리오 | 테스트 내용 | 예상 결과 |
|----------|-------------|-----------|
| 정상 플로우 | 모든 Thing 성공 | 체인 완료 |
| 에러 복구 | Thing 실패 후 재시도 | 재시도 성공 |
| 타임아웃 | Thing 실행 시간 초과 | 타임아웃 에러 |
| 병렬 실행 | 독립 Thing 동시 실행 | 실행 시간 단축 |

---

## 9. 운영 가이드

### 9.1 체인 배포
1. 설정 파일 검증
2. 테스트 환경 실행
3. 모니터링 설정
4. 프로덕션 배포
5. 헬스 체크

### 9.2 문제 해결
| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| Thing 멈춤 | 데드락 | 타임아웃 설정 |
| 메모리 증가 | 누수 | 리소스 정리 |
| 느린 실행 | 병목 | 병렬화 |

### 9.3 유지보수
- **일일**: 실행 로그 확인
- **주간**: 성능 지표 분석
- **월간**: 체인 최적화

---

## 10. 부록

### 10.1 용어집
- **Thing**: 실행 가능한 최소 작업 단위
- **Chain**: Thing들의 연결된 실행 흐름
- **Context**: 체인 실행 중 공유되는 데이터
- **Orchestrator**: 체인 실행을 관리하는 컴포넌트

### 10.2 참고 자료
- Chain of Thought Prompting
- Apache Airflow DAG 패턴
- Microservices Saga Pattern