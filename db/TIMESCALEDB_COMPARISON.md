# 📊 TimescaleDB 리모트 vs 로컬 상세 기능 비교

> 작성일: 2025-09-05  
> 목적: 리모트(192.168.1.80)와 로컬 Docker TimescaleDB 환경 간 기능 비교 및 마이그레이션 체크리스트

## 🔍 개요

### 환경 정보
| 구분 | 리모트 DB | 로컬 DB |
|------|----------|---------|
| **주소** | 192.168.1.80:5432 | localhost:5433 |
| **데이터베이스명** | EcoAnP | ecoanp |
| **사용자** | postgres | ecoanp_user |
| **PostgreSQL 버전** | 16.x | 16.10 |
| **TimescaleDB 버전** | 2.x | 2.22.0 |
| **컨테이너** | 별도 서버 | Docker (ecoanp_timescaledb) |
| **데이터 소스** | InfluxDB 직접 | InfluxDB → Dagster ETL |

## 📋 핵심 기능 비교표

### 1. 기본 구조 (Core Structure)

| 기능 | 리모트 | 로컬 | 상태 | 비고 |
|------|--------|------|------|------|
| **Hypertable** |||||
| influx_hist | ✅ | ✅ | ✅ 동기화 | 시계열 데이터 저장 |
| 압축 정책 | ✅ 7일 | ❌ | ⚠️ 미구현 | 로컬에 압축 정책 필요 |
| 보존 정책 | ✅ 365일 | ✅ 365일 | ✅ 동일 | Job ID: 1000 |
| **청크 설정** |||||
| 청크 간격 | 7일 | 7일 | ✅ 동일 | 자동 설정 |
| 청크 개수 | 다수 | 1개 | ⚠️ 차이 | 로컬은 데이터 적음 |

### 2. 테이블 구조 (Tables)

| 테이블명 | 리모트 | 로컬 | 동기화 | 용도 |
|---------|--------|------|--------|------|
| **핵심 데이터** |||||
| influx_hist | ✅ | ✅ | ✅ | 시계열 원본 데이터 |
| influx_tag | ✅ | ✅ | ✅ | 태그 매핑 (D100-D302) |
| influx_qc_rule | ✅ | ✅ | ✅ | QC 규칙 및 임계값 |
| influx_op_log | ✅ | ✅ | ✅ | 운영 로그 |
| **AI/분석** |||||
| ai_conversations | ❌ | ✅ | 🆕 신규 | AI 대화 내역 |
| ai_knowledge_base | ❌ | ✅ | 🆕 신규 | AI 지식 베이스 |
| predictions | ❌ | ✅ | 🆕 신규 | 예측 데이터 |
| anomalies | ❌ | ✅ | 🆕 신규 | 이상치 감지 |
| **예측 모델** |||||
| pred_linreg_h5_w60 | ❌ | ✅ | 🆕 신규 | 5시간 예측 (60분 윈도우) |
| pred_linreg_h15_w120 | ❌ | ✅ | 🆕 신규 | 15시간 예측 (120분 윈도우) |

### 3. 뷰와 집계 (Views & Aggregations)

| 뷰명 | 리모트 | 로컬 | 타입 | 상태 |
|------|--------|------|------|------|
| **실시간 뷰** |||||
| influx_latest | ✅ | ✅ | View | ✅ 정상 |
| system_stats | ❌ | ✅ | View | 🆕 신규 |
| **연속 집계** |||||
| influx_agg_1m | ✅ | ✅ | Continuous Aggregate | ✅ 정상 |
| influx_agg_10m | ✅ | ❌ | Continuous Aggregate | ❌ 미구현 |
| influx_agg_1h | ✅ | ❌ | Continuous Aggregate | ❌ 미구현 |
| influx_agg_1d | ✅ | ✅ | View (로컬은 일반 뷰) | ⚠️ 타입 차이 |
| **기술 지표** |||||
| tech_ind_1m_mv | ✅ | ❌ | Materialized View | ❌ 미구현 |
| tech_ind_1h_mv | ✅ | ❌ | Materialized View | ❌ 미구현 |
| tech_ind_1d_mv | ✅ | ✅ | Materialized View | ✅ 정상 |
| **통계 뷰** |||||
| features_5m | ✅ | ❌ | View | ❌ 미구현 |
| features_1h | ✅ | ❌ | View | ❌ 미구현 |

### 4. 자동화 작업 (Background Jobs)

| 작업 | 리모트 | 로컬 | 실행 주기 | 상태 |
|------|--------|------|-----------|------|
| **데이터 수집** |||||
| InfluxDB 수집 | Node-RED | Dagster | 10초 | ✅ 전환 완료 |
| 메타데이터 동기화 | Node-RED | Dagster | 1일 | ✅ 전환 완료 |
| **TimescaleDB Jobs** |||||
| 연속 집계 새로고침 (1m) | ✅ | ✅ | 1분 | ✅ Job: 1001 |
| 연속 집계 새로고침 (10m) | ✅ | ❌ | 10분 | ❌ 미구현 |
| 연속 집계 새로고침 (1h) | ✅ | ❌ | 1시간 | ❌ 미구현 |
| 데이터 압축 | ✅ | ❌ | 1일 | ❌ 미구현 |
| 데이터 보존 정책 | ✅ | ✅ | 1일 | ✅ Job: 1000 |
| Telemetry Reporter | ✅ | ✅ | 24시간 | ✅ Job: 1 |
| Job History 정리 | ✅ | ✅ | 1개월 | ✅ Job: 3 |

### 5. 인덱스 구성 (Indexes)

| 인덱스 | 리모트 | 로컬 | 용도 |
|--------|--------|------|------|
| **influx_hist** |||||
| influx_hist_pkey | ✅ | ✅ | Primary Key (ts, tag_name) |
| idx_influx_hist_time | ✅ | ✅ | 시간 기반 조회 |
| idx_influx_hist_tag_time | ✅ | ✅ | 태그+시간 조회 |
| influx_hist_ts_idx | ✅ | ✅ | TimescaleDB 자동 생성 |
| **influx_tag** |||||
| influx_tag_pkey | ✅ | ✅ | Primary Key |
| uq_influx_tag_id | ✅ | ✅ | Unique (tag_id) |
| uq_influx_tag_name | ✅ | ✅ | Unique (tag_name) |
| **influx_qc_rule** |||||
| influx_qc_rule_pkey | ✅ | ✅ | Primary Key |

### 6. 확장 기능 (Extensions)

| Extension | 리모트 | 로컬 | 버전 | 용도 |
|-----------|--------|------|------|------|
| timescaledb | ✅ | ✅ | 2.22.0 | 시계열 DB |
| pg_vector | ✅ | ❌ | - | 벡터 검색 (AI) |
| plpython3u | ✅ | ✅ | 1.0 | Python 함수 |
| pg_stat_statements | ✅ | ❌ | - | 쿼리 성능 모니터링 |
| hstore | ✅ | ❌ | - | Key-Value 저장 |
| ltree | ✅ | ❌ | - | 계층 구조 데이터 |

## 🔄 데이터 플로우 비교

### 리모트 (기존)
```
InfluxDB → Node-RED → TimescaleDB → Reflex App
         ↓
    (10초 주기)
```

### 로컬 (신규)
```
InfluxDB → Dagster → TimescaleDB → Reflex App
         ↓
    (10초 주기)
    
추가 기능:
- AI 대화 저장
- 예측 모델
- 이상치 감지
```

## ⚠️ 마이그레이션 체크리스트

### 🔴 필수 구현 사항
- [ ] **연속 집계 추가**
  - [ ] influx_agg_10m 생성
  - [ ] influx_agg_1h 생성
  - [ ] 자동 새로고침 정책 설정
- [ ] **압축 정책 설정**
  - [ ] 7일 이상 데이터 압축
  - [ ] 압축 작업 스케줄 설정
- [ ] **기술 지표 뷰**
  - [ ] tech_ind_1m_mv 생성
  - [ ] tech_ind_1h_mv 생성
- [ ] **통계 뷰**
  - [ ] features_5m 생성
  - [ ] features_1h 생성

### 🟡 권장 구현 사항
- [ ] **확장 기능**
  - [ ] pg_vector 설치 (AI 기능용)
  - [ ] pg_stat_statements 설치 (성능 모니터링)
- [ ] **성능 최적화**
  - [ ] 청크 크기 최적화
  - [ ] 추가 인덱스 생성
- [ ] **모니터링**
  - [ ] Grafana 대시보드 구성
  - [ ] 알림 설정

### 🟢 완료된 사항
- [x] Hypertable 생성 (influx_hist)
- [x] 기본 테이블 구조
- [x] 1분 연속 집계
- [x] 일별 집계 뷰
- [x] Dagster ETL 파이프라인
- [x] 10초 데이터 수집 센서
- [x] 보존 정책 (365일)

## 📊 데이터 현황

### 로컬 DB 통계 (2025-09-05 기준)
- **총 레코드**: 3,180개
- **태그 수**: 11개 (D100-D302 + 2개 추가)
- **데이터 범위**: 최근 24시간
- **DB 크기**: 48 MB
- **청크 수**: 1개
- **수집 주기**: 10초 (정상 작동)

## 🚀 추천 작업 우선순위

1. **단기 (1주일 내)**
   - influx_agg_10m, influx_agg_1h 연속 집계 생성
   - 압축 정책 설정
   - pg_vector 확장 설치

2. **중기 (2-4주)**
   - 기술 지표 뷰 구현
   - 통계 뷰 구현
   - 성능 모니터링 설정

3. **장기 (1-2개월)**
   - AI 기능 고도화
   - 예측 모델 개선
   - 완전 자동화 파이프라인

## 📝 참고사항

- 로컬 환경은 Docker 기반으로 구성되어 있어 확장성과 이식성이 우수
- Dagster를 통한 ETL은 Node-RED보다 더 안정적이고 모니터링이 용이
- AI 관련 테이블이 추가되어 향후 고급 분석 기능 구현 가능
- 로컬 DB는 개발/테스트 환경으로 최적화되어 있음

---

**문서 버전**: 1.0.0  
**최종 수정**: 2025-09-05  
**작성자**: Claude Code Assistant