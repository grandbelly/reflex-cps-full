# Reflex-KSys UI 문서

이 문서는 Reflex 기반 TimescaleDB 대시보드의 전체 UI 구조와 컴포넌트를 상세히 설명합니다.

**생성일**: 2025-08-26  
**프레임워크**: Reflex 0.8.6 + Chakra UI + TailwindCSS V4  
**페이지 수**: 3개 (Dashboard, Trend, Tech)

---

## 🏗️ 전체 UI 아키텍처

### 공통 레이아웃 구조
```
┌─────────────────────────────────────────────┐
│ 헤더 네비게이션 (Header Navigation)          │
│ [Logo] [Dashboard] [Trend Analysis] [Tech]  │
├─────────────────────────────────────────────┤
│ 배너 네비게이션 (Banner Navigation)          │
│ [Dashboard 실시간 모니터링] [Trend 시계열]... │
├─────────────────────────────────────────────┤
│                페이지별 콘텐츠                │
│            (Page-Specific Content)          │
└─────────────────────────────────────────────┘
```

### UI 프레임워크 스택
- **Reflex Framework**: Python → React 변환
- **Chakra UI**: `rc.circular_progress`, `rc.select` 등 UI 컴포넌트
- **TailwindCSS V4**: 유틸리티 기반 스타일링
- **Recharts**: `rx.recharts` 시계열 차트
- **psycopg**: 비동기 데이터베이스 연결

---

## 📄 Page 1: Dashboard (`/`)

### 페이지 구조
```yaml
URL: http://localhost:13000/
Title: KsysApp | Index
Purpose: 실시간 KPI 모니터링
Layout: 3x3 그리드 (9개 KPI 타일)
```

### 네비게이션 요소
```yaml
헤더_네비게이션:
  - 로고: "Ksys Logo" (이미지)
  - 링크:
    - "Dashboard" → / (현재 페이지)
    - "Trend Analysis" → /trend
    - "Tech Indicators" → /tech

배너_네비게이션:
  - 카드1: "Dashboard 실시간 모니터링" → /
  - 카드2: "Trend 시계열 분석" → /trend
  - 카드3: "Tech Indicators 기술지표" → /tech
```

### KPI 타일 구조 (9개)
```yaml
KPI_타일_구조:
  태그_그룹:
    D100_계열: [D100, D101, D102]  # 0.0~200.0 범위
    D200_계열: [D200, D201, D202]  # 0.0~2000.0 범위
    D300_계열: [D300, D301, D302]  # 0.0~20000.0 범위
  
  각_타일_요소:
    - 태그명: "D100" (센서 식별자)
    - 범위: "0.0 ~ 200.0" (QC 규칙 기반)
    - 상태: "OK" (녹색 배지)
    - 게이지: Chakra UI circular_progress
    - 현재값: "190.0" (게이지 중앙 표시)
    - 타임스탬프: "2025-08-26 22:01:47"
    - 미니차트: 6포인트 실시간 데이터
    - 변화율: "+0.0%" (이전 대비 변화)
```

### 실제 데이터 예시
```yaml
D100: {값: 190.0, 범위: 0-200, 상태: OK, 게이지: 95%}
D101: {값: 1.0, 범위: 0-200, 상태: OK, 게이지: 0.5%}
D102: {값: 301.0, 범위: 0-200, 상태: OK, 게이지: 초과}
D200: {값: 3000.0, 범위: 0-2000, 상태: OK, 게이지: 초과}
D201: {값: 3000.0, 범위: 0-2000, 상태: OK, 게이지: 초과}
D202: {값: 620.0, 범위: 0-2000, 상태: OK, 게이지: 31%}
D300: {값: 7000.0, 범위: 0-20000, 상태: OK, 게이지: 35%}
D301: {값: 7100.0, 범위: 0-20000, 상태: OK, 게이지: 35.5%}
D302: {값: 7200.0, 범위: 0-20000, 상태: OK, 게이지: 36%}
```

---

## 📈 Page 2: Trend Analysis (`/trend`)

### 페이지 구조
```yaml
URL: http://localhost:13000/trend
Title: KsysApp | Trend
Purpose: 시계열 데이터 분석
Layout: 필터 + 차트 + 테이블
```

### 컨트롤 패널
```yaml
필터_컨트롤:
  태그_선택:
    type: combobox (드롭다운)
    options: [D100, D101, D102, D200, D201, D202, D300, D301, D302]
    default: "D100" (선택됨)
    
  조회기간:
    type: combobox (드롭다운)
    options: [1min, 5min, 10min, 60min, 12hour, 24hour, 48hour, 7days, 14days, 30days, 3months, 6months, 12months]
    default: "5 min" (선택됨)
```

### 차트 영역
```yaml
차트_컨트롤:
  제목: "D100" (선택된 태그명)
  메트릭_선택:
    type: radio_group (라디오 버튼)
    options: ["Avg" (선택됨), "Min", "Max", "First", "Last"]
  
  범례:
    - "Average" (파란색 선)
  
  차트_데이터:
    type: Recharts 라인차트
    x축: 시간 (2025-08-26 22:05 ~ 22:09)
    y축: 값 (0 ~ 200)
    데이터: 5개 데이터포인트
```

### 데이터 테이블
```yaml
테이블_구조:
  제목: "Measurement History"
  부제목: "Real-time Data"
  
  컬럼:
    - "No." (순번)
    - "TAG" (태그명)
    - "Timestamp" (타임스탬프)
    - "Average" (평균값)
    - "Min" (최소값)
    - "Max" (최대값)
    - "Last" (마지막값)
    - "First" (첫값)
    - "Count" (데이터개수)
  
  데이터_예시:
    - Row 1: [1, D100, 2025-08-26 22:09:00+09:00, 190.00, 190.00, 190.00, 190.00, 190.00, 6]
    - Row 2: [2, D100, 2025-08-26 22:08:00+09:00, 190.00, 190.00, 190.00, 190.00, 190.00, 12]
    - ... (5개 행 표시)
```

---

## 🔧 Page 3: Tech Indicators (`/tech`)

### 페이지 구조
```yaml
URL: http://localhost:13000/tech
Title: KsysApp | Tech
Purpose: 기술적 지표 분석
Layout: 필터 + 차트 + 기술지표 테이블
```

### 컨트롤 패널
```yaml
필터_컨트롤:
  태그_선택: (Trend와 동일)
  조회기간: (Trend와 동일)
```

### 차트 영역
```yaml
차트_컨트롤:
  제목: "D100" (선택된 태그명)
  기술지표_선택:
    type: radio_group
    options: ["Avg" (선택됨), "SMA10", "SMA60", "BB Upper", "BB Lower"]
  
  범례:
    - "Average" (파란색 선)
  
  차트_데이터:
    type: Recharts 라인차트
    x축: 시간 (2025-08-26 22:05 ~ 22:09)
    y축: 값 (0 ~ 200)
```

### 기술지표 테이블
```yaml
테이블_구조:
  제목: "Technical Indicators"
  부제목: "Moving Averages & Bands"
  
  컬럼:
    - "No." (순번)
    - "TAG" (태그명)
    - "Timestamp" (타임스탬프)
    - "Average" (평균값)
    - "SMA 10" (10분 이동평균)
    - "SMA 60" (60분 이동평균)
    - "BB Top" (볼린저 밴드 상단)
    - "BB Bottom" (볼린저 밴드 하단)
    - "Slope 60" (60분 기울기)
  
  데이터_예시:
    - Row 1: [1, D100, 2025-08-26 22:09:00+09:00, 190.00, 190.00, 190.00, 190.00, 190.00, 0]
    - Row 2: [2, D100, 2025-08-26 22:08:00+09:00, 190.00, 190.00, 190.00, 190.00, 190.00, 0]
    - Row 5: [5, D100, 2025-08-26 22:05:00+09:00, 190.00, 190.00, 190.00, 0, 0, 0]
```

---

## 🧩 컴포넌트 상세 분석

### 1. Layout Components (`components/layout.py`)
```yaml
shell():
  - 전체 페이지 래퍼
  - 헤더 및 배너 네비게이션 포함
  - 알림 영역 (Notifications alt+T)

stat_card():
  - 배너 네비게이션 카드
  - 제목 + 설명 + 링크 구조
```

### 2. KPI Components (`components/kpi_tiles.py`)
```yaml
unified_kpi_card():
  - 9개 센서별 통합 KPI 카드
  - Chakra UI circular_progress 사용
  - 실시간 데이터 바인딩

mini_stat_card():
  - 미니 통계 카드 (미사용 추정)

sensor_detail_modal():
  - 센서 상세 모달 (구현 확인 필요)
```

### 3. Gauge Components (`components/gauge.py`)
```yaml
radial_gauge():
  - Chakra UI 기반 원형 게이지
  - 백분율 계산: (current - min) / (max - min) * 100
  - 색상: 상태별 동적 색상 (녹색/황색/적색)
```

### 4. Table Components
```yaml
features_table(): (components/features_table.py)
  - Trend 페이지 측정 히스토리 테이블
  - 실시간 데이터 스트리밍

indicators_table(): (components/indicators_table.py)
  - Tech 페이지 기술지표 테이블
  - SMA, Bollinger Bands, Slope 계산
```

### 5. Chart Components (`components/realtime_chart.py`)
```yaml
- Recharts 기반 라인차트
- 실시간 데이터 업데이트
- 범례 및 축 레이블 지원
```

### 6. Status Components (`components/status_badge.py`)
```yaml
- 상태 배지 (OK/WARNING/CRITICAL)
- 색상 코딩: 녹색(정상), 황색(경고), 적색(위험)
```

---

## 🎨 스타일링 시스템

### Color Scheme
```yaml
상태_색상:
  - OK: 녹색 (정상 상태)
  - WARNING: 황색 (경고 상태)
  - CRITICAL: 적색 (위험 상태)

차트_색상:
  - Primary: 파란색 (메인 데이터 라인)
  - Secondary: 회색 (보조 데이터)
```

### 반응형 레이아웃
```yaml
Dashboard:
  - Desktop: 3x3 그리드
  - Tablet: 2x5 그리드 (추정)
  - Mobile: 1x9 스택 (추정)

Trend/Tech:
  - 필터 패널: 상단 고정
  - 차트 영역: 가변 높이
  - 테이블: 스크롤 가능
```

---

## 📊 데이터 플로우

### State Management
```yaml
DashboardState (states/dashboard.py):
  실시간_모드:
    - 10초 주기 자동 갱신
    - WebSocket 통신 (추정)
  
  데이터_캐싱:
    - TTL 30-60초
    - 최대 100개 항목
  
  계산_로직:
    - 게이지 백분율
    - 상태 레벨 (0=정상, 1=경고, 2=위험)
    - 변화율 계산
```

### Database Integration
```yaml
TimescaleDB_Views:
  - influx_agg_1m: 1분 집계
  - influx_agg_10m: 10분 집계
  - influx_agg_1h: 1시간 집계
  - influx_latest: 최신 스냅샷
  - features_5m: 5분 통계
  - tech_ind_1m_mv: 기술지표 (MV)
  - influx_qc_rule: QC 규칙
```

---

## 🚀 성능 최적화

### Frontend Performance
```yaml
목표_성능:
  - First Content Paint: < 2초
  - 차트 렌더링: < 500ms
  - 실시간 업데이트: 10초 주기
  
최적화_기법:
  - Reflex 컴포넌트 캐싱
  - 동적 쿼리 제한
  - TTL 기반 데이터 캐싱
```

### Backend Performance
```yaml
쿼리_최적화:
  - 24시간 이하: 1분 해상도
  - 14일 이하: 10분 해상도  
  - 14일 초과: 1시간 해상도

연결_풀링:
  - 최소 1개, 최대 10개 연결
  - 자동 커밋 모드
  - 5초 쿼리 타임아웃
```

---

## 📱 접근성 & 사용성

### 접근성 기능
```yaml
키보드_네비게이션:
  - 알림 영역: Alt+T
  - 탭 네비게이션 지원

스크린_리더:
  - 적절한 ARIA 레이블
  - 테이블 헤더 구조화
  - 이미지 alt 텍스트

시각적_접근성:
  - 색상 대비 준수 (추정)
  - 텍스트 크기 조정 가능 (추정)
```

### 다국어 지원
```yaml
현재_언어:
  - 한국어: UI 텍스트 ("태그 선택", "조회기간")
  - 영어: 기술 용어 ("Dashboard", "Trend Analysis")

타임존:
  - Asia/Seoul (한국 표준시)
  - UTC 저장, 로컬 표시
```

---

## 🔧 개발자 가이드

### 컴포넌트 추가 방법
```python
# 1. components/ 폴더에 새 파일 생성
# 2. Reflex 컴포넌트 패턴 따르기
import reflex as rx

def my_component() -> rx.Component:
    return rx.el.div(
        # 컴포넌트 구조
        class_name="tailwind-classes"
    )

# 3. ksys_app.py에서 import 및 사용
```

### 상태 관리 패턴
```python
# states/ 폴더에 상태 클래스 정의
class MyState(rx.State):
    data: list[dict] = []
    
    @rx.event(background=True)
    async def load_data(self):
        # 비동기 데이터 로딩
        pass
        
    @rx.var
    def computed_value(self) -> str:
        # 계산된 속성
        return "result"
```

### 쿼리 추가 방법
```python
# queries/ 폴더에 쿼리 함수 정의
from ..db import q

async def get_my_data(tag: str) -> list[dict]:
    sql = "SELECT * FROM my_view WHERE tag_name = %s"
    return await q(sql, (tag,))
```

---

이 문서는 Reflex-KSys 대시보드의 완전한 UI 구조를 담고 있으며, 향후 개발 및 유지보수 시 참고 자료로 활용할 수 있습니다.