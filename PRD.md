# Ksys Dashboard PRD (Reverse‑engineered from current app)

본 문서는 "현재 정상 동작 화면"과 DB View 스키마만 근거로 작성되었다. 추측 금지, 변경은 본 PRD 갱신 후에만 구현한다.

**최신 업데이트**: 2025-08-26 코드 정리 완료 - 불필요한 파일 제거, 동적 쿼리 최적화, TTL 캐시 개선

## 0) 아키텍처(운영 파이프라인)
- 데이터 플로우
  - Edge → MQTT Broker(Mosquitto)
  - influx-DB : PLC 데이터 수집(ingest) 
  - Node-RED: influx-DB 데이터 수집(ingest), 변환(transform), QC 태깅, TimescaleDB 저장, mqtt (송신) 
  - TimescaleDB: 하이퍼테이블, Continuous Aggregate(CAGG), Timescale Toolkit
  - Python ML 서비스: 시계열 예측·이상탐지 → 결과 TimescaleDB 반영
  - Reflex 프런트엔드: 대시보드(UI/UX 최적화)
  - MCP(Model Context Protocol): 데이터·모델 분석 툴과 프롬프트 챗 연동

## 1) 라우트 / 내비게이션 (UI 관찰)
- `/` Dashboard (현재 기본)
- `/trend` Trend
- `/tech` Tech Indicator

## 2) 위젯 인벤토리 (현재 페이지 `/`) - 정리된 구현
- Latest snapshot 테이블
  - 컬럼: TAG | Time Stamp | Value | Comm. | Alarm.
  - 예시 행: `D100 | 2025-08-15 16:26:07.303478+09:00 | 190 | ● | -` (현재 Alarm는 placeholder '-').
- KPI 타일 그리드(각 태그별)
  - 타이틀: `D100`, `D101`, …, `D302`
  - 범위 배지: 예) `0.0 ~ 200.0`, `0.0 ~ 20000.0` (QC min/max)
  - 값: 굵은 수치(예: `190.0`)
  - 타임스탬프: `2025-08-15 16:26:07` (Asia/Seoul)
  - 증감: `+0.0%` + 문구(`increase from last window`)
  - 미니 통계: Count/Min/Max/First/Last
  - 게이지: SVG 기반 원형 게이지 (svg_gauge.py)
- 컨트롤(윈도우/버킷)
  - 옵션: 1m, 5m(기본), 10m, 60m, 12h, 24h, 48h, 7d, 14d, 30d, 3m, 6m, 12m

**정리된 컴포넌트 구조** (14개 파일):
- `kpi_tiles.py` - KPI 대시보드 타일
- `gauge.py`, `svg_gauge.py` - 게이지 컴포넌트 (SVG 기반)
- `layout.py` - 레이아웃 셸
- `table_components.py` - 테이블 컴포넌트
- `modal.py`, `popover.py` - UI 모달/팝오버
- `navbar.py`, `sidebar.py` - 내비게이션
- `recharts_components.py` - 차트 컴포넌트

## 3) 데이터 소스 (DB 스키마 확인됨)
- 시계열 Aggregates: `public.influx_agg_1m|10m|1h`
  - 컬럼: `bucket timestamptz, tag_name text, n bigint, avg, sum, min, max, last, first, diff double precision`
- 최신값: `public.influx_latest(tag_name text, value double precision, ts timestamptz)`
- 피처: `public.features_5m(bucket, tag_name, mean_5m, std_5m, min_5m, max_5m, p10_5m, p90_5m, n_5m)`
- QC 규칙: `public.influx_qc_rule(tag_name, min_val, max_val, max_step, max_gap_seconds, allow_negative, enabled, meta, warn_min, warn_max, crit_min, crit_max, roc_max_per_min, spike_zscore, deadband_pct)`

## 4) 계산 규칙 (State에서 확정 → UI는 표현만)
- gauge_pct (0..100)
  - 우선 QC 범위: `(last - min_val) / (max_val - min_val) * 100` → clamp 0..100
  - QC 미존재 시 윈도우 범위(min..max)
- status_level (게이지 색)
  - 0: 정상(green), 1: 경고(amber), 2: 치명(red)
  - 기준: `warn/crit` 우선, 하드(min/max) 위반은 치명
- delta_pct (실제 구현)
  - "최근 두 버킷"의 `last` 값으로 계산: `(last_in_win - prev_last_in_win) / prev_last_in_win * 100`
  - 분모가 `NULL/0`이면 `0`
- range_label
  - `"{min_val:.1f} ~ {max_val:.1f}"` (QC 없으면 윈도우 범위)
- Comm/Alarm 배지(현재 구현 상태)
  - Comm: 최신 시각과 버킷 간격 기준 OK/지연(화면에 `●` 표시)
  - Alarm: 아직 placeholder('-'); QC 위반 배지는 차기 반영

## 5) 위젯 계약 (각 타일)
입력(State→UI)
```json
{
  "title": "D100",
  "value_s": "190.0",
  "delta_pct": 0.0,
  "delta_s": "+0.0%",
  "gauge_pct": 95.0,
  "status_level": 0,
  "ts_s": "2025-08-15 16:26:07",
  "range_label": "0.0 ~ 200.0"
}
```
표현 규칙
- 게이지 색: `status_level`
- 화살표/증감 색: `delta_pct` (중립=회색/마이너스)
- 타이틀 옆 `range_label` 항상 노출

## 6) 성능/캐시/에러 상태 - 최적화된 구현
- 성능 목표: 24h 윈도우 < 300ms(agg 조회), 30d < 1.2s
- 캐시(최적화된 구현): TTL 캐시 - 메트릭 30s, 피처 60s, **스냅샷 0s(항상 최신 조회)**
  - 최대 크기 제한: 100개 항목, 만료 항목 자동 정리
  - 비동기 락으로 동시성 제어
- 쿼리 최적화: 시간 창 기반 동적 LIMIT 적용
  - 1-5분: 1440 (1일), 12-24시간: 2880 (2일), 7일: 1008개, 30일: 720개
- 에러: DSN/타임아웃/빈 데이터 메시지 표준화

## 7) 시험 성적서(샘플 시드)
`ksys_app/tests/sheets/kpi_24h.md`
```
[TestCase] KPI tile – D100 – 24h – 1m
- DB: "최근 두 버킷"의 last로 delta_pct_expected 계산
- QC: min_val/max_val from influx_qc_rule → gauge_pct_expected
- UI 관측: 값/증감/배지/게이지 색
[판정]
- |ui.delta_pct - expected.delta_pct| ≤ 0.1
- |ui.gauge_pct - expected.gauge_pct| ≤ 1.0
- ui.status_level == expected.status_level
- ui.range_label == expected.range_label
```
동일 템플릿으로 `D200`, `D300` 케이스 추가.

## 8) 코딩 룰 연동 (요약)
- PRD 우선, 테스트 우선. 구현 전 `PRD.md`/시험 성적서부터 갱신.
- 계산은 State에서 확정, UI는 표현만.
- View만 조회, 파라미터/리밋/타임아웃 필수.

## 9) 변경 이력
- 2025‑08‑15: 현재 동작 역공학하여 PRD 재정의(라우트/위젯/계산/계약/시험 성적서)
- 2025-08-26: 코드 정리 완료 - 19개 파일 삭제 (3,539 라인), 동적 쿼리 제한 적용, TTL 캐시 최적화
  - **삭제된 파일**: 백업 파일, 데모 컴포넌트, 트레이딩 관련 코드, 대체 UI 구현
  - **최적화**: 쿼리 성능 향상, 메모리 효율성 개선, 컴포넌트 구조 단순화

## 10) Trend 페이지 (현재 동작 역공학)
- 라우트: `/trend`
- 컨트롤
  - Tag 선택: D100, D101, D102, D200, D201, D202, D300, D301, D302
  - 윈도우/버킷: 1m, 5m(기본), 10m, 60m, 12h, 24h, 48h, 7d, 14d, 30d, 3m, 6m, 12m
  - Refresh 버튼
- 시계열 차트(리스트 토글)
  - 체크박스: Average, Min, Max, Last, First (기본 모두 on)
  - 범례: Average / First / Last / Max / Min
  - 축: 시간(로컬, Asia/Seoul), 값
  - 예시 레인지(관찰): 2025‑08‑15 18:51~18:55, 수치 188~192
- 테이블: Measurement history
  - 헤더: `Num. | TAG | Time Stamp | avg | min | max | last | first | n`
  - 예시 행:
    - `1 | D100 | 2025‑08‑15 18:55:00+09:00 | 190.00 | 190.00 | 190.00 | 190.00 | 190.00 | 7`
    - `2 | D100 | 2025‑08‑15 18:54:00+09:00 | 190.00 | … | n=12` …
- 데이터 소스(가정 아님, DB 스키마 근거)
  - `public.influx_agg_1m|10m|1h` 뷰에서 선택 태그/윈도우/버킷 기준으로 조회
- 계약(Trend)
  - 입력: `tag_name`, `time_range`, `bucket`
  - 출력(차트용): `{ bucket, tag_name, avg, min, max, last, first }[]`
  - 출력(테이블): 동일 컬럼 + `n`
- 수용 기준
  - 체크박스 on/off에 따라 해당 시리즈만 렌더
  - 테이블의 행 수와 차트 포인트 수가 일치(버킷=1 row)
  - 로컬 타임 포맷 일관 `YYYY‑MM‑DD HH:mm:ss+09:00`

## 11) Tech Indicator 페이지 (현재 동작 역공학)
- 라우트: `/tech`
- 컨트롤
  - Tag 선택: D100..D302
  - 윈도우/버킷: 1m, 5m(기본), 10m, 60m, 12h, 24h, 48h, 7d, 14d, 30d, 3m, 6m, 12m
- 시계열 차트
  - 범례: BB Bot, BB Top, SMA 10, SMA 60
  - 축: 로컬 타임, 값
- 테이블: Indicators (moving averages & bands)
  - 헤더: `Num. | TAG | Time Stamp | avg | sma_10 | sma_60 | bb_top | bb_bot | slope_60`
  - 예시 행: `1 | D100 | 2025‑08‑15 19:00:00+09:00 | 190.00 | 190.00 | 190.00 | 190.00 | 190.00 | 0`
- 데이터 소스(스키마 근거)
  - `public.tech_ind_1m_mv(bucket, tag_name, avg, sma_10, sma_60, bb_top, bb_bot, slope_60)`
- 계약(Tech)
  - 입력: `tag_name`, `time_range`, `bucket`
  - 출력(차트/테이블): `{ bucket, tag_name, avg, sma_10, sma_60, bb_top, bb_bot, slope_60 }[]`
- 수용 기준
  - 테이블/차트의 시계열 동기화(버킷 1개 = 1행)
  - 범례 토글(향후) 시리즈 가시성 반영

## 2) TimescaleDB 스키마(현재 DB 기준)
- 하이퍼테이블
  - `public.influx_hist` (원본 시계열 저장소; 컬럼 스키마는 운영 DB 기준)
  - `public.predictions` (예측값 저장소)
  - `public.anomalies` (이상탐지 이벤트)
- Continuous Aggregates(CAGG)
  - `public.influx_agg_1m`, `public.influx_agg_10m`, `public.influx_agg_1h`, `public.influx_agg_1d`
    - 공통 컬럼: `bucket timestamptz, tag_name text, n bigint, avg, sum, min, max, last, first, diff double precision`
  - `public.features_5m`
    - 컬럼: `bucket timestamptz, tag_name text, mean_5m, std_5m, min_5m, max_5m, p10_5m, p90_5m, n_5m`
- Materialized Views
  - `public.tech_ind_1m_mv`
    - 컬럼: `bucket timestamptz, tag_name text, avg, sma_10, sma_60, bb_top, bb_bot, slope_60`
- 최신 스냅샷
  - `public.influx_latest(tag_name, value, ts)`
- QC 규칙 테이블
  - `public.influx_qc_rule(tag_name, min_val, max_val, max_step, max_gap_seconds, allow_negative, enabled, meta, warn_min, warn_max, crit_min, crit_max, roc_max_per_min, spike_zscore, deadband_pct)`

> 비고: 사용자가 제시한 이상 스키마 예시는 참고용이며, 현재 운영 DB에서는 위 객체들이 확인되었다. 추가 객체(예: `sensor_raw`, `agg_1m`, `tech_1m`, `model_registry` 등)를 도입하려면 본 PRD에 정의 후 순차 적용한다.

## 12) TimescaleDB 목표 스키마(현 DB 기반 상세)
> 현 DB에서 확인되는 객체/컬럼을 기준으로, 운영 명세를 정리한다. 추가/변경은 본 섹션 개정 후 진행.

```sql
-- 원본 시계열 (현 DB: public.influx_hist)
-- 관찰 컬럼(정보 스키마):
-- ts timestamptz, tag_name text, value double precision, qc smallint, meta jsonb
-- (실제 생성문은 운영 저장소 참조)

-- 1분/10분/1시간/1일 집계 (CAGG)
-- 공통 스키마
-- bucket timestamptz, tag_name text,
-- n bigint, avg double precision, sum double precision,
-- min double precision, max double precision,
-- last double precision, first double precision,
-- diff double precision
-- 뷰 이름: public.influx_agg_1m|10m|1h|1d

-- 5분 피처 (CAGG)
CREATE MATERIALIZED VIEW public.features_5m AS -- (정의 참고)
-- columns
-- bucket timestamptz,
-- tag_name text,
-- mean_5m double precision,
-- std_5m double precision,
-- min_5m double precision,
-- max_5m double precision,
-- p10_5m double precision,
-- p90_5m double precision,
-- n_5m bigint;

-- 기술 지표 (MV)
-- public.tech_ind_1m_mv
-- bucket timestamptz, tag_name text,
-- avg double precision, sma_10 double precision, sma_60 double precision,
-- bb_top double precision, bb_bot double precision, slope_60 double precision

-- 최신 스냅샷
-- public.influx_latest(tag_name text, value double precision, ts timestamptz)

-- QC 룰
-- public.influx_qc_rule(
--   tag_name text,
--   min_val double precision,
--   max_val double precision,
--   max_step double precision,
--   max_gap_seconds integer,
--   allow_negative boolean,
--   enabled boolean,
--   meta jsonb,
--   warn_min double precision,
--   warn_max double precision,
--   crit_min double precision,
--   crit_max double precision,
--   roc_max_per_min double precision,
--   spike_zscore double precision,
--   deadband_pct double precision
-- )

-- 예측값 (하이퍼테이블)
-- public.predictions(
--   ts timestamptz,
--   tag_name text,
--   horizon interval,
--   yhat double precision,
--   pi_low double precision,
--   pi_high double precision,
--   model_id text,
--   version text,
--   features jsonb,
--   PRIMARY KEY (ts, tag_name, horizon, model_id, version)
-- )

-- 이상탐지 이벤트 (하이퍼테이블)
-- public.anomalies(
--   ts timestamptz,
--   tag_name text,
--   score double precision,
--   level text,
--   context jsonb,
--   PRIMARY KEY (ts, tag_name)
-- )
```

### 12.1) 목표 스키마 DDL(실DB 검증 기준, 컬럼/정책 명시)

```sql
-- 1) 원본 시계열 (하이퍼테이블)
CREATE TABLE IF NOT EXISTS public.influx_hist (
  ts timestamptz NOT NULL,
  tag_name text NOT NULL,
  value double precision NOT NULL,
  qc smallint DEFAULT 0,
  meta jsonb DEFAULT '{}'::jsonb,
  PRIMARY KEY (ts, tag_name)
);
-- 하이퍼테이블 등록(운영값 사용)
-- SELECT create_hypertable('public.influx_hist','ts');

-- 인덱스 (실DB 존재 확인)
CREATE UNIQUE INDEX IF NOT EXISTS influx_hist_pkey ON public.influx_hist (ts, tag_name);
CREATE INDEX IF NOT EXISTS idx_hist_tag_ts   ON public.influx_hist (tag_name, ts DESC);
CREATE INDEX IF NOT EXISTS influx_hist_ts_idx ON public.influx_hist (ts DESC);

-- 정책(실DB 잡 설정 기준)
-- 압축: 7일 후, 리텐션: 365일
-- SELECT add_compression_policy('public.influx_hist', INTERVAL '7 days');
-- SELECT add_retention_policy  ('public.influx_hist', INTERVAL '365 days');
```

```sql
-- 2) Continuous Aggregates (집계 스키마 공통)
-- 공통 컬럼: bucket timestamptz, tag_name text, n bigint,
--            avg/sum/min/max/last/first/diff double precision

-- 1분
CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_1m
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 minute', ts) AS bucket,
       tag_name,
       count(*) AS n,
       avg(value)  AS avg,
       sum(value)  AS sum,
       min(value)  AS min,
       max(value)  AS max,
       last(value, ts)  AS last,
       first(value, ts) AS first,
       last(value, ts) - first(value, ts) AS diff
FROM public.influx_hist
GROUP BY 1,2;
-- 정책(실DB 잡 설정): start_offset '2 hours', end_offset '1 minute', schedule '1 minute'

-- 10분
CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_10m
WITH (timescaledb.continuous) AS
SELECT time_bucket('10 minutes', ts) AS bucket,
       tag_name,
       count(*) AS n,
       avg(value)  AS avg,
       sum(value)  AS sum,
       min(value)  AS min,
       max(value)  AS max,
       last(value, ts)  AS last,
       first(value, ts) AS first,
       last(value, ts) - first(value, ts) AS diff
FROM public.influx_hist
GROUP BY 1,2;
-- 정책: start_offset '1 day', end_offset '10 minutes', schedule '10 minutes'

-- 1시간
CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_1h
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', ts) AS bucket,
       tag_name,
       count(*) AS n,
       avg(value)  AS avg,
       sum(value)  AS sum,
       min(value)  AS min,
       max(value)  AS max,
       last(value, ts)  AS last,
       first(value, ts) AS first,
       last(value, ts) - first(value, ts) AS diff
FROM public.influx_hist
GROUP BY 1,2;
-- 정책: start_offset '7 days', end_offset '1 hour', schedule '1 hour'

-- 1일
CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_1d
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', ts) AS bucket,
       tag_name,
       count(*) AS n,
       avg(value)  AS avg,
       sum(value)  AS sum,
       min(value)  AS min,
       max(value)  AS max,
       last(value, ts)  AS last,
       first(value, ts) AS first,
       last(value, ts) - first(value, ts) AS diff
FROM public.influx_hist
GROUP BY 1,2;
-- 정책: start_offset '730 days', end_offset '1 day', schedule '1 day'
```

```sql
-- 3) 5분 피처(CAGG)
CREATE MATERIALIZED VIEW IF NOT EXISTS public.features_5m
WITH (timescaledb.continuous) AS
SELECT time_bucket('5 minutes', ts) AS bucket,
       tag_name,
       avg(value)                  AS mean_5m,
       stddev_samp(value)          AS std_5m,
       min(value)                  AS min_5m,
       max(value)                  AS max_5m,
       approx_percentile(value,0.1) AS p10_5m,
       approx_percentile(value,0.9) AS p90_5m,
       count(*)                    AS n_5m
FROM public.influx_hist
GROUP BY 1,2;
```

```sql
-- 4) 기술 지표(MV)
CREATE MATERIALIZED VIEW IF NOT EXISTS public.tech_ind_1m_mv AS
SELECT bucket,
       tag_name,
       avg,
       avg(avg) OVER w10 AS sma_10,
       avg(avg) OVER w60 AS sma_60,
       avg + 2*stddev_samp(avg) OVER w20 AS bb_top,
       avg - 2*stddev_samp(avg) OVER w20 AS bb_bot,
       (avg - lag(avg, 60) OVER (PARTITION BY tag_name ORDER BY bucket)) AS slope_60
FROM public.influx_agg_1m
WINDOW
  w10 AS (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 9  PRECEDING AND CURRENT ROW),
  w20 AS (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
  w60 AS (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 59 PRECEDING AND CURRENT ROW);
```

```sql
-- 5) 최신 스냅샷(View)
CREATE OR REPLACE VIEW public.influx_latest AS
SELECT DISTINCT ON (tag_name)
       tag_name, value, ts
FROM public.influx_hist
ORDER BY tag_name, ts DESC;
```

```sql
-- 6) QC 규칙(테이블)
CREATE TABLE IF NOT EXISTS public.influx_qc_rule (
  tag_name text PRIMARY KEY,
  min_val double precision,
  max_val double precision,
  max_step double precision,
  max_gap_seconds integer,
  allow_negative boolean,
  enabled boolean,
  meta jsonb DEFAULT '{}'::jsonb,
  warn_min double precision,
  warn_max double precision,
  crit_min double precision,
  crit_max double precision,
  roc_max_per_min double precision,
  spike_zscore double precision,
  deadband_pct double precision
);
```

```sql
-- 7) 예측값(하이퍼테이블)
CREATE TABLE IF NOT EXISTS public.predictions (
  ts timestamptz NOT NULL,
  tag_name text NOT NULL,
  horizon interval NOT NULL,
  yhat double precision NOT NULL,
  pi_low double precision,
  pi_high double precision,
  model_id text NOT NULL,
  version text NOT NULL,
  features jsonb DEFAULT '{}'::jsonb,
  PRIMARY KEY (ts, tag_name, horizon, model_id, version)
);
-- SELECT create_hypertable('public.predictions','ts');

CREATE UNIQUE INDEX IF NOT EXISTS predictions_pkey ON public.predictions (ts, tag_name, horizon, model_id, version);
CREATE INDEX IF NOT EXISTS idx_pred_tag_ts ON public.predictions (tag_name, ts DESC);
CREATE INDEX IF NOT EXISTS predictions_ts_idx ON public.predictions (ts DESC);
```

```sql
-- 8) 이상탐지 이벤트(하이퍼테이블)
CREATE TABLE IF NOT EXISTS public.anomalies (
  ts timestamptz NOT NULL,
  tag_name text NOT NULL,
  score double precision NOT NULL,
  level text NOT NULL,
  context jsonb DEFAULT '{}'::jsonb,
  PRIMARY KEY (ts, tag_name)
);
-- SELECT create_hypertable('public.anomalies','ts');

CREATE UNIQUE INDEX IF NOT EXISTS anomalies_pkey      ON public.anomalies (ts, tag_name);
CREATE INDEX        IF NOT EXISTS anomalies_ts_idx    ON public.anomalies (ts DESC);
CREATE INDEX        IF NOT EXISTS anomalies_tag_ts_desc ON public.anomalies (tag_name, ts DESC);
```

---

## 부록 A) v0 베이스라인 PRD(복원·병합)
아래 내용은 초기 버전에서 복원한 요구사항을 현재 PRD와 병행 참조하기 위한 부록입니다. 본문(섹션 0~12.1)은 실DB/실화면 역공학 기준이며, 충돌 시 본문을 우선합니다.

### A.1 Purpose & Goals
- EcoAnP 시계열(metrics per `tag_name`)을 Reflex + TimescaleDB로 실시간 대시보드 제공
- 윈도우별 다운샘플(1m/10m/1h)과 지표 오버레이(tech indicators), 스냅샷/피처 테이블 지원

### A.2 Users & Personas
- Operations: 최신값/안정성/이상 모니터링
- Data Analyst: 24h/7d/30d 트렌드/지표 점검
- SRE/DevOps: 데이터 신선도, 잡/정책 상태 점검

### A.3 Scope
In scope
- 헤더 탭 + 3열 반응형 그리드(Tailwind V4)
- rx.recharts 라인차트(적응 다운샘플, 지표 오버레이)
- 테이블: 5분 피처, 최신 스냅샷, 간단 이벤트 리스트
- 컨트롤: time_range, bucket(read‑only 매핑), tag 필터
- TimescaleDB public 뷰/MatView만 사용

Out of scope(초기)
- 쓰기 경로, 원본 하이퍼테이블 직접 조회, 권한 UI
- 명시 지표 외 고급 분석

### A.4 Data Sources (discovered)
- `public.influx_agg_1m|10m|1h` (bucket, tag_name, n, avg, sum, min, max, last, first, diff)
- `public.influx_latest(tag_name, value, ts)`
- `public.features_5m(bucket, tag_name, mean_5m, std_5m, min_5m, max_5m, p10_5m, p90_5m, n_5m)`
- `public.tech_ind_1m_mv(bucket, tag_name, avg, sma_10, sma_60, bb_top, bb_bot, slope_60)`
Note: DB는 UTC, UI에서 Asia/Seoul 변환. 프로덕션은 read‑only 롤, 모든 SQL 파라미터화.

### A.5 Functional Requirements
- Header: 탭(Overview/Features/Indicators), 우측 글로벌 필터(tag), window/bucket, Refresh
- Chart Panel: `avg` over `bucket`; 지표 오버레이(SMA/Bollinger/slope); 도메인 패딩 10%; 로컬타임 툴팁; ≤24h→1m, 24h–7d→10m, >7d→1h
- Tables: latest(`influx_latest`), features(`features_5m`)
- Controls: time_range 24h/7d/30d; bucket 파생(read‑only); tag 필터
- States: loading/empty/error

### A.6 Non‑Functional
- 성능: 첫 차트 <2s, 페이로드 <50KB, 쿼리 24h<300ms/30d<1.2s
- 가용성: 일시 DB 오류에도 UI 복원/재시도, 캐시 사용
- 보안: 클라 시크릿 금지, ENV만
- 접근성: 키보드 접근, 대비

### A.7 Query Contracts(Parameterized)
Timeseries(adaptive)
```sql
SELECT bucket, tag_name, avg, min, max
FROM public.influx_agg_1m
WHERE bucket >= now() - $1::interval
  AND ($2::text IS NULL OR tag_name = $2)
ORDER BY bucket
LIMIT 10000;
```
Latest
```sql
SELECT tag_name, value, ts
FROM public.influx_latest
WHERE ($1::text IS NULL OR tag_name = $1)
ORDER BY tag_name
LIMIT 1000;
```
Features 5m
```sql
SELECT bucket, tag_name, mean_5m, std_5m, min_5m, max_5m, p10_5m, p90_5m, n_5m
FROM public.features_5m
WHERE bucket >= now() - $1::interval
  AND ($2::text IS NULL OR tag_name = $2)
ORDER BY bucket
LIMIT 10000;
```
Indicators(1m)
```sql
SELECT bucket, tag_name, avg, sma_10, sma_60, bb_top, bb_bot, slope_60
FROM public.tech_ind_1m_mv
WHERE bucket >= now() - $1::interval
  AND ($2::text IS NULL OR tag_name = $2)
ORDER BY bucket
LIMIT 10000;
```

### A.8 Architecture & State
- Reflex + Tailwind V4, rx.recharts
- `rx.State` + `@rx.event(background=True)`(DB‑backed; 시뮬레이션 없음)
- In‑memory TTL cache: 15–60s(메트릭), 5m(리스트); 필터 변경 시 무효화

### A.9 Observability
- 쿼리 지문/시간/rowcount, 캐시 hit/miss
- WS 크기/SSR 크기 추적; 300KB 초과 자산 경고

### A.10 Performance Budgets
- 첫 차트 <2s(유선)/<4s(4G); 각 쿼리 24h<300ms/30d<1.2s; CPU idle >70%

### A.11 Rollout
- Dev(WSL2) → Staging(cloud Timescale RO) → Prod
- 런타임 타겟: ksys_app http://localhost:13000/ , ksys_web http://localhost:3000/
- 정책: `public.influx_hist` retention 1y, compression 7d, CAGG refresh per jobs

### A.12 Acceptance Criteria & Smoke Test
- 24h 윈도우 렌더/오버레이/테이블 정상, 컨트롤 변경 시 갱신
- 스모크: 페이지 로드<2s, 윈도우 전환, tag 선택, DSN 오류 상태 표시→복구

### A.13 Prompting Quickstart & Templates
- 동일(본문 정책 준수)

### A.14 Wireframes (Mermaid)
본문과 동일 구성을 유지.

### A.15 Operational Runbook
- Jobs/Policies 점검 쿼리
```sql
SELECT job_id, application_name, schedule_interval, config,
       hypertable_schema, hypertable_name, check_schema, check_name
FROM timescaledb_information.jobs
ORDER BY job_id;
```
- Retention(1y) idempotent DO 블록
(본문 스니펫 준용)
- Index hint (현 스키마 정정: time→ts)
```sql
CREATE INDEX IF NOT EXISTS ON public.influx_hist (tag_name, ts DESC);
```

---

## 부록 B) Ksys/EcoAnP Telemetry Dashboard — PRD v2.0(사용자 보완안 통합)
> 버전: 2.0 (보완의견 반영)
> 원칙: 실제 동작·DB View 스키마 기반. 추측 금지. 변경은 본 PRD 개정 후 적용.

### B0) 아키텍처(운영 파이프라인)
- Edge → **MQTT(Mosquitto)**
- **influx-DB**: PLC 데이터 수집
- **Node-RED**: ingest/변환/QC 태깅 → TimescaleDB 저장, MQTT 송신
- **TimescaleDB**: 하이퍼테이블, CAGG, Toolkit
- **Python ML**: 예측·이상탐지 → 결과 Timescale 반영
- **Reflex** UI: 대시보드(웹)
- **MCP**: 데이터/모델 분석 도구 및 프롬프트 연동(차기)

### B1) 라우트 / 내비게이션
- `/` Dashboard(기본)
- `/trend` Trend
- `/tech` Technical Indicators

### B2) 위젯 인벤토리(현재 `/` 기준)
- **Latest Snapshot**: `TAG | Time Stamp | Value | Comm. | Alarm.`
- **KPI 타일**: 범위 배지(QC 또는 윈도우), 값/타임스탬프/증감/미니통계/게이지
- **컨트롤**: 1m, 5m(기본), 10m, 60m, 12h, 24h, 48h, 7d, 14d, 30d, 3m, 6m, 12m

### B3) 데이터 소스(확인 스키마)
- `public.influx_agg_1m|10m|1h|1d` (bucket, tag_name, n, avg, sum, min, max, last, first, diff)
- `public.influx_latest(tag_name, value, ts)`
- `public.features_5m(bucket, tag_name, mean_5m, std_5m, min_5m, max_5m, p10_5m, p90_5m, n_5m)`
- `public.tech_ind_1m_mv(bucket, tag_name, avg, sma_10, sma_60, bb_top, bb_bot, slope_60)`
- `public.influx_qc_rule(…)
- (참고) `public.predictions`, `public.anomalies`

### B4) 계산 규칙(상태 확정)
- **gauge_pct**: QC `(last - min_val)/NULLIF(max_val-min_val,0)*100` (없으면 윈도우 `[min,max]`) → clamp 0..100
- **status_level**: `0 green | 1 amber | 2 red` (crit/warn 우선, hard 위반 치명)
- **delta_pct**: 직전 동일 길이 창의 `prev_last` 대비; 분모 `NULL/0`이면 0
- **range_label**: `"{min_val:.1f} ~ {max_val:.1f}"` 또는 윈도우 범위
- **Comm/Alarm**
  - Comm: 최신 시각과 버킷 간격 기준 OK/지연(화면에 `●` 표시)
  - Alarm: 아직 placeholder('-'); QC 위반 배지는 차기 반영

### B5) 위젯 계약(타일)
(State→UI 입력 스키마는 본문 §5와 동일)

### B6) 태스크 플로우(운영 7종)
| Step | Actor | Trigger | Input | UI/Prompt | System Action | R/W | Success | Failure | SLA | Log/Event | Metric |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 대시보드 초기 로드 | Browser | `/` | time_range=24h | Skeleton→KPI/Chart | 해상도 매핑→준비문 실행→캐시쓰기 | R/W | 타일+차트 렌더 | timeout | 2s | dash_load_ok | FCP, TTFB |
| F2 기간 전환 | User | 24h↔30d | time_range | 버튼 유지 | 뷰 선택→쿼리→재렌더 | R | 갱신 | payload_bloat | 600ms | range_change_ok | p95 query |
| F3 태그 필터 | User | 입력/선택 | tag_name | Debounce 300ms | 파라미터 쿼리 | R | 결과 | zero-row | 800ms | tag_filter_ok | 전환율 |
| F4 스냅샷 갱신 | Scheduler | 60s | tag? | 표 갱신 | `influx_latest` 조회 | R | 갱신 | 지연 | 500ms | snapshot_refresh | 지연(ms) |
| F5 테크 오버레이 | User | 토글 | flags | 범례 토글 | `tech_ind_1m_mv` 컬럼 추가 | R | 표시 | 불일치 | 400ms | overlay_toggle | FPS |
| F6 Comm/Alarm 계산 | System | F4 후 | latest row | 배지 색 | Comm/Alarm 판정 | R | 배지 표시 | 판정실패 | 20ms | qc_badge_eval | SLA hit |
| F7 장애 회복 | DB down | 에러 | - | ErrorBox+Retry | 지수재시도, 캐시서빙 | R:cache | 복구 | 루프 | 즉시 | db_fail/db_recover | 가용성 |

### B7) 상태·오류 모델
- 페이지: `idle → loading → loaded | empty | error → retrying → loaded`
- 데이터 신뢰: `fresh(<TTL) | stale(≥TTL)`
- 오류코드: `DB_TIMEOUT, DB_CONN, NO_ROWS, SCHEMA_DRIFT, PAYLOAD_BLOAT, WS_FAIL`
- 백오프: `1s, 2s, 4s, 8s`(최대)
- 규칙: error+캐시 존재 시 **stale 배지**로 렌더

### B8) 버킷-시간창 매핑(고정)
- `≤24h → 1m`, `>24h & ≤14d → 10m`, `>14d & ≤90d → 1h`, `>90d → 1d`

### B9) 쿼리 계약(준비문 & 타임아웃)
세션 가드:
```sql
SET LOCAL statement_timeout='900ms';
SET LOCAL idle_in_transaction_session_timeout='5s';
```
Timeseries(해상도별 준비문 4종):
```sql
SELECT bucket, tag_name, avg, min, max, last, first, n
FROM public.influx_agg_1m
WHERE bucket >= now() - $1 AND ($2 IS NULL OR tag_name=$2)
ORDER BY bucket
LIMIT 10000;
```
Indicators:
```sql
SELECT bucket, tag_name, avg, sma_10, sma_60, bb_top, bb_bot, slope_60
FROM public.tech_ind_1m_mv
WHERE bucket >= now() - $1 AND ($2 IS NULL OR tag_name=$2)
ORDER BY bucket
LIMIT 10000;
```
Features:
```sql
SELECT bucket, tag_name, mean_5m, std_5m, min_5m, max_5m, p10_5m, p90_5m, n_5m
FROM public.features_5m
WHERE bucket >= now() - $1 AND ($2 IS NULL OR tag_name=$2)
ORDER BY bucket
LIMIT 10000;
```

### B10) KPI 계산 SQL(검증용)
(본문 §10 스니펫과 동일; `prev_last` 정의 포함)

### B11) Trend/Tech 페이지
- Trend: 토글(Avg/Min/Max/Last/First), 테이블/차트 1:1 동기
- Tech: 테이블(Avg/SMA10/SMA60/BBTop/BBBot/Slope), 범례 토글(차기)

### B12) 캐시·페이로드 예산
- TTL: metrics 30s / features 60s / snapshot 300s
- 캐시 키: `sha1(sql+params)`; 값 `{rows,rowcount,fetched_ms}`
- WS/SSR 페이로드 경고 임계: 300KB

### B13) 관측·로그 계약
- 이벤트: `dash_load_ok`, `range_change_ok`, `snapshot_refresh`, `overlay_toggle`, `qc_badge_eval`, `db_fail`, `db_recover`, `payload_bloat`
- 공통 필드: `{range, tag, view, rowcount, dur_ms, cache_hit}`

### B14) 비기능/성능
- 첫 차트 `< 2s(wired) / < 4s(4G)`
- 쿼리 p95 `< 300ms(24h/1m)`, `< 1.2s(30d/1h)`
- 페이로드 평균 `< 50KB`, CPU idle `> 70%`

### B15) 보안·권한
- 읽기 전용 롤, `public` 한정
- 모든 SQL **준비문**, 세션 타임아웃 강제
- ENV만 사용, 클라 비밀 금지

### B16) Timescale 정책
- CAGG 1m/10m/1h/1d 운용, refresh policy 적용
- 보존 365d / 압축 7d 유지
- Toolkit 미설치 시 percentile 대체

### B17) 런북(Quick)
정책/잡 확인:
```sql
SELECT job_id, application_name, schedule_interval, config,
       hypertable_schema, hypertable_name, check_schema, check_name
FROM timescaledb_information.jobs
ORDER BY job_id;
```
보존 정책(idempotent): (본문 스니펫 준용)
인덱스 힌트(컬럼 정정: `time`→`ts`):
```sql
CREATE INDEX IF NOT EXISTS ON public.influx_hist (tag_name, ts DESC);
```

### B18) 스캐폴딩(요지)
(현재 코드 구조와 일치하도록 본문 §19 참고)

### B19) 수용 기준(AC) & 테스트 시트
- AC 목록 및 시험 시트 항목은 본문 §20~§22 참조(동일 적용)

---

## 27) Disaster Recovery (DR) Runbook – 운영 수준 복구
> 목표: 빈 Timescale/Postgres 인스턴스에서 본 PRD만으로 “운영 동등 수준”의 스키마/정책/역할/잡을 재현한다. 데이터는 원천(Influx/Node‑RED/CSV)에서 재수집(backfill)하거나 백업으로 복원한다.

### 27.1 사전 조건
- PostgreSQL 16.x + TimescaleDB 2.x 이상
- 확장:
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;          -- 필수
CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit;  -- 선택(approx_percentile 등)
```
- 데이터베이스/스키마:
```sql
-- DB는 준비되어 있다고 가정(EcoAnP). 스키마는 public 사용.
```

### 27.2 운영 역할/권한(RO/APP)
```sql
-- 앱 읽기 전용 롤
DO $$BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='eco_ro') THEN
    CREATE ROLE eco_ro LOGIN PASSWORD 'CHANGE_ME_STRONG';
  END IF;
END$$;

-- 접근 권한(데이터베이스/스키마/객체)
GRANT CONNECT ON DATABASE "EcoAnP" TO eco_ro;
GRANT USAGE ON SCHEMA public TO eco_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO eco_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO eco_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO eco_ro;
```

### 27.3 스키마 부트스트랩(DDL + 하이퍼테이블)
> 순서: 원본 테이블 → 하이퍼테이블/청크 → 인덱스 → 보존/압축 → CAGG/MV → 최신 스냅샷 뷰

```sql
-- 원본(실DB 스키마 반영)
CREATE TABLE IF NOT EXISTS public.influx_hist (
  ts timestamptz NOT NULL,
  tag_name text NOT NULL,
  value double precision NOT NULL,
  qc smallint DEFAULT 0,
  meta jsonb DEFAULT '{}'::jsonb,
  PRIMARY KEY (ts, tag_name)
);
-- 하이퍼테이블(존재 시 무시)
SELECT create_hypertable('public.influx_hist','ts', if_not_exists=>true, migrate_data=>true, chunk_time_interval=> interval '7 days');

-- 인덱스(존재 시 무시)
CREATE UNIQUE INDEX IF NOT EXISTS influx_hist_pkey ON public.influx_hist (ts, tag_name);
CREATE INDEX IF NOT EXISTS idx_hist_tag_ts   ON public.influx_hist (tag_name, ts DESC);
CREATE INDEX IF NOT EXISTS influx_hist_ts_idx ON public.influx_hist (ts DESC);

-- 보존/압축 정책(존재 시 무시)
ALTER TABLE public.influx_hist SET (
  timescaledb.compress,
  timescaledb.compress_orderby = 'ts DESC',
  timescaledb.compress_segmentby = 'tag_name'
);
SELECT add_compression_policy('public.influx_hist', INTERVAL '7 days')
WHERE NOT EXISTS (
  SELECT 1 FROM timescaledb_information.jobs j
  WHERE j.hypertable_schema='public' AND j.hypertable_name='influx_hist'
    AND j.check_name = '_timescaledb_internal.policy_compression'
);
SELECT add_retention_policy('public.influx_hist', INTERVAL '365 days')
WHERE NOT EXISTS (
  SELECT 1 FROM timescaledb_information.jobs j
  WHERE j.hypertable_schema='public' AND j.hypertable_name='influx_hist'
    AND j.check_name = '_timescaledb_functions.policy_retention_check'
);
```

#### 27.3.1 CAGG/MV 생성
```sql
-- 공통 스키마: bucket, tag_name, n, avg, sum, min, max, last, first, diff
CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_1m
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 minute', ts) AS bucket, tag_name,
       count(*) n, avg(value) avg, sum(value) sum,
       min(value) min, max(value) max,
       last(value, ts) last, first(value, ts) first,
       last(value, ts) - first(value, ts) diff
FROM public.influx_hist GROUP BY 1,2;

CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_10m
WITH (timescaledb.continuous) AS
SELECT time_bucket('10 minutes', ts) AS bucket, tag_name,
       count(*) n, avg(value) avg, sum(value) sum,
       min(value) min, max(value) max,
       last(value, ts) last, first(value, ts) first,
       last(value, ts) - first(value, ts) diff
FROM public.influx_hist GROUP BY 1,2;

CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_1h
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', ts) AS bucket, tag_name,
       count(*) n, avg(value) avg, sum(value) sum,
       min(value) min, max(value) max,
       last(value, ts) last, first(value, ts) first,
       last(value, ts) - first(value, ts) diff
FROM public.influx_hist GROUP BY 1,2;

CREATE MATERIALIZED VIEW IF NOT EXISTS public.influx_agg_1d
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', ts) AS bucket, tag_name,
       count(*) n, avg(value) avg, sum(value) sum,
       min(value) min, max(value) max,
       last(value, ts) last, first(value, ts) first,
       last(value, ts) - first(value, ts) diff
FROM public.influx_hist GROUP BY 1,2;

-- Features 5m
CREATE MATERIALIZED VIEW IF NOT EXISTS public.features_5m
WITH (timescaledb.continuous) AS
SELECT time_bucket('5 minutes', ts) AS bucket, tag_name,
       avg(value) mean_5m, stddev_samp(value) std_5m,
       min(value) min_5m, max(value) max_5m,
       approx_percentile(value,0.1) p10_5m,
       approx_percentile(value,0.9) p90_5m,
       count(*) n_5m
FROM public.influx_hist GROUP BY 1,2;

-- Tech indicators MV
CREATE MATERIALIZED VIEW IF NOT EXISTS public.tech_ind_1m_mv AS
SELECT bucket,
       tag_name,
       avg,
       avg(avg) OVER w10 AS sma_10,
       avg(avg) OVER w60 AS sma_60,
       avg + 2*stddev_samp(avg) OVER w20 AS bb_top,
       avg - 2*stddev_samp(avg) OVER w20 AS bb_bot,
       (avg - lag(avg, 60) OVER (PARTITION BY tag_name ORDER BY bucket)) AS slope_60
FROM public.influx_agg_1m
WINDOW
  w10 AS (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 9  PRECEDING AND CURRENT ROW),
  w20 AS (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
  w60 AS (PARTITION BY tag_name ORDER BY bucket ROWS BETWEEN 59 PRECEDING AND CURRENT ROW);

-- Latest snapshot View
CREATE OR REPLACE VIEW public.influx_latest AS
SELECT DISTINCT ON (tag_name) tag_name, value, ts
FROM public.influx_hist
ORDER BY tag_name, ts DESC;
```

#### 27.3.2 CAGG 리프레시 정책(운영 값 적용)
```sql
-- 관측된 잡 설정을 재현(없으면 추가)
SELECT add_continuous_aggregate_policy('public.influx_agg_1m',
  start_offset => INTERVAL '2 hours', end_offset => INTERVAL '1 minute', schedule_interval => INTERVAL '1 minute')
WHERE NOT EXISTS (
  SELECT 1 FROM timescaledb_information.jobs j
  WHERE j.hypertable_schema='public' AND j.hypertable_name='influx_agg_1m'
);

SELECT add_continuous_aggregate_policy('public.influx_agg_10m',
  start_offset => INTERVAL '1 day', end_offset => INTERVAL '10 minutes', schedule_interval => INTERVAL '10 minutes')
WHERE NOT EXISTS (
  SELECT 1 FROM timescaledb_information.jobs j
  WHERE j.hypertable_schema='public' AND j.hypertable_name='influx_agg_10m'
);

SELECT add_continuous_aggregate_policy('public.influx_agg_1h',
  start_offset => INTERVAL '7 days', end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '1 hour')
WHERE NOT EXISTS (
  SELECT 1 FROM timescaledb_information.jobs j
  WHERE j.hypertable_schema='public' AND j.hypertable_name='influx_agg_1h'
);

SELECT add_continuous_aggregate_policy('public.influx_agg_1d',
  start_offset => INTERVAL '730 days', end_offset => INTERVAL '1 day', schedule_interval => INTERVAL '1 day')
WHERE NOT EXISTS (
  SELECT 1 FROM timescaledb_information.jobs j
  WHERE j.hypertable_schema='public' AND j.hypertable_name='influx_agg_1d'
);
```

### 27.4 QC 룰/마스터 데이터 복구
- CSV→DB 업서트:
```bash
python scripts/qc_sync.py   # data/qc/influx_qc_rule.csv 를 DB에 UPSERT
python scripts/qc_verify.py # CSV ↔ DB 드리프트 검증
```

### 27.5 데이터 백필(원천 기준)
- Influx/Node‑RED 재전송(추천): 파이프라인 재가동으로 최근 구간부터 채움
- CSV 백필: `COPY public.influx_hist (ts, tag_name, value, qc, meta) FROM STDIN CSV`
- 백필 후 CAGG 강제 리프레시(선택):
```sql
SELECT refresh_continuous_aggregate('public.influx_agg_1m', now()-interval '2 hours', now());
SELECT refresh_continuous_aggregate('public.influx_agg_10m', now()-interval '1 day',  now());
SELECT refresh_continuous_aggregate('public.influx_agg_1h', now()-interval '7 days', now());
SELECT refresh_continuous_aggregate('public.influx_agg_1d', now()-interval '730 days', now());
```

### 27.6 검증 체크리스트(자동 SQL)
```sql
-- 1) 확장
SELECT extname FROM pg_extension WHERE extname IN ('timescaledb','timescaledb_toolkit');
-- 2) 하이퍼테이블
SELECT hypertable_schema, hypertable_name FROM timescaledb_information.hypertables
WHERE hypertable_schema='public' ORDER BY 1,2;
-- 3) 인덱스
SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename IN ('influx_hist','predictions','anomalies') ORDER BY tablename,indexname;
-- 4) CAGG 존재
SELECT view_schema, view_name FROM timescaledb_information.continuous_aggregates ORDER BY 1,2;
-- 5) 정책/잡
SELECT job_id, hypertable_schema, hypertable_name, schedule_interval, config
FROM timescaledb_information.jobs ORDER BY job_id;
-- 6) QC 스키마
SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='influx_qc_rule' ORDER BY ordinal_position;
```

### 27.7 백업/복원 가이드
- 백업(pg_dump):
```bash
pg_dump -Fc -d EcoAnP -h <host> -U <user> -f ecoanp_$(date +%F).dump
```
- 복원(pg_restore):
```bash
createdb EcoAnP
pg_restore -d EcoAnP -h <host> -U <user> --create --clean ecoanp.dump
```
- PITR 사용 시: WAL 보관 설정/복구 타임 포인트는 운영 가이드에 따름.

### 27.8 앱 환경 설정(Reflex)
```bash
# .env (예시)
TS_DSN=postgresql://eco_ro:CHANGE_ME_STRONG@<host>:5432/EcoAnP?sslmode=disable
APP_ENV=production
TZ=Asia/Seoul
```

### 27.9 DR 스크립트 실행 순서(권장)
1. 27.1 확장 설치
2. 27.2 역할/권한
3. 27.3 스키마/하이퍼테이블/인덱스/정책
4. 27.3.1 CAGG/MV 생성
5. 27.3.2 CAGG 정책 등록
6. 27.4 QC 룰 업서트
7. 27.5 데이터 백필(필요 시) + 27.5 리프레시
8. 27.6 검증 SQL 일괄 실행
9. 앱 환경변수 설정 후 `reflex run`

### 27.10 DR 성공 기준(Runbook AC)
- 확장/하이퍼테이블/인덱스/정책/잡/뷰가 검증 SQL로 모두 확인됨
- `/` 대시보드가 정상 렌더(스냅샷/타일/차트)
- Trend/Tech 테이블과 차트 동기화(버킷=1행)
- KPI Δ%, 게이지, 범위 라벨 시험 시트 기준 통과

---

## 28) 통신 성공율 리포트 — `/comm` (Heatmap, 실DB 스키마 반영)
> 목적: 태그별(= `tag_name`) 최근 30일 × 24시간 통신 성공율을 한눈에. UTC 저장, UI에서 Asia/Seoul 변환.

### 28.1 스키마(운영 DB 기준으로 추가)
```sql
-- 기대 수신량/임계치(태그 마스터)
CREATE TABLE IF NOT EXISTS public.ingest_expectation (
  tag_name     text PRIMARY KEY,
  exp_per_min  integer NOT NULL DEFAULT 1,      -- 분당 기대 건수(기본 1)
  slo_warn     numeric NOT NULL DEFAULT 0.98,
  slo_crit     numeric NOT NULL DEFAULT 0.95,
  updated_at   timestamptz DEFAULT now()
);

-- 1시간 통신 성공율(CAGG) – 기반: public.influx_agg_1m (실DB 존재)
CREATE MATERIALIZED VIEW IF NOT EXISTS public.comm_success_1h
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 hour', a.bucket) AS bucket,   -- UTC
  a.tag_name,
  SUM(a.n)::bigint                                  AS recv_msgs,
  (COALESCE(e.exp_per_min,1) * 60)::bigint          AS exp_msgs,
  LEAST(1.0, GREATEST(0.0,
        SUM(a.n)::numeric / NULLIF(COALESCE(e.exp_per_min,1) * 60,0))) AS success_rate,
  GREATEST(0, (COALESCE(e.exp_per_min,1) * 60) - SUM(a.n))::bigint      AS missing_msgs,
  MAX(CASE WHEN a.n > 0 THEN a.bucket END)           AS last_seen_min   -- 마지막 수신 분(UTC)
FROM public.influx_agg_1m a
LEFT JOIN public.ingest_expectation e USING (tag_name)
GROUP BY 1,2,4;

-- 리프레시 정책(없으면 추가)
SELECT add_continuous_aggregate_policy('public.comm_success_1h',
  start_offset => INTERVAL '30 days', end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '15 minutes')
WHERE NOT EXISTS (
  SELECT 1 FROM timescaledb_information.jobs j
  WHERE j.hypertable_schema='public' AND j.hypertable_name='comm_success_1h'
);
```

### 28.2 조회 계약(준비문, 파라미터화)
히트맵(30d × 24h, 1태그, UTC 그리드)
```sql
-- eco_comm_heatmap($1 date, $2 text)
WITH days AS (
  SELECT gs::date AS d
  FROM generate_series($1::date, ($1::date + INTERVAL '29 days'), '1 day') gs
), hours AS (
  SELECT generate_series(0,23) AS h
), grid AS (
  SELECT (d + (h||':00')::time)::timestamptz AS bucket
  FROM days CROSS JOIN hours
)
SELECT
  g.bucket AS bucket_utc,
  $2 AS tag_name,
  c.success_rate,
  COALESCE(c.recv_msgs, 0) AS recv_msgs,
  (SELECT COALESCE(exp_per_min,1) FROM public.ingest_expectation e WHERE e.tag_name=$2) * 60 AS exp_msgs,
  c.missing_msgs,
  c.last_seen_min
FROM grid g
LEFT JOIN public.comm_success_1h c
  ON date_trunc('hour', c.bucket) = g.bucket
 AND c.tag_name = $2
ORDER BY g.bucket;
```
Outage 목록(30d, slo_crit 미달 연속 구간)
```sql
-- eco_comm_outages($1 date, $2 text)
WITH s AS (
  SELECT c.bucket, c.tag_name, c.success_rate,
         (c.success_rate < e.slo_crit) AS bad,
         c.bucket - LAG(c.bucket) OVER (PARTITION BY c.tag_name ORDER BY c.bucket) AS gap
  FROM public.comm_success_1h c
  LEFT JOIN public.ingest_expectation e USING (tag_name)
  WHERE c.tag_name = $2 AND c.bucket >= $1 AND c.bucket < $1 + INTERVAL '30 days'
), grp AS (
  SELECT *,
         SUM(CASE WHEN gap != INTERVAL '1 hour' THEN 1 ELSE 0 END)
         OVER (PARTITION BY tag_name ORDER BY bucket) AS gid
  FROM s WHERE bad
)
SELECT tag_name,
       MIN(bucket) AS start_ts_utc,
       MAX(bucket) + INTERVAL '1 hour' AS end_ts_utc,
       EXTRACT(EPOCH FROM (MAX(bucket) - MIN(bucket) + INTERVAL '1 hour'))/3600 AS hours
FROM grp
GROUP BY tag_name, gid
ORDER BY start_ts_utc;
```
태그 목록(실DB 기준)
```sql
-- eco_tags(): tag_name 리스트
SELECT tag_name FROM public.influx_latest ORDER BY tag_name;
```

### 28.3 라우트·상태
- Route: `/comm`
- State 필드(초기값 예)
  - `start_date: date = today-29d`
  - `tag_names: list[str]` (단일/다중 표시, 최초 1개 필수)
  - `cells: list[{bucket_utc, success_rate, recv_msgs, exp_msgs, missing_msgs, last_seen_min}]`
  - `outages: list[{start_ts_utc, end_ts_utc, hours}]`
  - `is_loading: bool`, `color_scale: str`(Red→Amber→Green 색각보정 팔레트)
- 이벤트: `prev_day()`, `next_day()`, `recent_30d()`, `refresh()`, `select_cell(ts)`

### 28.4 UI(요약)
- 상단 컨트롤: **Tag**(다중), **Start Date**, **Prev/Next**, **최근 30일**, **Refresh**
- 좌: 30×24 히트맵(가로=날짜 30, 세로=시간 0..23)
- 우: 선택 셀 상세 카드 + Outage 테이블(연속 임계 미달)
- 툴팁: 날짜/시간(로컬), `success_rate`, `recv/exp`, `missing`, `last_seen`
- 빈 칸: 데이터 없음 → 회색 해시 텍스처

### 28.5 성능·관측·TTL
- TTL: 히트맵 5m, Outage 5m, 태그 목록 5m
- 성능 목표: p95 `< 400ms`, 페이로드 `< 150KB`
- 로그: `comm_load_ok`, `comm_nav_prev`, `comm_nav_next`, `comm_recent30`, `comm_cell_select`

### 28.6 AC
- 30×24 히트맵 500ms 내 렌더(캐시 적중)
- 셀 클릭 팝업에 `success_rate`, `recv/exp`, `missing`, `last_seen` 정확
- Prev/Next/최근30일 동작 정확
- Outage 구간과 히트맵 연속성 일치
- 접근성 대비/텍스처/키보드 포커스 준수
