# 할루시네이션 방지 종합 가이드

## 🎯 목표
LLM이 실제 데이터 없이 그럴듯한 수치를 생성하는 것을 완전히 차단

## ✅ 구현된 방어 메커니즘

### 1. **Temperature 조정** ✅
- `0.7 → 0.2` 로 낮춤
- 창의성 감소, 정확성 증가
- 파일: `rag_engine.py`, `enhanced_agent_orchestrator.py`

### 2. **엄격한 시스템 프롬프트** ✅
```python
"중요 규칙 (절대 준수):
1. 제공된 데이터만 사용하세요
2. 수치를 절대 창작하지 마세요
3. 데이터가 없으면 '데이터 없음' 표시
4. 모든 숫자는 제공된 값 그대로"
```

### 3. **컨텍스트 검증** ✅
```python
if not has_data and not has_qc and not has_knowledge:
    return "데이터베이스 연결 문제 또는 데이터 없음"
```

### 4. **구조화된 응답 (JSON)** ✅
- `response_validator.py` 구현
- 템플릿 기반 응답 생성
- 숫자는 실제 데이터에서만 추출

### 5. **할루시네이션 탐지** ✅
```python
def detect_hallucination(response, context):
    # 응답의 모든 숫자 추출
    # 컨텍스트와 대조
    # 없는 숫자 발견 시 경고
```

## 🔧 추가 개선 방안

### 6. **Few-Shot 프롬프팅**
```python
examples = [
    {
        "query": "D999 센서 상태는?",
        "context": "[]",  # 빈 데이터
        "good_response": "D999 센서 데이터를 찾을 수 없습니다.",
        "bad_response": "D999 센서는 정상입니다. 값은 50.3입니다."  # ❌ 환각
    }
]
```

### 7. **Chain of Verification (CoV)**
```python
async def verify_response(response, context):
    # Step 1: 응답에서 주장 추출
    claims = extract_claims(response)
    
    # Step 2: 각 주장 검증
    for claim in claims:
        if not verify_claim_against_context(claim, context):
            return regenerate_without_claim(response, claim)
    
    return response
```

### 8. **Retrieval Augmented Validation**
```python
class ValidatedRAG:
    async def generate(self, query):
        # 1. 관련 문서 검색
        docs = await self.retrieve(query)
        
        # 2. 문서가 없으면 즉시 중단
        if not docs:
            return "관련 데이터 없음"
        
        # 3. LLM 생성
        response = await self.llm_generate(query, docs)
        
        # 4. 생성된 응답 검증
        if self.contains_unsupported_facts(response, docs):
            return "데이터 검증 실패"
        
        return response
```

### 9. **Semantic Similarity Check**
```python
async def check_semantic_consistency(response, context):
    # 임베딩 생성
    response_embedding = embed(response)
    context_embedding = embed(str(context))
    
    # 유사도 계산
    similarity = cosine_similarity(response_embedding, context_embedding)
    
    # 임계값 이하면 거부
    if similarity < 0.7:
        return "응답이 컨텍스트와 일치하지 않음"
```

### 10. **Output Parser with Strict Schema**
```python
from pydantic import BaseModel, validator

class SensorResponse(BaseModel):
    sensor_name: str
    value: Optional[float]
    status: Literal['normal', 'warning', 'critical', 'unknown']
    source: Literal['database', 'cache', 'none']
    
    @validator('value')
    def value_must_be_from_context(cls, v, values):
        if values.get('source') == 'none' and v is not None:
            raise ValueError("Cannot have value without source")
        return v
```

## 📊 테스트 케이스

### 할루시네이션 테스트
```python
test_cases = [
    {
        "query": "D999 센서의 정확한 값은?",
        "expected": "D999 센서 데이터를 찾을 수 없습니다",
        "should_not_contain": ["값", "정상", "범위", "숫자"]
    },
    {
        "query": "품질 점수는 얼마야?",
        "context": {},  # 빈 컨텍스트
        "expected": "품질 점수 데이터가 제공되지 않았습니다",
        "should_not_contain": ["0.", "1.", "%"]
    }
]
```

## 🚀 적용 우선순위

1. **즉시 적용** (완료)
   - Temperature 낮춤 ✅
   - 엄격한 프롬프트 ✅
   - 컨텍스트 검증 ✅

2. **단기 적용** (진행중)
   - JSON 구조화 응답 ✅
   - 응답 검증기 ✅
   - 지식베이스 구축 🔄

3. **중기 적용**
   - Few-shot 예시 추가
   - Chain of Verification
   - Semantic similarity check

4. **장기 적용**
   - Fine-tuning with factual data
   - Custom hallucination detection model
   - A/B testing framework

## 🔍 모니터링

### 할루시네이션 지표
```python
metrics = {
    "unsupported_numbers": 0,  # 컨텍스트에 없는 숫자
    "fabricated_ranges": 0,     # 생성된 범위
    "false_statuses": 0,        # 잘못된 상태
    "confidence_drops": 0        # 신뢰도 하락
}
```

### 로깅
```python
if hallucination_detected:
    logger.warning(f"""
    할루시네이션 감지:
    Query: {query}
    Response: {response[:100]}
    Issue: {issue}
    Context size: {len(context)}
    """)
```

## 💡 Best Practices

1. **명시적 불확실성 표현**
   - "데이터 없음" > 추측
   - "확인 불가" > 가정
   - "~일 수 있음" 금지

2. **숫자는 항상 출처 표시**
   - ✅ "D100: 190 (현재 DB 값)"
   - ❌ "D100: 약 190 정도"

3. **범위는 실제 QC 규칙에서만**
   - ✅ "QC 규칙: 10-180 (DB 조회)"
   - ❌ "일반적으로 10-180 범위"

4. **템플릿 우선**
   - 반복되는 패턴은 템플릿화
   - LLM은 변수 채우기만

5. **신뢰도 점수 명시**
   - 각 응답에 confidence score
   - 낮은 신뢰도시 경고

## 🛠️ 디버깅 도구

### 할루시네이션 체커
```bash
python scripts/check_hallucination.py --query "D101 상태" --response "..."
```

### 컨텍스트 덤프
```python
if DEBUG:
    print(f"Context: {json.dumps(context, indent=2)}")
    print(f"Response: {response}")
    print(f"Hallucination check: {detect_hallucination(response, context)}")
```

## 📈 효과 측정

### Before
- 할루시네이션 율: ~30%
- 잘못된 수치: 빈번
- 사용자 신뢰도: 낮음

### After (목표)
- 할루시네이션 율: <1%
- 잘못된 수치: 0
- 사용자 신뢰도: 높음

## 🔄 지속적 개선

1. **주간 리뷰**
   - 할루시네이션 사례 수집
   - 패턴 분석
   - 프롬프트/검증 로직 개선

2. **월간 업데이트**
   - 지식베이스 확장
   - 검증 규칙 추가
   - 모델 파라미터 조정

3. **분기별 평가**
   - 전체 시스템 성능
   - 사용자 피드백
   - 새로운 방어 기법 도입