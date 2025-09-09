# 🛠️ Dagster 문제 해결 가이드

## 📋 목차
1. [일반적인 문제](#일반적인-문제)
2. [컨테이너 문제](#컨테이너-문제)
3. [네트워크 문제](#네트워크-문제)
4. [Asset 실행 문제](#asset-실행-문제)
5. [성능 문제](#성능-문제)
6. [고급 문제 해결](#고급-문제-해결)

## ❌ 일반적인 문제

### 1. 포트 충돌

#### 문제 증상
```bash
Error response from daemon: failed to set up container networking: 
driver failed programming external connectivity on endpoint ecoanp_dagster: 
Bind for 0.0.0.0:3000 failed: port is already allocated
```

#### 해결 방법
```bash
# 포트 3000 사용 확인
netstat -an | findstr ":3000"

# 사용 중인 프로세스 종료
taskkill /PID <PID> /F

# 또는 다른 포트 사용
# docker-compose.dagster.yml 수정
ports:
  - "3001:3000"  # 3001 포트 사용
```

### 2. 권한 문제

#### 문제 증상
```bash
Permission denied: cannot connect to the Docker daemon
```

#### 해결 방법
```bash
# Docker Desktop 관리자 권한으로 실행
# Windows Defender 방화벽 예외 추가
# WSL2 백엔드 활성화 확인
```

### 3. 메모리 부족

#### 문제 증상
```bash
Container killed due to memory limit
```

#### 해결 방법
```bash
# Docker Desktop 메모리 설정
# Settings > Resources > Memory: 8GB 이상

# 컨테이너 메모리 제한 설정
services:
  dagster:
    deploy:
      resources:
        limits:
          memory: 2G
```

## 🐳 컨테이너 문제

### 1. Dagster 컨테이너 시작 실패

#### 문제 진단
```bash
# 컨테이너 상태 확인
docker ps -a --filter "name=dagster"

# 로그 확인
docker logs ecoanp_dagster
docker logs ecoanp_dagster_daemon

# 컨테이너 상세 정보
docker inspect ecoanp_dagster
```

#### 일반적인 원인 및 해결

##### 이미지 다운로드 실패
```bash
# 이미지 강제 재다운로드
docker pull dagster/dagster:latest

# 기존 이미지 제거
docker rmi dagster/dagster:latest

# 컨테이너 재시작
docker-compose -f docker-compose.dagster.yml up -d --force-recreate
```

##### 볼륨 마운트 실패
```bash
# 볼륨 권한 확인
ls -la dagster/

# 볼륨 재생성
docker volume prune
docker-compose -f docker-compose.dagster.yml down -v
docker-compose -f docker-compose.dagster.yml up -d
```

### 2. Dagster Daemon 문제

#### 문제 증상
```bash
# Daemon이 시작되지 않음
# 스케줄이 실행되지 않음
# Asset이 자동으로 실행되지 않음
```

#### 해결 방법
```bash
# Daemon 로그 확인
docker logs ecoanp_dagster_daemon

# Daemon 재시작
docker restart ecoanp_dagster_daemon

# 전체 재시작
docker-compose -f docker-compose.dagster.yml restart
```

## 🌐 네트워크 문제

### 1. TimescaleDB 연결 실패

#### 문제 진단
```bash
# 네트워크 확인
docker network ls
docker network inspect ecoanp_network

# 컨테이너 간 연결 테스트
docker exec ecoanp_dagster ping timescaledb

# TimescaleDB 상태 확인
docker exec ecoanp_timescaledb pg_isready -U ecoanp_user -d ecoanp
```

#### 해결 방법

##### 네트워크 재생성
```bash
# 기존 네트워크 제거
docker network rm ecoanp_network

# 컨테이너 재시작
docker-compose -f docker-compose.timescaledb-only.yml up -d
docker-compose -f docker-compose.dagster.yml up -d
```

##### 연결 문자열 확인
```python
# Asset에서 연결 문자열 확인
# dagster/assets/influx_tags.py
conn = psycopg.connect(
    "postgresql://ecoanp_user:ecoanp_password@timescaledb:5432/ecoanp"
)
```

### 2. 외부 InfluxDB 연결 문제

#### 문제 진단
```bash
# 현장 InfluxDB 연결 테스트
curl -f http://<INFLUXDB_HOST>:8086/ping

# 네트워크 라우팅 확인
traceroute <INFLUXDB_HOST>
```

#### 해결 방법

##### 방화벽 설정
```bash
# Windows 방화벽 예외 추가
# Docker Desktop 네트워크 허용

# WSL2 네트워크 설정
# /etc/wsl.conf
[network]
generateResolvConf = false
```

##### 프록시 설정
```yaml
# docker-compose.dagster.yml에 추가
services:
  dagster:
    environment:
      - HTTP_PROXY=http://proxy:port
      - HTTPS_PROXY=http://proxy:port
      - NO_PROXY=localhost,127.0.0.1,timescaledb
```

## 🔄 Asset 실행 문제

### 1. Asset 로드 실패

#### 문제 증상
```bash
# Dagster UI에서 Asset이 보이지 않음
# "No assets found" 메시지
```

#### 해결 방법

##### Asset 파일 확인
```bash
# Asset 파일 구조 확인
ls -la dagster/assets/

# Python 문법 오류 확인
python -m py_compile dagster/assets/influx_tags.py
```

##### 워크스페이스 설정 확인
```yaml
# dagster/config/workspace.yaml
load_from:
  - python_file:
      relative_path: assets/__init__.py
      working_directory: .
```

### 2. Asset 실행 실패

#### 문제 진단
```bash
# Asset 실행 로그 확인
# Dagster UI > Assets > influx_tags > Materialize > View Logs

# CLI로 실행 테스트
docker exec ecoanp_dagster dagster asset materialize --select influx_tags
```

#### 일반적인 원인 및 해결

##### 의존성 문제
```python
# Asset 의존성 확인
@asset(deps=["influx_tags"])  # 올바른 Asset 키 사용
def influx_data(context: AssetExecutionContext):
    pass

# 의존성 순서 확인
# influx_tags → influx_data → create_aggregates
```

##### 리소스 문제
```python
# 필요한 리소스 확인
@asset(required_resource_keys={"postgres"})
def influx_data(context: AssetExecutionContext):
    # 리소스 사용
    conn = context.resources.postgres.get_connection()
```

##### 설정 문제
```python
# Config 스키마 확인
class InfluxTagsConfig(Config):
    batch_size: int = 100
    retry_count: int = 3

@asset
def influx_tags(context: AssetExecutionContext, config: InfluxTagsConfig):
    # 설정 사용
    context.log.info(f"배치 크기: {config.batch_size}")
```

### 3. Asset 실행 시간 초과

#### 문제 증상
```bash
# Asset이 실행 중이지만 완료되지 않음
# 타임아웃 오류
```

#### 해결 방법

##### 타임아웃 설정
```python
@asset(
    compute_kind="python",
    retry_policy=RetryPolicy(max_retries=3, delay=60)
)
def influx_data(context: AssetExecutionContext):
    # 타임아웃 처리
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Asset 실행 시간 초과")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(300)  # 5분 타임아웃
    
    try:
        # Asset 로직
        pass
    finally:
        signal.alarm(0)
```

##### 배치 처리 최적화
```python
@asset
def influx_data(context: AssetExecutionContext):
    # 배치 크기 조정
    batch_size = 1000  # 작은 배치로 처리
    
    for i in range(0, total_records, batch_size):
        batch = records[i:i + batch_size]
        # 배치 처리
        context.log.info(f"배치 {i//batch_size + 1} 처리 중...")
```

## ⚡ 성능 문제

### 1. 느린 Asset 실행

#### 문제 진단
```bash
# 실행 시간 확인
# Dagster UI > Assets > 실행 시간 메트릭

# 리소스 사용량 확인
docker stats ecoanp_dagster
```

#### 해결 방법

##### 병렬 처리
```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

@asset
def influx_data(context: AssetExecutionContext):
    # 병렬 처리
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for tag in tags:
            future = executor.submit(process_tag, tag)
            futures.append(future)
        
        # 결과 수집
        results = [f.result() for f in futures]
```

##### 데이터베이스 최적화
```sql
-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_influx_hist_ts_tag 
ON influx_hist (ts, tag_name);

-- 통계 업데이트
ANALYZE influx_hist;

-- 쿼리 최적화
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM influx_hist WHERE ts >= NOW() - INTERVAL '1 hour';
```

### 2. 메모리 사용량 과다

#### 문제 진단
```bash
# 메모리 사용량 확인
docker stats --no-stream

# 컨테이너 메모리 제한 확인
docker inspect ecoanp_dagster | grep -i memory
```

#### 해결 방법

##### 메모리 제한 설정
```yaml
# docker-compose.dagster.yml
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

##### 메모리 효율적인 처리
```python
@asset
def influx_data(context: AssetExecutionContext):
    # 스트리밍 처리
    def process_stream():
        for chunk in data_stream:
            yield process_chunk(chunk)
    
    # 청크 단위로 처리
    for chunk in process_stream():
        # 메모리에서 즉시 해제
        process_and_save(chunk)
        del chunk
```

## 🔧 고급 문제 해결

### 1. 디버깅 모드

#### 상세 로깅 활성화
```yaml
# dagster/config/dagster.yaml
run_coordinator:
  module: dagster.core.run_coordinator
  class: QueuedRunCoordinator
  config:
    max_concurrent_runs: 10
    debug: true  # 디버그 모드

scheduler:
  module: dagster.core.scheduler
  class: DagsterDaemonScheduler
  config:
    debug: true  # 디버그 모드
```

#### Asset 디버깅
```python
@asset
def influx_tags(context: AssetExecutionContext):
    # 상세 로깅
    context.log.debug("함수 시작")
    context.log.debug(f"입력 파라미터: {locals()}")
    
    try:
        # 로직 실행
        result = process_data()
        context.log.debug(f"처리 결과: {result}")
        return result
    except Exception as e:
        context.log.error(f"오류 발생: {str(e)}")
        context.log.error(f"스택 트레이스: {traceback.format_exc()}")
        raise
```

### 2. 성능 프로파일링

#### cProfile 사용
```python
import cProfile
import pstats

@asset
def influx_data(context: AssetExecutionContext):
    # 성능 프로파일링
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        # Asset 로직
        result = process_data()
        return result
    finally:
        profiler.disable()
        
        # 프로파일 결과 저장
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.dump_stats('influx_data_profile.prof')
        
        context.log.info("성능 프로파일 저장됨: influx_data_profile.prof")
```

#### 메모리 프로파일링
```python
import tracemalloc

@asset
def influx_data(context: AssetExecutionContext):
    # 메모리 사용량 추적
    tracemalloc.start()
    
    try:
        # Asset 로직
        result = process_data()
        return result
    finally:
        # 메모리 사용량 확인
        current, peak = tracemalloc.get_traced_memory()
        context.log.info(f"현재 메모리: {current / 1024 / 1024:.1f} MB")
        context.log.info(f"최대 메모리: {peak / 1024 / 1024:.1f} MB")
        
        tracemalloc.stop()
```

### 3. 복구 및 백업

#### Asset 상태 복구
```bash
# 실패한 Asset 재실행
docker exec ecoanp_dagster dagster asset materialize --select influx_tags --force

# 특정 시점으로 복구
docker exec ecoanp_dagster dagster asset materialize --select influx_tags --partition 2024-01-01
```

#### 데이터베이스 백업
```bash
# TimescaleDB 백업
docker exec ecoanp_timescaledb pg_dump -U ecoanp_user ecoanp > backup_$(date +%Y%m%d_%H%M%S).sql

# Dagster 설정 백업
tar -czf dagster_backup_$(date +%Y%m%d_%H%M%S).tar.gz dagster/
```

## 📚 추가 리소스

### 🔗 공식 문서
- [Dagster Troubleshooting](https://docs.dagster.io/troubleshooting)
- [Dagster Debugging](https://docs.dagster.io/concepts/debugging)
- [Dagster Performance](https://docs.dagster.io/concepts/performance)

### 🆘 커뮤니티 지원
- [Dagster GitHub Issues](https://github.com/dagster-io/dagster/issues)
- [Dagster Discord](https://discord.gg/dagster)
- [Dagster Community](https://dagster.io/community)

---

## 🎯 문제 해결 체크리스트

**기본 문제 해결 순서:**
1. ✅ 컨테이너 상태 확인 (`docker ps`)
2. ✅ 로그 확인 (`docker logs`)
3. ✅ 네트워크 연결 확인 (`docker network inspect`)
4. ✅ 포트 충돌 확인 (`netstat -an`)
5. ✅ 리소스 사용량 확인 (`docker stats`)
6. ✅ Asset 코드 문법 확인 (`python -m py_compile`)
7. ✅ 의존성 순서 확인
8. ✅ 설정 파일 검증

**문제가 지속되면:**
- 상세한 오류 메시지와 함께 GitHub Issues 등록
- Dagster Discord에서 커뮤니티 도움 요청
- 공식 문서의 Troubleshooting 섹션 참조

**문제가 있으면 언제든 말씀해주세요!** 🚀
