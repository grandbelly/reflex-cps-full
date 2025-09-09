# 📥 Dagster 설치 및 설정 가이드

## 📋 목차
1. [사전 요구사항](#사전-요구사항)
2. [Docker 설치](#docker-설치)
3. [Dagster 컨테이너 설정](#dagster-컨테이너-설정)
4. [초기 설정](#초기-설정)
5. [검증 및 테스트](#검증-및-테스트)

## 🔍 사전 요구사항

### 필수 소프트웨어
- **Docker Desktop**: 4.0.0 이상
- **Docker Compose**: 2.0.0 이상
- **Windows**: 10/11 (WSL2 권장)
- **메모리**: 최소 8GB (16GB 권장)
- **디스크**: 최소 10GB 여유 공간

### 시스템 요구사항
```bash
# Docker 버전 확인
docker --version
docker-compose --version

# 시스템 리소스 확인
docker system df
docker stats
```

## 🐳 Docker 설치

### 1. Docker Desktop 설치
```bash
# 공식 사이트에서 다운로드
# https://www.docker.com/products/docker-desktop/

# 설치 후 재부팅
# WSL2 백엔드 활성화 (권장)
```

### 2. Docker 설정 확인
```bash
# Docker 실행 상태 확인
docker ps

# 네트워크 확인
docker network ls

# 볼륨 확인
docker volume ls
```

## 🚀 Dagster 컨테이너 설정

### 1단계: 프로젝트 디렉토리 생성
```bash
# 프로젝트 루트로 이동
cd C:\reflex\reflex-ksys-refactor\db

# Dagster 디렉토리 구조 생성
mkdir dagster
cd dagster
mkdir assets config workspace docs
```

### 2단계: Docker Compose 파일 생성
```yaml
# docker-compose.dagster.yml
version: '3.8'

services:
  dagster:
    image: dagster/dagster:latest
    container_name: ecoanp_dagster
    restart: unless-stopped
    environment:
      - DAGSTER_HOME=/opt/dagster/dagster_home
      - DAGSTER_WEBSERVER_HOST=0.0.0.0
      - DAGSTER_WEBSERVER_PORT=3000
    volumes:
      - ./dagster:/opt/dagster/app
      - ./dagster/dagster_home:/opt/dagster/dagster_home
      - ./dagster/workspace:/opt/dagster/workspace
    ports:
      - "3000:3000"
    networks:
      - dagster_network
      - ecoanp_network
    depends_on:
      - timescaledb
```

### 3단계: TimescaleDB 네트워크 연결
```bash
# TimescaleDB 먼저 시작
docker-compose -f docker-compose.timescaledb-only.yml up -d

# 네트워크 확인
docker network ls | grep ecoanp
```

### 4단계: Dagster 컨테이너 시작
```bash
# Dagster 시작
docker-compose -f docker-compose.dagster.yml up -d

# 상태 확인
docker ps --filter "name=dagster"
```

## ⚙️ 초기 설정

### 1단계: Dagster 설정 파일 생성
```yaml
# dagster/config/dagster.yaml
run_coordinator:
  module: dagster.core.run_coordinator
  class: QueuedRunCoordinator
  config:
    max_concurrent_runs: 10

scheduler:
  module: dagster.core.scheduler
  class: DagsterDaemonScheduler

run_launcher:
  module: dagster.core.launcher
  class: DefaultRunLauncher
```

### 2단계: 워크스페이스 설정
```yaml
# dagster/config/workspace.yaml
load_from:
  - python_file:
      relative_path: assets/__init__.py
      working_directory: .
```

### 3단계: Asset 초기화
```python
# dagster/assets/__init__.py
from dagster import Definitions
from .influx_tags import influx_tags
from .influx_data import influx_data

defs = Definitions(
    assets=[influx_tags, influx_data],
    resources={},
)
```

## ✅ 검증 및 테스트

### 1단계: 컨테이너 상태 확인
```bash
# 모든 컨테이너 상태
docker ps --filter "name=ecoanp"

# Dagster 로그 확인
docker logs ecoanp_dagster
docker logs ecoanp_dagster_daemon
```

### 2단계: 웹 인터페이스 접속
```bash
# 브라우저에서 접속
# http://localhost:3000

# 기본 페이지가 로드되는지 확인
# Dagster 로고와 메뉴가 보이는지 확인
```

### 3단계: Asset 로드 확인
```bash
# Asset 목록 확인
# Dagster UI에서 Assets 탭 클릭
# influx_tags, influx_data Asset이 보이는지 확인
```

### 4단계: 연결 테스트
```bash
# TimescaleDB 연결 테스트
docker exec ecoanp_dagster python -c "
import psycopg
conn = psycopg.connect('postgresql://ecoanp_user:ecoanp_password@timescaledb:5432/ecoanp')
print('TimescaleDB 연결 성공!')
conn.close()
"
```

## 🚨 문제 해결

### 일반적인 설치 문제

#### 1. 포트 충돌
```bash
# 포트 3000 사용 확인
netstat -an | findstr ":3000"

# 사용 중인 프로세스 종료
taskkill /PID <PID> /F
```

#### 2. 권한 문제
```bash
# Docker Desktop 관리자 권한으로 실행
# Windows Defender 방화벽 예외 추가
```

#### 3. 네트워크 연결 실패
```bash
# 네트워크 확인
docker network inspect ecoanp_network

# 컨테이너 재시작
docker-compose -f docker-compose.dagster.yml restart
```

### 고급 문제 해결

#### 1. 메모리 부족
```bash
# Docker 메모리 제한 설정
# Docker Desktop > Settings > Resources > Memory: 8GB 이상
```

#### 2. 디스크 공간 부족
```bash
# Docker 정리
docker system prune -a
docker volume prune
```

#### 3. 이미지 다운로드 실패
```bash
# 네트워크 프록시 설정 확인
# Docker Desktop > Settings > Resources > Proxies
```

## 🔧 성능 튜닝

### 1. 리소스 최적화
```yaml
# docker-compose.dagster.yml에 추가
services:
  dagster:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### 2. 로깅 최적화
```yaml
# 로그 드라이버 설정
services:
  dagster:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 📚 다음 단계

설치가 완료되면 다음 문서를 참조하세요:

1. **[USAGE.md](./USAGE.md)**: Dagster 사용법 및 Asset 개발
2. **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**: 상세한 문제 해결 가이드
3. **[README.md](../README.md)**: 전체 프로젝트 개요

---

## 🎉 설치 완료!

**축하합니다!** Dagster가 성공적으로 설치되었습니다.

**확인 사항:**
- ✅ Docker 컨테이너 실행 중
- ✅ 웹 인터페이스 접속 가능 (http://localhost:3000)
- ✅ TimescaleDB 연결 성공
- ✅ Asset 로드 완료

**문제가 있으면 언제든 말씀해주세요!** 🚀
