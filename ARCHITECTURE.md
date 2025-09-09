# Reflex-KSys Architecture Documentation

## 개요
Reflex 기반 TimescaleDB 대시보드 시스템의 현재 파일 구조와 의존성 관계를 정리한 문서입니다.

**업데이트 날짜**: 2025-08-26  
**정리 완료**: 19개 파일 삭제, 3,539 라인 정리  
**현재 상태**: 14개 핵심 컴포넌트, 745 라인 메인 앱

---

## 🏗️ 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (localhost:13000)                │
├─────────────────────────────────────────────────────────────┤
│                    Reflex Frontend                          │
│  ksys_app.py (Pages: /, /trend, /tech)                    │
├─────────────────────────────────────────────────────────────┤
│                    Reflex Backend                           │
│  states/dashboard.py (State Management)                     │
├─────────────────────────────────────────────────────────────┤
│                    Database Layer                           │
│  queries/*.py (SQL Queries) → db.py (Connection Pool)      │
├─────────────────────────────────────────────────────────────┤
│                   TimescaleDB                              │
│  public.influx_agg_* (CAGG Views)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 핵심 파일 구조 및 역할

### **루트 레벨**
```
reflex-ksys/
├── ksys_app/              # 메인 애플리케이션 패키지
├── requirements.txt       # Python 의존성
├── rxconfig.py           # Reflex 설정
├── .env                  # 환경변수 (TS_DSN, APP_ENV)
├── venv/                 # 가상환경
└── [문서 및 설정 파일들]
```

### **ksys_app/ 패키지 구조**

#### **1. 메인 앱 진입점**
- **`ksys_app.py`** (745줄)
  - 역할: Reflex 앱 정의, 3개 페이지 라우팅
  - 의존성: components/, states/dashboard.py
  - 페이지: `/` (대시보드), `/trend`, `/tech`

#### **2. 상태 관리 (states/)**
- **`dashboard.py`**
  - 역할: 메인 상태 클래스, 실시간 업데이트 로직
  - 의존성: queries/*.py, utils/cache.py
  - 핵심 기능: KPI 계산, 차트 데이터, 실시간 모드

- **`data.py`**
  - 역할: 데이터 모델 및 타입 정의

#### **3. 데이터베이스 레이어**
- **`db.py`**
  - 역할: PostgreSQL 연결 풀 관리
  - 기능: AsyncConnectionPool, 타임아웃 설정

- **`queries/`** (8개 모듈)
  ```
  ├── metrics.py      # 시계열 데이터 쿼리 (동적 LIMIT)
  ├── latest.py       # 최신 스냅샷 데이터
  ├── features.py     # 5분 통계 피처
  ├── indicators.py   # 기술 지표 (SMA, Bollinger)
  ├── tags.py         # 태그 목록
  ├── qc.py          # QC 규칙 관리
  ├── alarms.py      # 알람 로직
  └── realtime.py    # 실시간 데이터
  ```

#### **4. UI 컴포넌트 (components/) - 정리된 13개**
```
├── layout.py           # 메인 셸, 네비게이션
├── kpi_tiles.py       # KPI 대시보드 타일 (Chakra UI 사용)
├── gauge.py           # 게이지 컴포넌트
├── features_table.py  # Trend 페이지 테이블
├── indicators_table.py # Tech 페이지 테이블
├── realtime_chart.py  # 실시간 차트
├── mini_chart.py      # 미니 차트
├── status_badge.py    # 상태 배지
├── alarms.py         # 알람 컴포넌트
├── card.py           # 카드 래퍼
└── tooltip_props.py  # 툴팁 속성
```

**실제 게이지 구현**: Reflex Chakra UI의 `rc.circular_progress` 사용

#### **5. 유틸리티**
- **`utils/cache.py`**
  - 역할: TTL 캐시 시스템 (최대 100개 항목)
  - 기능: 비동기 락, 자동 만료 정리

- **`security.py`**
  - 역할: 보안 검증 모듈

#### **6. 기타**
- **`models/models.py`**: Pydantic 데이터 모델
- **`api/gauge.py`**: API 엔드포인트
- **`tests/`**: 테스트 스위트 (4개 테스트 파일)
- **`scripts/`**: 운영 스크립트 (3개)

---

## 🔄 파일 간 의존성 관계

### **메인 데이터 플로우**
```
ksys_app.py
    ↓
states/dashboard.py 
    ↓
queries/*.py 
    ↓
db.py 
    ↓
TimescaleDB Views
```

### **컴포넌트 의존성 트리**
```
ksys_app.py
├── components/layout.py (셸)
│   ├── components/kpi_tiles.py (Chakra UI)
│   │   ├── components/gauge.py
│   │   └── components/status_badge.py
│   ├── components/features_table.py
│   ├── components/indicators_table.py
│   └── components/realtime_chart.py
└── states/dashboard.py
    ├── queries/*.py
    ├── utils/cache.py
    └── db.py
```

### **상세 Import 맵**

#### **ksys_app.py → components/**
```python
from .components.layout import shell, stat_card
from .components.kpi_tiles import unified_kpi_card, mini_stat_card, sensor_detail_modal
from .components.gauge import radial_gauge
from .components.features_table import features_table
from .components.indicators_table import indicators_table
from .states.dashboard import DashboardState as D
```

#### **states/dashboard.py → queries/**
```python
from ..queries.metrics import get_series_for_tag, get_series_realtime
from ..queries.latest import get_latest_all, get_latest_for_tag
from ..queries.features import get_features_for_tag
from ..queries.indicators import get_indicators_for_tag
from ..queries.tags import get_unique_tags
from ..queries.qc import get_qc_rules
from ..queries.alarms import get_alarm_status
from ..queries.realtime import get_realtime_data
from ..utils.cache import cached_async
```

---

## 🎯 핵심 기능별 파일 그룹

### **1. 대시보드 페이지 (`/`)**
- **메인**: `ksys_app.py::index()`
- **상태**: `states/dashboard.py`
- **컴포넌트**: `kpi_tiles.py`, `gauge.py`, `svg_gauge.py`
- **데이터**: `queries/latest.py`, `queries/realtime.py`

### **2. 트렌드 페이지 (`/trend`)**
- **메인**: `ksys_app.py::trend_page()`
- **컴포넌트**: `features_table.py`, 차트 함수들
- **데이터**: `queries/metrics.py`, `queries/features.py`

### **3. 기술지표 페이지 (`/tech`)**
- **메인**: `ksys_app.py::tech_page()`
- **컴포넌트**: `indicators_table.py`, 차트 함수들
- **데이터**: `queries/indicators.py`

### **4. 실시간 시스템**
- **상태 관리**: `states/dashboard.py::start_realtime()`
- **캐시**: `utils/cache.py`
- **데이터**: `queries/realtime.py`

---

## 📊 성능 최적화 적용

### **1. 데이터베이스 쿼리**
- **동적 LIMIT**: `queries/metrics.py::_calculate_dynamic_limit()`
  - 1-5분: 1440개, 12-24시간: 2880개, 7일: 1008개, 30일: 720개
- **뷰 기반 쿼리**: `public.influx_agg_*` 만 사용

### **2. 캐시 시스템**
- **TTL 캐시**: `utils/cache.py::TTLCache`
  - 최대 100개 항목, 자동 만료 정리
  - 메트릭 30초, 피처 60초, 스냅샷 0초

### **3. 실시간 업데이트**
- **주기**: 10초마다 자동 갱신
- **범위**: 9개 태그 통합 업데이트
- **최적화**: 페이지별 조건부 실행

---

## 🗄️ 데이터베이스 스키마

### **TimescaleDB Views**
```sql
public.influx_agg_1m     -- 1분 집계 (CAGG)
public.influx_agg_10m    -- 10분 집계 (CAGG)  
public.influx_agg_1h     -- 1시간 집계 (CAGG)
public.influx_latest     -- 최신 스냅샷 (View)
public.features_5m       -- 5분 통계 피처 (CAGG)
public.tech_ind_1m_mv    -- 기술 지표 (MV)
public.influx_qc_rule    -- QC 규칙 (Table)
```

### **주요 컬럼**
- **집계**: `bucket, tag_name, n, avg, sum, min, max, last, first, diff`
- **피처**: `mean_5m, std_5m, min_5m, max_5m, p10_5m, p90_5m, n_5m`
- **기술지표**: `avg, sma_10, sma_60, bb_top, bb_bot, slope_60`

---

## 🧹 정리 완료 현황

### **삭제된 파일 (25개) - 2단계 정리 완료**

#### **1단계 정리 (20개 파일)**
- **백업 파일**: `dashboard.py.backup`, `ksys_app_backup.py`
- **데모 컴포넌트**: `line_demo.py`, `states/line_demo.py`
- **트레이딩 관련**: `trading_state.py`, `options_table.py`, `orders_table.py`, `positions_table.py`
- **대체 UI**: `ksys_app_chakra.py`, `layout_chakra.py`, `kpi_tiles_chakra.py`
- **사용안함 게이지**: `gauge_apex.py`, `gauge_icon.py`, `gauge_recharts.py`, `simple_gauge.py`, `svg_gauge.py`

#### **2단계 백엔드 정리 (5개 파일 추가)**
- **알람 시스템**: `queries/alarms.py` (160+ 라인), `components/alarms.py` (201 라인)
- **API 모듈**: `api/gauge.py` (120+ 라인)
- **컴포넌트**: `components/card.py` (30+ 라인), `components/mini_chart.py` (50+ 라인)

### **코드 최적화 - 2단계 완료**

#### **1단계 정리**
- **ksys_app.py**: 790줄 → 745줄 (45줄 정리)
- **사용안함 함수**: `_custom_tooltip`, `trend_chart_toggle_button`, `tech_chart_toggle_button`
- **컴포넌트**: 26개 → 13개 (핵심만 유지)

#### **2단계 백엔드 정리**
- **함수 정리**: 8개 주요 사용안함 함수 제거 (660+ 라인)
  - `sensor_detail_modal()` (220+ 라인)
  - `realtime_kpi_card()` (69 라인)
  - `mini_stat_card()` (13 라인)
  - `tech_indicators()` (12 라인)
  - `simulate_continuous_data_stream()` (6 라인)
  - 알람 관련 함수 5개 (160+ 라인)
- **모델 정리**: Trading 관련 TypedDict 5개 제거 (ChartDataPoint, Option, Order, Position, StockInfo)
- **Import 최적화**: 불필요한 import 3개 제거
- **총 정리량**: 1,360+ 라인 제거

### **성능 개선**
- **동적 쿼리 제한**: 시간 창 기반 LIMIT 자동 계산
- **TTL 캐시 최적화**: 크기 제한, 자동 정리
- **메모리 효율성**: 불필요한 imports 및 변수 제거

---

## 🚀 실행 환경

### **환경변수**
```bash
TS_DSN=postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable
APP_ENV=development
TZ=Asia/Seoul
```

### **실행 명령**
```bash
source venv/bin/activate
reflex run
```

### **접속 주소**
- **Frontend**: http://localhost:13000/
- **Backend API**: http://localhost:8000/

---

## 📈 현재 운영 상태

- ✅ **데이터 연결**: 9개 태그 정상 수신
- ✅ **실시간 업데이트**: 10초 주기 자동 갱신
- ✅ **3개 페이지**: Dashboard, Trend, Tech 모두 정상
- ✅ **성능**: 캐시 적용, 쿼리 최적화 완료

이 문서는 현재 시스템의 정확한 상태를 반영하며, 향후 개발 시 참고 자료로 활용 가능합니다.