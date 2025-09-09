# Full/Part 버전 분리 아키텍처 설계안

## Executive Summary

reflex-ksys-refactor 프로젝트를 Full 버전(CPS - 엔터프라이즈급)과 Part 버전(ksys - 경량화)으로 분리하는 종합 아키텍처 설계안입니다. 네트워크 성능 이슈를 해결하고 하드웨어 리소스를 최적화하면서 코드 재사용성을 극대화하는 방안을 제시합니다.

## 1. 현재 상태 분석

### 1.1 프로젝트 구조 현황
```
reflex-ksys-refactor/
├── ksys_app/                 # Reflex 메인 애플리케이션
│   ├── ai_engine/            # AI/RAG 엔진 (무거움)
│   ├── components/           # UI 컴포넌트
│   ├── pages/               # 페이지 라우팅
│   ├── states/              # 상태 관리
│   ├── queries/             # DB 쿼리
│   ├── alarm/               # 알람 시스템
│   ├── diagnostics/         # 진단 도구
│   ├── integration/         # 통합 모듈
│   ├── maintenance/         # 유지보수
│   ├── ml/                  # 머신러닝
│   ├── monitoring/          # 모니터링
│   ├── performance/         # 성능 분석
│   └── water_quality/       # 수질 관리
├── dagster/                 # 데이터 파이프라인
├── node-red/               # Node-RED 설정
├── db/                     # 데이터베이스 스크립트
└── docker files            # 컨테이너 설정
```

### 1.2 주요 문제점
- **프로젝트 크기**: 전체 코드베이스가 너무 거대함
- **네트워크 레이턴시**: 윈도우→라즈베리파이 DB 접속 시 성능 저하
- **리소스 사용량**: AI 엔진이 메모리/CPU 과다 사용
- **배포 복잡성**: 단일 이미지로 모든 환경 대응 어려움
- **유지보수성**: 기능별 분리가 안되어 관리 어려움

### 1.3 의존성 분석
- **AI 관련**: sentence-transformers, openai (약 1GB)
- **데이터 분석**: pandas, scipy, matplotlib (약 500MB)
- **머신러닝**: xgboost, lightgbm (약 300MB)
- **기본 Reflex**: reflex, psycopg (약 200MB)

## 2. 분리 전략

### 2.1 아키텍처 원칙
1. **모듈화**: 기능별 명확한 분리
2. **재사용성**: 공통 코드 최대한 공유
3. **확장성**: 향후 기능 추가 용이
4. **성능**: 각 환경에 최적화
5. **유지보수성**: 버전별 독립적 관리

### 2.2 버전별 구성

#### Full 버전 (CPS - Complete Process System)
**배포 위치**: 윈도우 서버
```yaml
Components:
  - Reflex Full UI (모든 메뉴)
  - AI/RAG Engine
  - Dagster Pipeline
  - TimescaleDB (Docker/K3s)
  - Prometheus + Grafana
  - Redis Cache
  
Hardware Requirements:
  - CPU: 4+ cores
  - RAM: 8GB+
  - Storage: 50GB+
```

#### Part 버전 (ksys - Lightweight)
**배포 위치**: 라즈베리파이
```yaml
Components:
  - Reflex Lite UI (핵심 메뉴만)
  - Node-RED
  - TimescaleDB
  - InfluxDB
  - Memory Cache
  
Hardware Requirements:
  - CPU: 2+ cores (ARM64)
  - RAM: 2GB+
  - Storage: 16GB+
```

## 3. 프로젝트 구조 재편성

### 3.1 Monorepo 구조
```
reflex-ksys-unified/
├── shared/                   # 공통 코드
│   ├── components/          # 공통 UI 컴포넌트
│   ├── models/             # 데이터 모델
│   ├── queries/            # DB 쿼리
│   ├── utils/              # 유틸리티
│   └── config/             # 설정 관리
│
├── full/                    # Full 버전 전용
│   ├── ai_engine/          # AI/RAG 엔진
│   ├── ml/                 # 머신러닝
│   ├── dagster/            # 데이터 파이프라인
│   ├── pages/              # Full 전용 페이지
│   └── components/         # Full 전용 컴포넌트
│
├── part/                    # Part 버전 전용
│   ├── node-red/           # Node-RED 설정
│   ├── pages/              # Part 전용 페이지
│   └── components/         # Part 전용 컴포넌트
│
├── docker/                  # Docker 설정
│   ├── full/               
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   └── part/
│       ├── Dockerfile
│       └── docker-compose.yml
│
├── scripts/                 # 빌드/배포 스크립트
├── docs/                    # 문서
└── tests/                   # 테스트
```

### 3.2 환경 변수 설정
```env
# 공통 설정
APP_VERSION=FULL|PART
APP_ENV=development|production
TZ=Asia/Seoul

# 데이터베이스
TS_DSN=postgresql://...
INFLUX_URL=http://...

# Full 버전 전용
ENABLE_AI=true
ENABLE_ML=true
ENABLE_DAGSTER=true
OPENAI_API_KEY=...
REDIS_URL=redis://...

# Part 버전 전용
ENABLE_NODERED=true
MEMORY_LIMIT=512M
```

## 4. 코드 재사용 전략

### 4.1 Feature Flags 패턴
```python
# shared/config/features.py
import os

class Features:
    IS_FULL_VERSION = os.getenv('APP_VERSION') == 'FULL'
    
    # AI 기능
    AI_INSIGHTS = IS_FULL_VERSION
    AI_CHAT = IS_FULL_VERSION
    
    # 데이터 파이프라인
    DAGSTER_PIPELINE = IS_FULL_VERSION
    NODE_RED = not IS_FULL_VERSION
    
    # UI 메뉴
    SHOW_AI_MENU = IS_FULL_VERSION
    SHOW_ML_MENU = IS_FULL_VERSION
    SHOW_ADVANCED_ANALYTICS = IS_FULL_VERSION
```

### 4.2 의존성 주입
```python
# shared/services/base.py
from abc import ABC, abstractmethod

class DataService(ABC):
    @abstractmethod
    async def get_metrics(self): pass

# full/services/ai_data_service.py
class AIDataService(DataService):
    async def get_metrics(self):
        # AI 기반 메트릭 분석
        pass

# part/services/simple_data_service.py
class SimpleDataService(DataService):
    async def get_metrics(self):
        # 기본 메트릭 조회
        pass
```

### 4.3 동적 임포트
```python
# ksys_app.py
from shared.config.features import Features

def create_app():
    if Features.AI_INSIGHTS:
        from full.pages.ai_insights import ai_insights_page
        app.add_page(ai_insights_page)
    
    if Features.NODE_RED:
        from part.pages.nodered_dashboard import nodered_page
        app.add_page(nodered_page)
```

## 5. Docker 최적화

### 5.1 Multi-stage Build (Full 버전)
```dockerfile
# docker/full/Dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
WORKDIR /build
COPY requirements-full.txt .
RUN pip install --user -r requirements-full.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app

# 시스템 패키지
RUN apt-get update && apt-get install -y \
    curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지
COPY --from=builder /root/.local /root/.local

# 애플리케이션 코드
COPY shared/ ./shared/
COPY full/ ./full/
COPY ksys_app.py rxconfig.py ./

ENV PATH=/root/.local/bin:$PATH
ENV APP_VERSION=FULL

EXPOSE 13000 13001
CMD ["reflex", "run", "--env", "prod"]
```

### 5.2 경량화 Build (Part 버전)
```dockerfile
# docker/part/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 최소 시스템 패키지
RUN apt-get update && apt-get install -y \
    curl nodejs \
    && rm -rf /var/lib/apt/lists/*

# 경량 의존성
COPY requirements-part.txt .
RUN pip install --no-cache-dir -r requirements-part.txt

# 애플리케이션 코드
COPY shared/ ./shared/
COPY part/ ./part/
COPY ksys_app.py rxconfig.py ./

ENV APP_VERSION=PART
ENV PYTHONOPTIMIZE=1

EXPOSE 13000 13001
CMD ["reflex", "run", "--env", "prod", "--backend-only"]
```

### 5.3 ARM64 지원 (라즈베리파이)
```yaml
# docker/part/docker-compose.yml
version: '3.8'

services:
  reflex-part:
    build:
      context: ../..
      dockerfile: docker/part/Dockerfile
      platforms:
        - linux/arm64
        - linux/amd64
    image: reflex-ksys:part-${VERSION:-latest}
    container_name: reflex-ksys-part
    environment:
      - APP_VERSION=PART
      - TS_DSN=${TS_DSN}
    ports:
      - "13000:13000"
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.5'
```

## 6. 네트워크 성능 최적화

### 6.1 캐싱 전략

#### Full 버전 - Redis 캐싱
```python
# full/cache/redis_cache.py
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def redis_cache(ttl=60):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

#### Part 버전 - 메모리 캐싱
```python
# part/cache/memory_cache.py
from cachetools import TTLCache
from functools import wraps

cache = TTLCache(maxsize=100, ttl=60)

def memory_cache(ttl=60):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            if cache_key in cache:
                return cache[cache_key]
            
            result = await func(*args, **kwargs)
            cache[cache_key] = result
            return result
        return wrapper
    return decorator
```

### 6.2 데이터베이스 연결 최적화
```python
# shared/db/connection_pool.py
import psycopg_pool
from contextlib import asynccontextmanager

class DatabasePool:
    def __init__(self, dsn, min_size=2, max_size=10):
        self.pool = psycopg_pool.AsyncConnectionPool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            max_idle=300,
            max_lifetime=3600
        )
    
    @asynccontextmanager
    async def connection(self):
        async with self.pool.connection() as conn:
            yield conn

# Full 버전: 더 많은 연결
full_db = DatabasePool(dsn, min_size=5, max_size=20)

# Part 버전: 제한된 연결
part_db = DatabasePool(dsn, min_size=2, max_size=5)
```

### 6.3 성능 모니터링

#### Full 버전 - Prometheus 메트릭
```python
# full/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

query_duration = Histogram('db_query_duration_seconds', 'Database query duration')
active_connections = Gauge('db_active_connections', 'Active database connections')
cache_hits = Counter('cache_hits_total', 'Total cache hits')

@query_duration.time()
async def monitored_query(query):
    # 쿼리 실행
    pass
```

#### Part 버전 - 간단한 로깅
```python
# part/monitoring/simple_metrics.py
import logging
import time

logger = logging.getLogger(__name__)

async def timed_query(query):
    start = time.time()
    try:
        result = await execute_query(query)
        duration = time.time() - start
        if duration > 1:
            logger.warning(f"Slow query: {duration:.2f}s - {query[:50]}")
        return result
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise
```

## 7. UI 메뉴 분리

### 7.1 Full 버전 메뉴 구조
```python
# full/config/menu.py
FULL_MENU = [
    {"name": "Dashboard", "path": "/", "icon": "dashboard"},
    {"name": "Trend Analysis", "path": "/trend", "icon": "chart"},
    {"name": "AI Insights", "path": "/ai", "icon": "brain"},
    {"name": "ML Predictions", "path": "/ml", "icon": "predict"},
    {"name": "Water Quality", "path": "/water", "icon": "water"},
    {"name": "Performance", "path": "/performance", "icon": "speed"},
    {"name": "Diagnostics", "path": "/diagnostics", "icon": "health"},
    {"name": "Maintenance", "path": "/maintenance", "icon": "wrench"},
    {"name": "Integration", "path": "/integration", "icon": "link"},
    {"name": "Settings", "path": "/settings", "icon": "settings"}
]
```

### 7.2 Part 버전 메뉴 구조
```python
# part/config/menu.py
PART_MENU = [
    {"name": "Dashboard", "path": "/", "icon": "dashboard"},
    {"name": "Trend", "path": "/trend", "icon": "chart"},
    {"name": "Alarms", "path": "/alarms", "icon": "bell"},
    {"name": "Node-RED", "path": "/nodered", "icon": "flow"},
    {"name": "Settings", "path": "/settings", "icon": "settings"}
]
```

## 8. 배포 전략

### 8.1 CI/CD 파이프라인
```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build-full:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Full Version
        run: |
          docker buildx build \
            --platform linux/amd64 \
            --tag ghcr.io/${{ github.repository }}/full:${{ github.ref_name }} \
            --file docker/full/Dockerfile \
            --push .

  build-part:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Part Version
        run: |
          docker buildx build \
            --platform linux/arm64,linux/amd64 \
            --tag ghcr.io/${{ github.repository }}/part:${{ github.ref_name }} \
            --file docker/part/Dockerfile \
            --push .
```

### 8.2 배포 스크립트

#### Full 버전 배포 (윈도우)
```powershell
# scripts/deploy-full.ps1
$VERSION = "latest"
$COMPOSE_FILE = "docker/full/docker-compose.yml"

# 환경 변수 설정
$env:APP_VERSION = "FULL"
$env:VERSION = $VERSION

# 이미지 풀 및 실행
docker-compose -f $COMPOSE_FILE pull
docker-compose -f $COMPOSE_FILE up -d

# 헬스체크
Start-Sleep -Seconds 10
Invoke-WebRequest -Uri "http://localhost:13000/health" -UseBasicParsing
```

#### Part 버전 배포 (라즈베리파이)
```bash
#!/bin/bash
# scripts/deploy-part.sh

VERSION="latest"
COMPOSE_FILE="docker/part/docker-compose.yml"

# 환경 변수 설정
export APP_VERSION="PART"
export VERSION=$VERSION

# 메모리 최적화
sudo sysctl -w vm.swappiness=10
sudo sysctl -w vm.vfs_cache_pressure=50

# 이미지 풀 및 실행
docker-compose -f $COMPOSE_FILE pull
docker-compose -f $COMPOSE_FILE up -d

# 헬스체크
sleep 10
curl -f http://localhost:13000/health || exit 1
```

## 9. 마이그레이션 계획

### 9.1 단계별 마이그레이션
```
Phase 1 (Week 1-2): 프로젝트 구조 재편성
- [ ] Monorepo 구조로 전환
- [ ] shared/full/part 디렉토리 생성
- [ ] 공통 코드 추출 및 이동

Phase 2 (Week 3-4): Docker 설정
- [ ] Multi-stage Dockerfile 작성
- [ ] docker-compose 파일 분리
- [ ] ARM64 빌드 테스트

Phase 3 (Week 5-6): 기능 분리
- [ ] Feature flags 구현
- [ ] 메뉴 시스템 분리
- [ ] AI 엔진 조건부 로드

Phase 4 (Week 7-8): 테스트 및 최적화
- [ ] 성능 테스트
- [ ] 메모리 사용량 측정
- [ ] 네트워크 레이턴시 개선

Phase 5 (Week 9-10): 배포
- [ ] CI/CD 파이프라인 구축
- [ ] 문서화
- [ ] 프로덕션 배포
```

### 9.2 호환성 유지
```python
# shared/compat/version_check.py
import os
import sys

def check_version_compatibility():
    version = os.getenv('APP_VERSION', 'FULL')
    
    if version == 'PART':
        # Part 버전에서 사용할 수 없는 모듈 체크
        forbidden_modules = ['ai_engine', 'ml', 'dagster']
        for module in forbidden_modules:
            if module in sys.modules:
                raise ImportError(f"{module} is not available in PART version")
    
    return version
```

## 10. 성능 목표 및 메트릭

### 10.1 Full 버전 성능 목표
```yaml
Performance Targets:
  - Startup Time: < 30s
  - Memory Usage: < 4GB
  - CPU Usage (Idle): < 20%
  - Query Response: < 500ms (avg)
  - AI Response: < 3s
  - Docker Image Size: < 2GB
```

### 10.2 Part 버전 성능 목표
```yaml
Performance Targets:
  - Startup Time: < 15s
  - Memory Usage: < 512MB
  - CPU Usage (Idle): < 10%
  - Query Response: < 300ms (avg)
  - Docker Image Size: < 500MB
  - Raspberry Pi 4 Compatible
```

### 10.3 모니터링 대시보드
```python
# shared/monitoring/dashboard.py
class PerformanceMonitor:
    def __init__(self, version):
        self.version = version
        self.metrics = {
            'startup_time': None,
            'memory_usage': None,
            'cpu_usage': None,
            'query_times': [],
            'error_count': 0
        }
    
    def collect_metrics(self):
        import psutil
        process = psutil.Process()
        
        self.metrics['memory_usage'] = process.memory_info().rss / 1024 / 1024  # MB
        self.metrics['cpu_usage'] = process.cpu_percent()
        
        return self.metrics
    
    def export_metrics(self):
        if self.version == 'FULL':
            # Prometheus 형식으로 export
            return self.export_prometheus()
        else:
            # JSON 형식으로 export
            return self.export_json()
```

## 11. 보안 고려사항

### 11.1 버전별 보안 설정
```python
# shared/security/config.py
class SecurityConfig:
    def __init__(self, version):
        self.version = version
        
        if version == 'FULL':
            self.enable_api_auth = True
            self.enable_ssl = True
            self.enable_audit_log = True
            self.max_connections = 100
        else:
            self.enable_api_auth = True
            self.enable_ssl = False  # 내부 네트워크
            self.enable_audit_log = False
            self.max_connections = 20
```

### 11.2 환경변수 암호화
```python
# shared/utils/secrets.py
from cryptography.fernet import Fernet
import os

class SecretManager:
    def __init__(self):
        key = os.getenv('ENCRYPTION_KEY')
        self.cipher = Fernet(key) if key else None
    
    def encrypt_env(self, value):
        if self.cipher:
            return self.cipher.encrypt(value.encode()).decode()
        return value
    
    def decrypt_env(self, encrypted_value):
        if self.cipher:
            return self.cipher.decrypt(encrypted_value.encode()).decode()
        return encrypted_value
```

## 12. 문서화 및 가이드

### 12.1 개발자 가이드
```markdown
# Developer Guide

## 로컬 개발 환경 설정

### Full 버전 개발
1. 환경변수 설정: `cp .env.full.example .env`
2. 의존성 설치: `pip install -r requirements-full.txt`
3. 실행: `APP_VERSION=FULL reflex run`

### Part 버전 개발
1. 환경변수 설정: `cp .env.part.example .env`
2. 의존성 설치: `pip install -r requirements-part.txt`
3. 실행: `APP_VERSION=PART reflex run`

## 코드 컨벤션
- 공통 코드는 shared/ 디렉토리에
- 버전별 코드는 full/ 또는 part/ 디렉토리에
- Feature flags 사용하여 조건부 기능 구현
```

### 12.2 운영 가이드
```markdown
# Operations Guide

## Full 버전 운영 (윈도우)
- 최소 사양: 4 Core CPU, 8GB RAM
- Docker Desktop 필수
- 포트: 13000(Frontend), 13001(Backend), 3000(Grafana)

## Part 버전 운영 (라즈베리파이)
- 최소 사양: Raspberry Pi 4 (2GB+)
- Docker 설치 필요
- 스왑 메모리 설정 권장
- 포트: 13000(Frontend), 1880(Node-RED)

## 백업 및 복구
- 데이터베이스: pg_dump 일일 백업
- 설정 파일: Git 저장소 관리
- Docker 볼륨: 주기적 스냅샷
```

## 13. 예상 결과 및 이점

### 13.1 성능 개선
- **네트워크**: 로컬 실행으로 레이턴시 90% 감소
- **메모리**: Part 버전 75% 절감 (2GB → 512MB)
- **시작 시간**: 50% 단축
- **이미지 크기**: Part 버전 75% 감소

### 13.2 관리 이점
- **유지보수**: 버전별 독립 관리 가능
- **배포**: 환경별 최적화된 배포
- **확장성**: 기능 추가/제거 용이
- **비용**: 하드웨어 요구사항 감소

### 13.3 개발 효율성
- **코드 재사용**: 70% 이상 공통 코드 공유
- **테스트**: 버전별 독립 테스트
- **디버깅**: 간소화된 스택으로 문제 해결 용이

## 14. 리스크 및 대응 방안

### 14.1 기술적 리스크
| 리스크 | 영향도 | 대응 방안 |
|--------|--------|-----------|
| ARM64 호환성 | 높음 | 사전 테스트 및 대체 패키지 준비 |
| 네트워크 분리 | 중간 | VPN 또는 터널링 솔루션 |
| 버전 간 데이터 동기화 | 높음 | 실시간 복제 또는 CDC 구현 |
| 성능 저하 | 중간 | 캐싱 강화 및 쿼리 최적화 |

### 14.2 운영 리스크
| 리스크 | 영향도 | 대응 방안 |
|--------|--------|-----------|
| 버전 관리 복잡성 | 중간 | 자동화된 CI/CD 파이프라인 |
| 문서화 부족 | 낮음 | 지속적인 문서 업데이트 |
| 교육 필요성 | 중간 | 운영자 교육 프로그램 |

## 15. 결론 및 다음 단계

### 15.1 핵심 권장사항
1. **Monorepo 구조 채택**: 코드 재사용성 극대화
2. **Feature Flags 패턴**: 런타임 기능 제어
3. **Multi-stage Docker 빌드**: 이미지 크기 최적화
4. **환경별 캐싱 전략**: 성능 최적화
5. **자동화된 배포**: CI/CD 파이프라인 구축

### 15.2 즉시 실행 가능한 작업
1. 프로젝트 구조 재편성 시작
2. requirements-full.txt와 requirements-part.txt 분리
3. Docker 멀티스테이지 빌드 파일 작성
4. Feature flags 시스템 구현
5. 기본 성능 메트릭 수집 시작

### 15.3 장기 로드맵
- **Q1 2025**: 구조 재편성 및 기초 작업
- **Q2 2025**: Full/Part 버전 분리 완료
- **Q3 2025**: 성능 최적화 및 안정화
- **Q4 2025**: 프로덕션 배포 및 운영

## Appendix A: 의존성 분리

### requirements-full.txt
```
# Core
reflex==0.8.9
psycopg[binary,pool]>=3.1
pydantic>=2.6
cachetools>=5

# AI/ML
sentence-transformers==2.2.2
openai>=1.35.0
numpy==1.24.3
scikit-learn==1.3.0
pandas>=2.0.0
scipy>=1.10.0
xgboost>=1.7.0
lightgbm>=3.3.0

# Monitoring
prometheus-client>=0.19.0
redis>=5.0.0

# Dagster
dagster>=1.5.0
dagster-webserver>=1.5.0
```

### requirements-part.txt
```
# Core
reflex==0.8.9
psycopg[binary,pool]>=3.1
pydantic>=2.6
cachetools>=5

# Lightweight components only
watchdog>=3.0.0
cryptography>=41.0.0
```

## Appendix B: 환경 변수 템플릿

### .env.full.example
```env
# App Configuration
APP_VERSION=FULL
APP_ENV=production
TZ=Asia/Seoul

# Database
TS_DSN=postgresql://user:pass@localhost:5432/dbname
INFLUX_URL=http://localhost:8086

# AI Services
OPENAI_API_KEY=sk-...
ENABLE_AI=true
ENABLE_ML=true

# Cache
REDIS_URL=redis://localhost:6379

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Dagster
DAGSTER_HOME=/opt/dagster
ENABLE_DAGSTER=true
```

### .env.part.example
```env
# App Configuration
APP_VERSION=PART
APP_ENV=production
TZ=Asia/Seoul

# Database
TS_DSN=postgresql://user:pass@localhost:5432/dbname
INFLUX_URL=http://localhost:8086

# Node-RED
ENABLE_NODERED=true
NODERED_PORT=1880

# Resource Limits
MEMORY_LIMIT=512M
CPU_LIMIT=1.5

# Cache
CACHE_TYPE=memory
CACHE_TTL=60
```

---

*이 문서는 reflex-ksys-refactor 프로젝트의 Full/Part 버전 분리를 위한 종합 아키텍처 설계안입니다.*
*작성일: 2025-09-09*
*버전: 1.0*