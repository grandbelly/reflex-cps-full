
# PRD — AIoT PLC 데이터 파이프라인 & Vibe 대시보드
작성일: 2025-08-17  
작성자: 아키텍트

---

## 0. 한 줄 요약
CSV 주소맵 한 장으로 **수집 → 전송 → 적재 → 집계 → 복제 → 분석 → 시각화**까지 자동화한다.  
현장(라즈베리파이)은 빠르고 단단하게. 원격(WSL+Pigsty)은 길게, 깊게.

---

## 1. 목적과 성공지표
### 1.1 목적
- PLC 데이터의 **완전 자동화**: CSV 주소맵으로 모든 구성 파일과 테이블을 생성.
- **저지연 현장 모니터링**과 **장기 저장·분석**의 분리.
- **유튜브 감성** 카드형 UX로 **즉시 이해 가능한** 뷰어 제공.

### 1.2 성공지표(KPI)
- 카드 첫 페인트 < 1.0s (로컬 1분 집계 기준)
- 상세 페이지 쿼리 < 2.5s (최근 7일, 1분 집계)
- 데이터 유실율 ≈ 0% (네트워크 복구 시 자동 재전송)
- CSV→운영 반영 소요 < 5분 (생성기 파이프라인)
- MTTR < 30분 (복구 플레이북/백업)

---

## 2. 범위
### 2.1 포함
- 주소맵 CSV 스키마/검증/버전관리
- Node-RED 폴링/정규화 → MQTT 발행
- Mosquitto 브로커
- Telegraf 구독 → InfluxDB(단기) + TimescaleDB(영속) 동시 적재
- Timescale **Hypertable, 압축, 보관, 연속 집계(1m/1h)**, 인덱스
- 원격 Pigsty(WSL)로 **논리 복제** 수신, ML/분석 공간 구성
- Reflex 기반 **Vibe 대시보드**(메인/디테일), 카드 자동 생성
- 품질/관측: 로그, 메트릭, 알람, 데이터 테스트

### 2.2 제외
- OT 네트워크/PLC 자체 보안 하드닝
- 모델링 코드(도메인별 ML 알고리즘 상세)
- 모바일 앱(웹 응답형으로 대체)

---

## 3. 페르소나·유스케이스
- **운영자(현장)**: 지금 설비가 정상인가? 경고는 무엇인가?
- **분석가/데이터과학자(원격)**: 지난달 추세, 이상탐지, 예측.
- **관리자(시스템)**: 주소맵 변경, 장애/복구, 리소스/비용.

핵심 유스케이스
1) CSV에 태그 추가 → 5분 내 카드가 자동 등장.
2) 현장 대시보드로 초단위 상태 확인.
3) 원격에서 장기 추세 분석과 모델 실험.

---

## 4. 요구사항
### 4.1 기능
- CSV 업로드 → 검증(GX/dbt 테스트) → 구성(Telegraf/Node-RED/SQL/대시보드) 자동 생성
- Node-RED: 다양한 프로토콜(Modbus/OPC-UA 등) 폴링
- MQTT 메시지 스키마 고정: `ts, site, line, device, tag, value, unit`
- Telegraf: MQTT 구독 → InfluxDB+Timescale 적재, 파일버퍼로 재시도
- Timescale: 1분/1시간 연속 집계, 보관/압축 정책
- 원격 Pigsty: 논리복제, ML/ETL 실행 공간
- Reflex 뷰어: 카드형(게이지+미니바) 메인, 라인차트+테이블 상세
- 권한 분리: ingest/viewer/rep

### 4.2 비기능
- 가용성: 로컬 단일 노드, 원격 HA(Pigsty 구성요소)로 보완
- 보안: TLS(MQTT), 최소권한 DB 계정, 터널/WireGuard
- 성능: 수집 5k msg/s(엣지 기준) 설계, 쿼리 SLA 위 KPI
- 확장성: CSV 증가 시 수평 확장(브로커/DB 파티션/집계 계층)
- 관측성: 메트릭/로그 대시보드, 알람 룰

---

## 5. 아키텍처
```mermaid
flowchart LR
  subgraph EDGE[Raspberry Pi / Edge]
    A[PLC] --> N[Node-RED
(폴링/정규화)]
    N -->|JSON| M[MQTT / Mosquitto]
    M --> T[Telegraf]
    T --> I[InfluxDB (버퍼)]
    T --> L[TimescaleDB (로컬, 원천)]
  end

  subgraph REMOTE[On-Prem Windows Server (WSL) + Pigsty]
    L == 논리복제 ==> R[TimescaleDB (원격, 영속)]
    R --> G[Grafana/Prometheus]
    R --> ML[MLflow/Feast/Jupyter]
  end

  UI[Vibe Dashboard (Reflex)] --> L
  UI --> R
```
설명
- Edge는 **빠른 수집/확인**. Remote는 **장기 보관/분석/ML**.
- 복제는 Postgres **Logical Replication**. 변경만 전송.

대안(옵션)
- 브로커 진화: NATS JetStream 또는 Redpanda(Kafka API 호환). 추후 스케일에 맞춰 교체 가능.

---

## 6. 데이터 모델
### 6.1 주소맵 CSV 스키마
필수 컬럼
- `site,line,device,tag` : 식별자
- `protocol, conn, unit_id, address, type` : 폴링 정보
- `scale, offset, period_ms, unit, hi, lo` : 변환/주기/임계
검증 규칙
- 복합키 `(site,device,tag,address)` 유일
- `period_ms` ≥ 200
- `type` ∈ {INT16, UINT16, FLOAT32, …}

### 6.2 Timescale 스키마(요지)
```sql
CREATE TABLE plc_raw(
  ts timestamptz NOT NULL,
  site text, line text, device text, tag text,
  unit text,
  value double precision,
  PRIMARY KEY (ts, site, device, tag)
);
SELECT create_hypertable('plc_raw','ts', chunk_time_interval => interval '1 day');

ALTER TABLE plc_raw SET (timescaledb.compress,
  timescaledb.compress_orderby='ts',
  timescaledb.compress_segmentby='site,device,tag');
SELECT add_compression_policy('plc_raw', INTERVAL '7 days');
SELECT add_retention_policy('plc_raw', INTERVAL '90 days');
```

연속 집계
```sql
-- 1m
CREATE MATERIALIZED VIEW plc_1m
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 minute', ts) AS bucket, site, line, device, tag, unit,
       avg(value) AS avg_value, min(value) AS min_value, max(value) AS max_value
FROM plc_raw GROUP BY bucket, site, line, device, tag, unit;

SELECT add_continuous_aggregate_policy('plc_1m',
  start_offset => INTERVAL '7 days',
  end_offset   => INTERVAL '1 minute',
  schedule_interval => INTERVAL '1 minute');

-- 1h (계층 집계)
CREATE MATERIALIZED VIEW plc_1h
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', bucket) AS bucket, site, line, device, tag, unit,
       avg(avg_value) AS avg_value,
       min(min_value) AS min_value,
       max(max_value) AS max_value
FROM plc_1m GROUP BY bucket, site, line, device, tag, unit;
```

---

## 7. 파이프라인 설계
### 7.1 Node-RED
- 부팅 시 CSV 로드 → 전역에 보관.
- 500ms 틱 스케줄러 → 각 행의 `period_ms`에 맞춰 폴링.
- 결과를 타입 변환/스케일/오프셋 적용 후 MQTT 발행.
- 토픽: `plc/{site}/{device}/{tag}`.
- 페이로드(JSON):
```json
{"ts":"2025-08-17T12:00:00Z","site":"A1","line":"L1","device":"PUMP01","tag":"PRESS","value":12.3,"unit":"bar"}
```

### 7.2 Telegraf
- MQTT 구독(qos=1). 파일저널 버퍼 Enable.
- 동시 출력: InfluxDB(버퍼), TimescaleDB(시스템 오브 레코드).
- Starlark Processor로 **deadband/라운딩/중복제거** 수행 가능.

### 7.3 Timescale
- Hypertable 정책: 청크 1일, 압축 7일 이후, 보관 90일.
- 1분/1시간 연속 집계로 질의 비용 절감.
- 인덱스: `(site, device, tag, ts)` 조합.

### 7.4 복제(원격)
- 로컬 `plc_raw` 발행 → 원격 구독.
- 실패 시 재동기화. `copy_data=true` 초기 적재.

---

## 8. 화면 설계 (Vibe 대시보드)
### 8.1 정보 구조
- **메인**: 카드 그리드. 카드=디바이스 단위. 내부에 **게이지 + 미니 막대**.
- **상세**: 상단 라인차트(1m 집계). 우측/하단 표(최근 N행).

### 8.2 상호작용
- 카드 클릭 → `/detail?device=...`
- 범위 선택(24h/7d/30d).
- 태그 필터(멀티 셀렉트).

### 8.3 레이아웃
- 메인: sticky 검색바, `min_child_width=300px` 카드 그리드.
- 카드: hover 확대, 라운드, 그림자. 제목 2줄, 태그 뱃지.
- 상세: 8:4 그리드. 우측 표 스크롤 고정.

### 8.4 성능
- 메인 데이터는 1분 집계만. 첫 페인트 가볍게.
- 상세는 필요 시 원본 혼합. 최대 포인트 3000으로 다운샘플.

### 8.5 접근성
- 키보드 포커스, 대체 텍스트, 대비 확보.

---

## 9. 구성 자동화(생성기)
### 9.1 입력
- `address_map.csv`

### 9.2 산출
- `generated/nodered.flow.json` : 플로우 정의
- `generated/telegraf.toml` : 수집 파이프
- `generated/init.sql` : 테이블/집계/정책
- `generated/dashboard.yaml` : 카드/차트 메타 (옵션)

### 9.3 동작
- CSV→스키마 검증(Great Expectations)→DB 적재(admin.address_map)→Jinja2 템플릿 렌더→산출물 커밋/배포.

---

## 10. 운영/보안/관측
- **보안**: MQTT TLS, 계정 ACL. DB 최소권한(ingest/viewer/rep).
- **백업**: 원격 Pigsty 백업/복구 시나리오. 스냅샷+WAL.
- **관측**: Prometheus/Grafana 대시보드. 수집량, 지연, 실패 카운트, 집계 지연.
- **알람**: 복제 지연, 연속집계 지연, 드롭율, 브로커 큐 적체.

---

## 11. 성능 목표(초기 튜닝)
- Telegraf: `flush_interval=1s`, `metric_batch_size=500`
- Timescale: `shared_buffers` 25% RAM, `timescaledb.parallelize_compression=on`
- 연속집계 정책: 1m 뷰 7일 범위 지속 갱신, 1h 뷰 월 범위.
- 인덱스 재검토: 월 1회.

---

## 12. 실패 모드 & 대응
- 브로커 다운: 파일버퍼로 재전송. 알람 발송.
- DB 장애: 로컬 지속 수집. 원격 복제 재시도.
- CSV 오류: 생성기 테스트 실패 → 배포 중단 → 리포트.

---

## 13. 테스트/검증
- 단위: 주소맵 파서, 타입 변환, deadband.
- 통합: MQTT→Telegraf→DB 적재 E2E.
- 데이터 품질: 단위/범위/누락 테스트(GX, dbt).
- 부하: 5k msg/s 30분 소크테스트.

---

## 14. 배포
- 개발: Docker Compose(모든 구성). `.env`로 분리.
- 운영: Edge(단일 노드), Remote(Pigsty HA). Ansible 플레이북 제공.

---

## 15. 일정(초안)
- W1: 주소맵 스키마/검증, 생성기 스켈레톤
- W2: Edge 파이프라인 완성(Node-RED, MQTT, Telegraf)
- W3: Timescale 스키마/집계/정책 + 복제
- W4: Reflex UI(메인/상세) + 자동 카드
- W5: 관측/알람 + 성능 튜닝
- W6: 문서화/인수

---

## 16. 리스크 & 대응
- PLC 베리언트: 어댑터를 플러그인화.
- 네트워크 불안정: JetStream/파일버퍼/재시도 강화.
- 스키마 변경: 주소맵 버전 필드, 하위호환 유지.

---

## 17. 부록
### 17.1 예시 Telegraf (요지)
```toml
[[inputs.mqtt_consumer]]
  servers = ["tcp://127.0.0.1:1883"]
  topics  = ["plc/+/+/+"]
  qos = 1
  data_format = "json"
  json_time_key = "ts"
  json_time_format = "2006-01-02T15:04:05Z07:00"

[[processors.converter]]
  [processors.converter.tags]
    string = ["site","line","device","tag","unit"]

[[outputs.influxdb_v2]]
  urls = ["http://127.0.0.1:8086"]
  token = "TOKEN"
  organization = "org"
  bucket = "edge"

[[outputs.postgresql]]
  connection = "host=127.0.0.1 user=telegraf password=*** dbname=iot sslmode=disable"
  table = "plc_raw"
```

### 17.2 예시 주소맵 CSV
```csv
site,line,device,tag,protocol,conn,unit_id,address,type,scale,offset,period_ms,unit,hi,lo
A1,LINE1,PUMP01,PRESS,modbus,tcp://192.168.0.10:502,1,40001,FLOAT32,0.1,0,1000,bar,10,0
A1,LINE1,PUMP01,TEMP,modbus,tcp://192.168.0.10:502,1,40021,INT16,1,0,1000,°C,120,-20
```

### 17.3 Reflex 뷰어 쿼리(개요)
- 메인 카드: `SELECT device, max(bucket) as ts, avg_value FROM plc_1m WHERE bucket>=now()-interval '1 hour' GROUP BY device;`
- 상세: `SELECT bucket, tag, avg_value FROM plc_1m WHERE device=$1 AND bucket>=now()-interval '7 days' ORDER BY bucket;`

---

## 참고 링크
- Reflex: https://reflex.dev/
- Mosquitto: https://mosquitto.org/
- Node-RED: https://nodered.org/
- Telegraf: https://www.influxdata.com/time-series-platform/telegraf/
- InfluxDB: https://www.influxdata.com/
- TimescaleDB: https://www.timescale.com/
- Timescale Continuous Aggregates: https://docs.timescale.com/use-timescale/latest/continuous-aggregates/
- PostgreSQL Logical Replication: https://www.postgresql.org/docs/current/logical-replication.html
- Pigsty: https://pigsty.io/docs/pgsql/
- MLflow: https://mlflow.org/
- Feast: https://docs.feast.dev/
- DuckDB: https://duckdb.org/
- Polars: https://pola.rs/
- NATS JetStream: https://docs.nats.io/nats-concepts/jetstream/overview
- Redpanda: https://redpanda.com/
