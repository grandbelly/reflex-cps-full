# 🚀 EcoAnP Dagster 데이터 파이프라인

## 📋 목차
1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [설치 및 설정](#설치-및-설정)
4. [사용법](#사용법)
5. [문제 해결](#문제-해결)
6. [개발 가이드](#개발-가이드)

## 🎯 개요

**EcoAnP Dagster 파이프라인**은 InfluxDB에서 실시간 데이터를 자동으로 수집하여 TimescaleDB에 저장하고, 연속 집계를 통해 고성능 시계열 분석을 제공하는 데이터 파이프라인입니다.

### ✨ 주요 특징
- **🔄 자동화된 데이터 파이프라인**: InfluxDB → TimescaleDB 실시간 동기화
- **📊 자동 스키마 생성**: 태그 매핑 자동 처리
- **⚡ 고성능**: TimescaleDB 하이퍼테이블 + 연속 집계
- **🛡️ 안정성**: 의존성 관리 + 에러 처리 + 재시도
- **📈 모니터링**: 실시간 파이프라인 상태 및 성능 메트릭

## 🏗️ 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   InfluxDB      │    │     Dagster     │    │   TimescaleDB   │
│   (현장 데이터)   │───▶│   (파이프라인)   │───▶│   (분석 DB)     │
│   Port: 8086    │    │   Port: 3000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
   실시간 센서 데이터      자동화 파이프라인 실행      하이퍼테이블 + 연속집계
```

### 🔧 서비스 구성
- **Dagster**: 데이터 파이프라인 오케스트레이션
- **TimescaleDB**: PostgreSQL + TimescaleDB + pg_vector + Python 확장
- **현장 InfluxDB**: 기존 시스템 (별도 관리)

## 🚀 설치 및 설정

### 1단계: Docker 환경 준비
```bash
# TimescaleDB 먼저 시작
cd C:\reflex\reflex-ksys-refactor\db
docker-compose -f docker-compose.timescaledb-only.yml up -d

# Dagster 시작
docker-compose -f docker-compose.dagster.yml up -d
```

### 2단계: 서비스 상태 확인
```bash
# 컨테이너 상태 확인
docker ps --filter "name=ecoanp"

# Dagster 로그 확인
docker logs ecoanp_dagster
docker logs ecoanp_dagster_daemon
```

### 3단계: 웹 인터페이스 접속
- **Dagster**: http://localhost:3000
- **TimescaleDB**: localhost:5432 (ecoanp_user/ecoanp_password)

## 📖 사용법

### 🎯 주요 기능

#### 1. 태그 자동 생성
- InfluxDB 스키마에서 자동으로 태그 생성
- 스케줄: 1시간마다 실행
- 의존성: 스키마 변경 시 자동 실행

#### 2. 데이터 수집 및 변환
- InfluxDB에서 실시간 데이터 수집
- 스케줄: 5분마다 실행
- 데이터 형식 변환 및 검증

#### 3. 연속 집계 생성
- TimescaleDB 연속 집계 자동 생성
- 1분, 5분, 1시간 단위 집계
- 압축 정책 자동 적용

### 🔄 파이프라인 실행

#### 자동 실행
```bash
# Dagster Daemon이 자동으로 스케줄에 따라 실행
# 웹 UI에서 실시간 모니터링 가능
```

#### 수동 실행
```bash
# 특정 Asset 수동 실행
dagster asset materialize --select influx_tags

# 전체 파이프라인 실행
dagster asset materialize --all
```

## 🛠️ 문제 해결

### ❌ 일반적인 문제들

#### 1. Dagster 컨테이너 시작 실패
```bash
# 로그 확인
docker logs ecoanp_dagster

# 포트 충돌 확인
netstat -an | findstr ":3000"

# 컨테이너 재시작
docker-compose -f docker-compose.dagster.yml restart
```

#### 2. TimescaleDB 연결 오류
```bash
# 네트워크 연결 확인
docker network ls
docker network inspect ecoanp_network

# TimescaleDB 상태 확인
docker exec ecoanp_timescaledb pg_isready -U ecoanp_user -d ecoanp
```

#### 3. Asset 실행 실패
```bash
# Asset 로그 확인
# Dagster UI에서 실패한 Asset 클릭하여 상세 로그 확인

# 의존성 확인
dagster asset list --select influx_tags
```

### 🔧 고급 문제 해결

#### 1. 성능 최적화
```python
# Asset 실행 시간 최적화
@asset(
    compute_kind="python",
    group_name="ecoanp",
    retry_policy=RetryPolicy(max_retries=3, delay=60)
)
def influx_data(context: AssetExecutionContext):
    # 최적화된 데이터 처리 로직
    pass
```

#### 2. 리소스 관리
```python
# 리소스 제한 설정
@asset(
    resource_defs={"postgres": postgres_resource},
    config_schema={"batch_size": int}
)
def transform_data(context: AssetExecutionContext):
    # 리소스 기반 데이터 처리
    pass
```

## 👨‍💻 개발 가이드

### 📁 프로젝트 구조
```
dagster/
├── README.md              # 이 파일
├── docker-compose.yml     # Docker 설정
├── assets/                # Asset 정의
│   ├── __init__.py
│   ├── influx_tags.py     # 태그 생성 Asset
│   ├── influx_data.py     # 데이터 수집 Asset
│   └── aggregates.py      # 집계 생성 Asset
├── config/                # 설정 파일
│   ├── dagster.yaml       # Dagster 설정
│   └── workspace.yaml     # 워크스페이스 설정
├── workspace/             # 워크스페이스
└── docs/                  # 문서
    ├── INSTALLATION.md    # 설치 가이드
    ├── USAGE.md           # 사용법
    └── TROUBLESHOOTING.md # 문제 해결
```

### 🔧 개발 환경 설정

#### 1. 로컬 개발
```bash
# Python 가상환경 생성
python -m venv dagster_env
source dagster_env/bin/activate  # Linux/Mac
dagster_env\Scripts\activate     # Windows

# 의존성 설치
pip install dagster dagster-postgres dagster-timescale
```

#### 2. Asset 개발
```python
# assets/influx_tags.py
from dagster import asset, AssetExecutionContext
import psycopg

@asset
def influx_tags(context: AssetExecutionContext):
    """InfluxDB 스키마에서 태그 자동 생성"""
    context.log.info("태그 생성 시작...")
    
    # 태그 생성 로직
    # ...
    
    context.log.info("태그 생성 완료!")
    return {"status": "success", "tags_created": 10}
```

### 📊 모니터링 및 알림

#### 1. 실시간 모니터링
- **Dagster UI**: http://localhost:3000
- **Asset 실행 상태**: 실시간 모니터링
- **성능 메트릭**: 실행 시간, 성공률 등

#### 2. 알림 설정
```python
# Slack 알림 설정
@asset(
    hooks={slack_on_failure_sensor}
)
def critical_data_pipeline(context: AssetExecutionContext):
    # 중요 데이터 파이프라인
    pass
```

## 📚 추가 리소스

### 🔗 공식 문서
- [Dagster Documentation](https://docs.dagster.io/)
- [Dagster Concepts](https://docs.dagster.io/concepts)
- [Dagster Tutorials](https://docs.dagster.io/tutorial)

### 📖 학습 자료
- [Data Pipeline Best Practices](https://docs.dagster.io/concepts/assets/asset-dependencies)
- [Dagster Testing](https://docs.dagster.io/concepts/testing)
- [Dagster Deployment](https://docs.dagster.io/deployment)

### 🆘 지원 및 커뮤니티
- [Dagster Community](https://dagster.io/community)
- [Dagster GitHub](https://github.com/dagster-io/dagster)
- [Dagster Discord](https://discord.gg/dagster)

---

## 🎉 완료!

이제 **EcoAnP Dagster 데이터 파이프라인**이 준비되었습니다!

**다음 단계:**
1. `docker-compose.dagster.yml` 실행
2. Dagster UI 접속 (http://localhost:3000)
3. Asset 배포 및 실행
4. 실시간 모니터링 시작

**문제가 있으면 언제든 말씀해주세요!** 🚀
