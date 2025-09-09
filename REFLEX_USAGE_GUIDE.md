# Reflex 사용법 가이드 - 데이터 타입 및 상태 관리 중심

## 📋 작성 목적
- Reflex 개발 시 반복되는 실수 방지
- Python, Reflex, React 간 데이터 타입 혼동 해결
- 상태 관리 및 이벤트 처리 표준화

---

## 🔧 핵심 개념

### 1. Reflex State 클래스 기본 구조

```python
import reflex as rx
from typing import List, Dict, Any

class MyState(rx.State):
    # 📌 필수: 모든 상태 변수는 타입 어노테이션 필수
    count: int = 0
    items: List[str] = []
    data: Dict[str, Any] = {}
    
    # 📌 이벤트 핸들러는 @rx.event 데코레이터 사용 (선택적)
    @rx.event
    def increment(self):
        self.count += 1
    
    # 📌 계산된 변수는 @rx.var 데코레이터 사용
    @rx.var
    def double_count(self) -> int:
        return self.count * 2
```

---

## 📊 데이터 타입 매핑 규칙

### Python → Reflex → React 변환표

| Python 타입 | Reflex 상태 타입 | React Props 타입 | 주의사항 |
|-------------|----------------|-----------------|----------|
| `int` | `int` | `number` | 정수값 유지 |
| `float` | `float` | `number` | NaN 처리 주의 |
| `str` | `str` | `string` | 문자열 이스케이핑 |
| `bool` | `bool` | `boolean` | True/False → true/false |
| `List[T]` | `List[T]` | `Array<T>` | **rx.foreach 필수** |
| `Dict[str, Any]` | `Dict[str, Any]` | `Record<string, any>` | 중첩 접근 주의 |
| `None` | `None` | `null/undefined` | 조건부 렌더링 필요 |

---

## ⚠️ 자주 발생하는 타입 오류 및 해결법

### 1. NaN 값 처리

```python
# ❌ 잘못된 방법 - NaN이 그대로 전달됨
class BadState(rx.State):
    correlation_matrix: Dict[str, float] = {}
    
    def calculate_correlation(self):
        # pandas에서 NaN이 발생할 수 있음
        self.correlation_matrix = df.corr().to_dict()

# ✅ 올바른 방법 - NaN 값 사전 처리
class GoodState(rx.State):
    correlation_matrix: Dict[str, float] = {}
    
    @rx.event
    def calculate_correlation(self):
        corr_data = df.corr()
        # NaN 값 제거/대체
        corr_data = corr_data.fillna(0.0)
        self.correlation_matrix = corr_data.to_dict()
```

### 2. List 데이터 렌더링

```python
# ❌ 잘못된 방법 - Python for loop 사용
def render_items():
    return rx.vstack(
        [rx.text(item) for item in MyState.items]  # 동적 업데이트 안됨
    )

# ✅ 올바른 방법 - rx.foreach 사용
def render_items():
    return rx.vstack(
        rx.foreach(MyState.items, lambda item: rx.text(item))
    )
```

### 3. 중첩 딕셔너리 접근

```python
# ❌ 잘못된 방법 - 직접 중첩 접근
class BadState(rx.State):
    complex_data: Dict[str, Dict[str, Any]] = {}

def bad_component():
    return rx.text(BadState.complex_data["key"]["nested_key"])  # 오류 발생

# ✅ 올바른 방법 - 계산된 변수 사용
class GoodState(rx.State):
    complex_data: Dict[str, Dict[str, Any]] = {}
    
    @rx.var
    def nested_value(self) -> str:
        return self.complex_data.get("key", {}).get("nested_key", "")

def good_component():
    return rx.text(GoodState.nested_value)
```

---

## 🎯 이벤트 처리 패턴

### 1. 폼 데이터 처리

```python
class FormState(rx.State):
    form_data: Dict[str, Any] = {}
    
    @rx.event
    def handle_submit(self, form_data: dict):
        """폼 제출 시 자동으로 form_data 매개변수 전달됨"""
        self.form_data = form_data
        # 추가 처리 로직

def form_component():
    return rx.form(
        rx.input(name="username", placeholder="사용자명"),
        rx.input(name="email", placeholder="이메일"),
        rx.button("제출", type="submit"),
        on_submit=FormState.handle_submit,  # 자동으로 form_data 전달
        reset_on_submit=True
    )
```

### 2. 비동기 이벤트 처리

```python
class AsyncState(rx.State):
    loading: bool = False
    data: List[Dict] = []
    
    @rx.event(background=True)
    async def fetch_data(self):
        async with self:
            self.loading = True
            
        try:
            # 비동기 작업 수행
            result = await some_async_operation()
            
            async with self:
                self.data = result
                self.loading = False
        except Exception as e:
            async with self:
                self.loading = False
            # 오류 처리
```

---

## 🔄 상태 간 통신

### Cross-State Communication

```python
class SettingsState(rx.State):
    theme: str = "light"

class MainState(rx.State):
    content: str = ""
    
    @rx.event
    async def update_content(self):
        # 다른 상태 접근
        settings = await self.get_state(SettingsState)
        if settings.theme == "dark":
            self.content = "다크 테마 콘텐츠"
        else:
            self.content = "라이트 테마 콘텐츠"
```

---

## 🎨 조건부 렌더링 패턴

### 1. 데이터 존재 여부 확인

```python
class DataState(rx.State):
    items: List[str] = []
    
    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

def conditional_render():
    return rx.cond(
        DataState.has_items,
        rx.foreach(DataState.items, lambda item: rx.text(item)),
        rx.text("데이터가 없습니다")
    )
```

### 2. 로딩 상태 처리

```python
class LoadingState(rx.State):
    is_loading: bool = False
    data: List[Dict] = []

def loading_component():
    return rx.cond(
        LoadingState.is_loading,
        rx.spinner(),
        rx.cond(
            LoadingState.data,
            rx.foreach(LoadingState.data, render_data_item),
            rx.text("데이터를 로드하지 못했습니다")
        )
    )
```

---

## 🚫 절대 금지사항

### 1. 타입 어노테이션 생략
```python
# ❌ 금지
class BadState(rx.State):
    data = []  # 타입 불명확

# ✅ 필수
class GoodState(rx.State):
    data: List[Dict[str, Any]] = []
```

### 2. 직접적인 상태 변수 수정 (이벤트 핸들러 외부에서)
```python
# ❌ 금지 - 컴포넌트에서 직접 수정
def bad_component():
    MyState.count = 10  # 절대 금지!

# ✅ 올바름 - 이벤트 핸들러를 통한 수정
class MyState(rx.State):
    count: int = 0
    
    @rx.event
    def set_count(self, value: int):
        self.count = value
```

### 3. Python for loop와 rx.foreach 혼용
```python
# ❌ 동적 데이터에 Python for loop 사용
def bad_render():
    return rx.vstack(
        [rx.text(item) for item in MyState.dynamic_list]  # 업데이트 안됨
    )

# ✅ 동적 데이터에는 rx.foreach 사용
def good_render():
    return rx.vstack(
        rx.foreach(MyState.dynamic_list, lambda item: rx.text(item))
    )
```

---

## 📈 성능 최적화 팁

### 1. 계산된 변수 캐싱
```python
class OptimizedState(rx.State):
    large_data: List[Dict] = []
    
    @rx.var(cache=True)  # 캐싱 활성화
    def processed_data(self) -> List[Dict]:
        # 무거운 계산 작업
        return [process_item(item) for item in self.large_data]
```

### 2. 백그라운드 작업
```python
class BackgroundState(rx.State):
    @rx.event(background=True)  # 백그라운드 실행
    async def heavy_task(self):
        # 무거운 작업을 백그라운드에서 실행
        result = await expensive_operation()
        async with self:
            self.result = result
```

---

## ✅ 개발 전 체크리스트

1. [ ] 모든 상태 변수에 타입 어노테이션 추가
2. [ ] 동적 리스트는 `rx.foreach` 사용 확인
3. [ ] NaN/None 값 처리 로직 구현
4. [ ] 이벤트 핸들러는 상태 클래스 내부에 정의
5. [ ] 비동기 작업은 `@rx.event(background=True)` 사용
6. [ ] 조건부 렌더링에 `rx.cond` 사용
7. [ ] 중첩 데이터 접근시 계산된 변수 활용
8. [ ] 폼 데이터는 `on_submit` 이벤트로 처리

---

## 🔍 디버깅 가이드

### 1. 상태 변경 확인
```python
@rx.event
def debug_state_change(self):
    print(f"현재 상태: {self.dict()}")  # 전체 상태 출력
    self.some_value += 1
    print(f"변경 후: {self.dict()}")
```

### 2. 타입 검증
```python
@rx.event
def validate_types(self):
    for key, value in self.dict().items():
        print(f"{key}: {type(value)} = {value}")
```

---

## 📚 참고 자료

- [Reflex 공식 문서](https://reflex.dev/docs)
- [State Management](https://reflex.dev/docs/state/overview)
- [Event Handling](https://reflex.dev/docs/events/overview)
- [Data Types](https://reflex.dev/docs/vars/base_vars)

---

**⚠️ 중요**: 이 가이드의 패턴을 따르지 않으면 런타임 오류, 타입 오류, 성능 저하가 발생할 수 있습니다. 개발 전 반드시 체크리스트를 확인하세요.