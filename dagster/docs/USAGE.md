# 📖 Dagster 사용법 및 Asset 개발 가이드

## 📋 목차
1. [기본 개념](#기본-개념)
2. [Asset 개발](#asset-개발)
3. [파이프라인 실행](#파이프라인-실행)
4. [모니터링 및 관리](#모니터링-및-관리)
5. [고급 기능](#고급-기능)

## 🧠 기본 개념

### Asset이란?
**Asset**은 Dagster에서 데이터를 표현하는 핵심 개념입니다.

```python
from dagster import asset, AssetExecutionContext

@asset
def influx_tags(context: AssetExecutionContext):
    """InfluxDB 스키마에서 태그 자동 생성"""
    # 태그 생성 로직
    return {"status": "success", "tags_created": 10}
```

### 의존성 관리
Asset 간의 의존성을 명시적으로 정의할 수 있습니다.

```python
@asset(deps=[influx_tags])
def influx_data(context: AssetExecutionContext):
    """태그가 생성된 후에만 실행"""
    # 데이터 수집 로직
    pass
```

### 스케줄링
정해진 시간에 자동으로 Asset을 실행할 수 있습니다.

```python
from dagster import asset, ScheduleDefinition

@asset
def daily_report(context: AssetExecutionContext):
    """매일 자정에 실행"""
    pass

daily_report_schedule = ScheduleDefinition(
    job=define_asset_job("daily_report_job"),
    cron_schedule="0 0 * * *"  # 매일 자정
)
```

## 🚀 Asset 개발

### 1. 기본 Asset 구조

#### influx_tags.py
```python
# dagster/assets/influx_tags.py
from dagster import asset, AssetExecutionContext, Config
import psycopg
from typing import Dict, Any
import json

class InfluxTagsConfig(Config):
    """태그 생성 설정"""
    batch_size: int = 100
    retry_count: int = 3

@asset(
    description="InfluxDB 스키마에서 태그 자동 생성",
    group_name="ecoanp",
    tags={"team": "data_engineering", "domain": "influxdb"}
)
def influx_tags(context: AssetExecutionContext, config: InfluxTagsConfig) -> Dict[str, Any]:
    """InfluxDB 스키마를 기반으로 태그를 자동 생성합니다."""
    
    context.log.info(f"태그 생성 시작 (배치 크기: {config.batch_size})")
    
    try:
        # TimescaleDB 연결
        conn = psycopg.connect(
            "postgresql://ecoanp_user:ecoanp_password@timescaledb:5432/ecoanp"
        )
        
        with conn.cursor() as cur:
            # 기존 태그 수 확인
            cur.execute("SELECT COUNT(*) FROM influx_tag")
            existing_count = cur.fetchone()[0]
            context.log.info(f"기존 태그 수: {existing_count}")
            
            # 스키마 데이터 조회 (예시)
            # 실제로는 InfluxDB API를 통해 스키마 조회
            schema_data = [
                {"DataName": "D100", "DataId": "1", "DataType": "float", "Unit": "V"},
                {"DataName": "D101", "DataId": "2", "DataType": "float", "Unit": "V"},
                {"DataName": "D102", "DataId": "3", "DataType": "float", "Unit": "V"}
            ]
            
            # 태그 생성 SQL
            for schema in schema_data:
                sql = """
                INSERT INTO influx_tag (key, tag_id, tag_name, tag_type, unit, meta)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (key) DO UPDATE SET
                    tag_id = EXCLUDED.tag_id,
                    tag_name = EXCLUDED.tag_name,
                    tag_type = EXCLUDED.tag_type,
                    unit = EXCLUDED.unit,
                    meta = EXCLUDED.meta,
                    updated_at = CURRENT_TIMESTAMP
                """
                
                meta = {
                    "source": "auto_generated",
                    "original_schema": schema,
                    "created_at": context.log.info("태그 생성 중...")
                }
                
                cur.execute(sql, (
                    schema["DataName"],
                    schema["DataId"],
                    schema["DataName"],
                    schema["DataType"],
                    schema["Unit"],
                    json.dumps(meta)
                ))
            
            conn.commit()
            
            # 생성된 태그 수 확인
            cur.execute("SELECT COUNT(*) FROM influx_tag")
            final_count = cur.fetchone()[0]
            tags_created = final_count - existing_count
            
            context.log.info(f"태그 생성 완료! {tags_created}개 생성됨")
            
            return {
                "status": "success",
                "tags_created": tags_created,
                "total_tags": final_count,
                "batch_size": config.batch_size
            }
            
    except Exception as e:
        context.log.error(f"태그 생성 실패: {str(e)}")
        raise e
        
    finally:
        if 'conn' in locals():
            conn.close()
```

#### influx_data.py
```python
# dagster/assets/influx_data.py
from dagster import asset, AssetExecutionContext, Config, RetryPolicy
from typing import Dict, Any, List
import psycopg
from datetime import datetime, timedelta
import json

class InfluxDataConfig(Config):
    """데이터 수집 설정"""
    time_window_hours: int = 1
    batch_size: int = 1000
    max_retries: int = 3

@asset(
    description="InfluxDB에서 실시간 데이터 수집 및 변환",
    group_name="ecoanp",
    deps=["influx_tags"],  # 태그가 먼저 생성되어야 함
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=60,  # 1분 후 재시도
        backoff=2  # 지수 백오프
    ),
    tags={"team": "data_engineering", "domain": "data_collection"}
)
def influx_data(context: AssetExecutionContext, config: InfluxDataConfig) -> Dict[str, Any]:
    """InfluxDB에서 데이터를 수집하여 TimescaleDB에 저장합니다."""
    
    context.log.info(f"데이터 수집 시작 (시간 창: {config.time_window_hours}시간)")
    
    try:
        # TimescaleDB 연결
        conn = psycopg.connect(
            "postgresql://ecoanp_user:ecoanp_password@timescaledb:5432/ecoanp"
        )
        
        with conn.cursor() as cur:
            # 최근 데이터 수집 (실제로는 InfluxDB API 호출)
            # 여기서는 예시 데이터 사용
            sample_data = [
                {
                    "timestamp": datetime.now() - timedelta(minutes=i),
                    "tag_name": f"D{100 + (i % 9)}",
                    "value": 10.0 + (i * 0.1),
                    "qc": 1,
                    "meta": {"source": "simulated"}
                }
                for i in range(config.batch_size)
            ]
            
            # 데이터 삽입
            insert_sql = """
            INSERT INTO influx_hist (ts, tag_name, value, qc, meta)
            VALUES (%s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (ts, tag_name) DO UPDATE SET
                value = EXCLUDED.value,
                qc = EXCLUDED.qc,
                meta = EXCLUDED.meta,
                updated_at = CURRENT_TIMESTAMP
            """
            
            records_inserted = 0
            for record in sample_data:
                cur.execute(insert_sql, (
                    record["timestamp"],
                    record["tag_name"],
                    record["value"],
                    record["qc"],
                    json.dumps(record["meta"])
                ))
                records_inserted += 1
            
            conn.commit()
            
            context.log.info(f"데이터 수집 완료! {records_inserted}개 레코드 삽입됨")
            
            return {
                "status": "success",
                "records_inserted": records_inserted,
                "time_window": f"{config.time_window_hours}시간",
                "batch_size": config.batch_size
            }
            
    except Exception as e:
        context.log.error(f"데이터 수집 실패: {str(e)}")
        raise e
        
    finally:
        if 'conn' in locals():
            conn.close()
```

#### aggregates.py
```python
# dagster/assets/aggregates.py
from dagster import asset, AssetExecutionContext, Config
from typing import Dict, Any
import psycopg

class AggregatesConfig(Config):
    """집계 생성 설정"""
    time_buckets: List[str] = ["1 minute", "5 minutes", "1 hour"]

@asset(
    description="TimescaleDB 연속 집계 생성",
    group_name="ecoanp",
    deps=["influx_data"],  # 데이터가 먼저 수집되어야 함
    tags={"team": "data_engineering", "domain": "aggregation"}
)
def create_aggregates(context: AssetExecutionContext, config: AggregatesConfig) -> Dict[str, Any]:
    """TimescaleDB 연속 집계를 생성합니다."""
    
    context.log.info("연속 집계 생성 시작...")
    
    try:
        # TimescaleDB 연결
        conn = psycopg.connect(
            "postgresql://ecoanp_user:ecoanp_password@timescaledb:5432/ecoanp"
        )
        
        with conn.cursor() as cur:
            # 기존 집계 확인
            cur.execute("""
                SELECT view_name FROM timescaledb_information.continuous_aggregates
                WHERE view_name LIKE 'influx_agg_%'
            """)
            existing_aggregates = [row[0] for row in cur.fetchall()]
            
            context.log.info(f"기존 집계: {existing_aggregates}")
            
            # 새로운 집계 생성
            for bucket in config.time_buckets:
                bucket_name = bucket.replace(" ", "_")
                view_name = f"influx_agg_{bucket_name}"
                
                if view_name not in existing_aggregates:
                    # 연속 집계 생성
                    create_sql = f"""
                    CREATE MATERIALIZED VIEW {view_name} AS
                    SELECT 
                        time_bucket('{bucket}', ts) AS bucket,
                        tag_name,
                        avg(value) as avg_value,
                        min(value) as min_value,
                        max(value) as max_value,
                        count(*) as record_count
                    FROM influx_hist
                    GROUP BY bucket, tag_name
                    WITH (timescaledb.continuous);
                    """
                    
                    cur.execute(create_sql)
                    context.log.info(f"집계 생성됨: {view_name}")
                    
                    # 압축 정책 설정
                    compression_sql = f"""
                    SELECT add_compression_policy('{view_name}', INTERVAL '7 days');
                    """
                    cur.execute(compression_sql)
                    
                    # 새로고침 정책 설정
                    refresh_sql = f"""
                    SELECT add_continuous_aggregate_policy('{view_name}',
                        start_offset => INTERVAL '1 hour',
                        end_offset => INTERVAL '1 minute',
                        schedule_interval => INTERVAL '5 minutes');
                    """
                    cur.execute(refresh_sql)
            
            conn.commit()
            
            # 최종 집계 목록
            cur.execute("""
                SELECT view_name FROM timescaledb_information.continuous_aggregates
                WHERE view_name LIKE 'influx_agg_%'
            """)
            final_aggregates = [row[0] for row in cur.fetchall()]
            
            context.log.info(f"연속 집계 생성 완료! 총 {len(final_aggregates)}개")
            
            return {
                "status": "success",
                "aggregates_created": len(final_aggregates),
                "aggregate_list": final_aggregates,
                "time_buckets": config.time_buckets
            }
            
    except Exception as e:
        context.log.error(f"집계 생성 실패: {str(e)}")
        raise e
        
    finally:
        if 'conn' in locals():
            conn.close()
```

### 2. Asset 초기화 파일

#### __init__.py
```python
# dagster/assets/__init__.py
from dagster import Definitions, load_assets_from_modules
from . import influx_tags, influx_data, aggregates

# 모든 Asset을 자동으로 로드
all_assets = load_assets_from_modules([influx_tags, influx_data, aggregates])

# Definitions 생성
defs = Definitions(
    assets=all_assets,
    resources={},
    schedules=[],
    sensors=[]
)
```

## 🔄 파이프라인 실행

### 1. 자동 실행 (스케줄)

#### 스케줄 정의
```python
# dagster/schedules.py
from dagster import ScheduleDefinition, define_asset_job
from dagster import load_assets_from_modules
from . import influx_tags, influx_data, aggregates

# Asset 로드
all_assets = load_assets_from_modules([influx_tags, influx_data, aggregates])

# Job 정의
ecoanp_pipeline_job = define_asset_job(
    "ecoanp_pipeline",
    selection=all_assets
)

# 스케줄 정의
ecoanp_daily_schedule = ScheduleDefinition(
    job=ecoanp_pipeline_job,
    cron_schedule="0 2 * * *",  # 매일 새벽 2시
    description="EcoAnP 일일 데이터 파이프라인"
)

ecoanp_hourly_schedule = ScheduleDefinition(
    job=ecoanp_pipeline_job,
    cron_schedule="0 * * * *",  # 매시간
    description="EcoAnP 시간별 데이터 파이프라인"
)
```

### 2. 수동 실행

#### CLI를 통한 실행
```bash
# 특정 Asset 실행
dagster asset materialize --select influx_tags

# 여러 Asset 실행
dagster asset materialize --select influx_tags influx_data

# 전체 파이프라인 실행
dagster asset materialize --all
```

#### Python 코드를 통한 실행
```python
from dagster import materialize
from dagster.assets import influx_tags, influx_data

# 특정 Asset 실행
result = materialize([influx_tags])

# 결과 확인
print(result.success)
print(result.output_value_for_asset_key("influx_tags"))
```

### 3. 조건부 실행

#### 의존성 기반 실행
```python
@asset(deps=[influx_tags])
def influx_data(context: AssetExecutionContext):
    """태그가 생성된 후에만 실행"""
    pass

@asset(deps=[influx_data])
def create_aggregates(context: AssetExecutionContext):
    """데이터가 수집된 후에만 실행"""
    pass
```

## 📊 모니터링 및 관리

### 1. Dagster UI

#### 주요 기능
- **Assets**: Asset 목록 및 상태
- **Ops**: 작업 실행 상태
- **Schedules**: 스케줄 관리
- **Sensors**: 센서 상태
- **Logs**: 실행 로그
- **Runs**: 실행 이력

#### 모니터링 방법
1. **실시간 상태**: Asset별 실행 상태 실시간 확인
2. **실행 이력**: 성공/실패 이력 및 로그 확인
3. **성능 메트릭**: 실행 시간, 리소스 사용량 등
4. **의존성 그래프**: Asset 간 의존성 시각화

### 2. 로깅 및 알림

#### 로깅 레벨
```python
from dagster import AssetExecutionContext

@asset
def example_asset(context: AssetExecutionContext):
    context.log.debug("디버그 정보")
    context.log.info("일반 정보")
    context.log.warning("경고")
    context.log.error("오류")
```

#### 알림 설정
```python
from dagster import asset, Failure, HookContext, hook

@hook(required_resource_keys={"slack"})
def slack_notification(context: HookContext):
    """실패 시 Slack 알림"""
    if context.dagster_event.event_type_value == "ASSET_MATERIALIZATION_PLANNED":
        context.resources.slack.send_message(
            channel="#data-pipeline",
            text=f"Asset 실행 시작: {context.asset_key}"
        )

@asset(hooks={slack_notification})
def critical_asset(context: AssetExecutionContext):
    """중요 Asset"""
    pass
```

## 🚀 고급 기능

### 1. 리소스 관리

#### 리소스 정의
```python
from dagster import resource, ConfigurableResource
from typing import Dict, Any

class PostgresResource(ConfigurableResource):
    host: str
    port: int
    database: str
    username: str
    password: str
    
    def get_connection(self):
        return psycopg.connect(
            f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        )

@resource(config_schema=PostgresResource)
def postgres_resource(context):
    return PostgresResource(**context.resource_config)
```

#### Asset에서 리소스 사용
```python
@asset(required_resource_keys={"postgres"})
def influx_data(context: AssetExecutionContext):
    """Postgres 리소스 사용"""
    conn = context.resources.postgres.get_connection()
    # 데이터 처리 로직
    conn.close()
```

### 2. 설정 관리

#### 설정 스키마
```python
from dagster import Config

class DataPipelineConfig(Config):
    """데이터 파이프라인 설정"""
    batch_size: int = 1000
    timeout_seconds: int = 300
    retry_count: int = 3
    enable_compression: bool = True
    compression_days: int = 7
```

#### 설정 사용
```python
@asset
def influx_data(context: AssetExecutionContext, config: DataPipelineConfig):
    """설정을 사용한 데이터 처리"""
    context.log.info(f"배치 크기: {config.batch_size}")
    context.log.info(f"타임아웃: {config.timeout_seconds}초")
    
    # 설정 기반 로직
    if config.enable_compression:
        # 압축 활성화
        pass
```

### 3. 테스트

#### Asset 테스트
```python
from dagster import materialize, build_asset_context
from dagster.assets import influx_tags

def test_influx_tags():
    """influx_tags Asset 테스트"""
    context = build_asset_context()
    
    # Asset 실행
    result = materialize([influx_tags], context=context)
    
    # 결과 검증
    assert result.success
    output = result.output_value_for_asset_key("influx_tags")
    assert output["status"] == "success"
    assert output["tags_created"] > 0
```

## 📚 다음 단계

이제 Dagster를 사용하여 데이터 파이프라인을 구축할 수 있습니다!

**추천 학습 순서:**
1. **기본 Asset 개발**: influx_tags, influx_data 구현
2. **의존성 관리**: Asset 간 의존성 설정
3. **스케줄링**: 자동 실행 설정
4. **모니터링**: UI를 통한 파이프라인 관리
5. **고급 기능**: 리소스, 설정, 테스트 등

**문제가 있으면 언제든 말씀해주세요!** 🚀
