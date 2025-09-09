# 🚀 EcoAnP 완전 자동화 Docker 환경 가이드

## 📋 목차
1. [개요](#개요)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [빠른 시작](#빠른-시작)
4. [자동화 플로우](#자동화-플로우)
5. [모니터링 및 관리](#모니터링-및-관리)
6. [문제 해결](#문제-해결)
7. [고급 설정](#고급-설정)

## 🎯 개요

**EcoAnP 완전 자동화 환경**은 InfluxDB에서 실시간 데이터를 자동으로 수집하여 TimescaleDB에 저장하고, 연속 집계를 통해 고성능 시계열 분석을 제공하는 시스템입니다.

### ✨ 주요 특징
- **🔄 완전 자동화**: InfluxDB → TimescaleDB 실시간 동기화
- **📊 자동 스키마 생성**: 태그 매핑 자동 처리
- **⚡ 고성능**: TimescaleDB 하이퍼테이블 + 연속 집계
- **🛡️ 안정성**: Health Check + 자동 재시작
- **📈 모니터링**: 실시간 상태 확인 및 로깅

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   InfluxDB      │    │    Node-RED     │    │   TimescaleDB   │
│   (데이터 소스)  │───▶│   (자동화 엔진)  │───▶│   (분석 DB)     │
│   Port: 8086    │    │   Port: 1880    │    │   Port: 5433    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
   실시간 센서 데이터      자동화 플로우 실행      하이퍼테이블 + 연속집계
```

### 🔧 서비스 구성
- **TimescaleDB**: PostgreSQL + TimescaleDB + pg_vector + Python 확장
- **InfluxDB**: 시계열 데이터 수집 및 저장
- **Node-RED**: 자동화 플로우 실행 및 데이터 변환

## 🚀 빠른 시작

### 1단계: 환경 준비
```powershell
# PowerShell에서 실행
cd C:\reflex\reflex-ksys-refactor\db
.\start-complete-automation.ps1
```

### 2단계: 서비스 상태 확인
```bash
# 컨테이너 상태 확인
docker ps --filter "name=ecoanp"

# 로그 확인
docker logs ecoanp_timescaledb
docker logs ecoanp_influxdb  
docker logs ecoanp_node_red
```

### 3단계: 웹 인터페이스 접속
- **Node-RED**: http://localhost:1880
- **InfluxDB**: http://localhost:8086 (admin/admin)
- **TimescaleDB**: localhost:5433 (postgres/admin)

## 🔄 자동화 플로우

### 📊 태그 자동 생성 플로우
```
시작 → 태그 수 확인 → 스키마 조회 → 태그 생성 → 완료
  ↓         ↓         ↓         ↓         ↓
자동 실행   DB 조회   InfluxDB   SQL 실행   다음 단계
```

### 📈 데이터 수집 플로우
```
데이터 수집 → InfluxDB 조회 → 변환 → TimescaleDB 저장 → 상태 업데이트
    ↓           ↓         ↓      ↓         ↓
  5분마다    최근 1시간   형식변환   INSERT     로그 출력
```

### 🔍 상태 모니터링 플로우
```
상태 확인 → DB 통계 조회 → 결과 출력 → 1분마다 반복
    ↓         ↓         ↓         ↓
  1분마다   태그/데이터 수   콘솔 출력   자동 실행
```

## 📊 모니터링 및 관리

### 🟢 Health Check
```bash
# TimescaleDB 상태 확인
docker exec ecoanp_timescaledb pg_isready -U postgres -d EcoAnP

# InfluxDB 상태 확인
curl -f http://localhost:8086/ping

# Node-RED 상태 확인
curl -f http://localhost:1880/red/health
```

### 📈 성능 모니터링
```sql
-- 연속 집계 상태 확인
SELECT * FROM timescaledb_information.continuous_aggregates;

-- 하이퍼테이블 정보
SELECT * FROM timescaledb_information.hypertables;

-- 작업 상태 확인
SELECT * FROM timescaledb_information.jobs;
```

### 📊 데이터 통계
```sql
-- 태그별 데이터 수
SELECT tag_name, COUNT(*) as record_count 
FROM influx_hist 
GROUP BY tag_name;

-- 최신 데이터 확인
SELECT * FROM influx_latest LIMIT 10;

-- 시간별 집계 확인
SELECT * FROM influx_agg_1h 
WHERE bucket >= NOW() - INTERVAL '24 hours'
ORDER BY bucket DESC;
```

## 🛠️ 문제 해결

### ❌ 일반적인 문제들

#### 1. 컨테이너 시작 실패
```bash
# 로그 확인
docker logs ecoanp_timescaledb
docker logs ecoanp_influxdb
docker logs ecoanp_node_red

# 포트 충돌 확인
netstat -an | findstr "5433\|8086\|1880"

# 컨테이너 재시작
docker-compose -f docker-compose.complete.yml restart
```

#### 2. TimescaleDB 연결 오류
```bash
# 컨테이너 내부 접속
docker exec -it ecoanp_timescaledb psql -U postgres -d EcoAnP

# 확장 확인
\dx timescaledb
\dx pg_vector

# 하이퍼테이블 확인
SELECT * FROM timescaledb_information.hypertables;
```

#### 3. Node-RED 플로우 오류
```bash
# Node-RED 로그 확인
docker logs ecoanp_node_red --tail 100

# 설정 파일 확인
docker exec ecoanp_node_red cat /data/settings.js

# 플로우 파일 확인
docker exec ecoanp_node_red cat /data/flows.json
```

#### 4. 데이터 동기화 문제
```sql
-- InfluxDB 데이터 확인
SELECT * FROM influx_hist ORDER BY ts DESC LIMIT 10;

-- 태그 매핑 확인
SELECT * FROM influx_tag;

-- 연속 집계 상태 확인
SELECT * FROM timescaledb_information.continuous_aggregates;
```

### 🔧 고급 문제 해결

#### 1. 성능 최적화
```sql
-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_influx_hist_ts_tag 
ON influx_hist (ts, tag_name);

-- 통계 업데이트
ANALYZE influx_hist;

-- 압축 정책 조정
SELECT alter_compression_policy('influx_hist', INTERVAL '3 days');
```

#### 2. 백업 및 복구
```bash
# TimescaleDB 백업
docker exec ecoanp_timescaledb pg_dump -U postgres EcoAnP > backup.sql

# InfluxDB 백업
docker exec ecoanp_influxdb influxd backup -database EcoAnP /backups

# 복구
docker exec -i ecoanp_timescaledb psql -U postgres EcoAnP < backup.sql
```

## ⚙️ 고급 설정

### 🔐 보안 강화
```yaml
# docker-compose.complete.yml에 추가
environment:
  POSTGRES_PASSWORD: ${DB_PASSWORD}
  INFLUXDB_ADMIN_PASSWORD: ${INFLUX_PASSWORD}
```

### 📊 모니터링 강화
```yaml
# Prometheus + Grafana 추가
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

### 🚀 성능 튜닝
```sql
-- PostgreSQL 설정 최적화
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';

-- TimescaleDB 설정
ALTER SYSTEM SET timescaledb.max_background_workers = 8;
ALTER SYSTEM SET timescaledb.license = 'apache';
```

## 📚 추가 리소스

### 🔗 공식 문서
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [InfluxDB Documentation](https://docs.influxdata.com/)
- [Node-RED Documentation](https://nodered.org/docs/)

### 📖 학습 자료
- [시계열 데이터베이스 최적화](https://docs.timescale.com/timescaledb/latest/how-to-guides/optimizations/)
- [Node-RED 자동화 패턴](https://nodered.org/docs/user-guide/)
- [Docker 컨테이너 관리](https://docs.docker.com/get-started/)

### 🆘 지원 및 커뮤니티
- [TimescaleDB Community](https://community.timescale.com/)
- [Node-RED Forum](https://discourse.nodered.org/)
- [Docker Community](https://forums.docker.com/)

---

## 🎉 완료!

이제 **EcoAnP 완전 자동화 환경**이 준비되었습니다! 

**다음 단계:**
1. `start-complete-automation.ps1` 실행
2. Node-RED 웹 인터페이스 접속
3. 자동화 플로우 배포 및 실행
4. 실시간 모니터링 시작

**문제가 있으면 언제든 말씀해주세요!** 🚀
