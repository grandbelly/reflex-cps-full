import os
import time
from dagster import (
    asset, 
    Definitions, 
    define_asset_job, 
    AssetSelection, 
    ScheduleDefinition,
    sensor,
    RunRequest,
    SensorEvaluationContext,
    SkipReason
)
from . import influx_timescale_assets
from .ts_health import ts_health
from .db_smoke_asset import db_smoke

@asset
def hello_world():
    """간단한 테스트 Asset"""
    return "Hello World from Dagster!"

@asset
def test_calculation():
    """간단한 계산 테스트 Asset"""
    numbers = list(range(1, 11))
    total = sum(numbers)
    average = total / len(numbers)

    return {
        "numbers": numbers,
        "total": total,
        "average": average
    }

# Definitions 생성
include_influx = os.getenv("INCLUDE_INFLUX_ASSETS", "true").lower() == "true"

asset_list = [
    db_smoke,
    ts_health,
    hello_world,
    test_calculation,
    influx_timescale_assets.ingest_health,
    influx_timescale_assets.influx_hist_ingest,
    influx_timescale_assets.influx_hist_ingest_min,
]
if include_influx:
    asset_list += [
        influx_timescale_assets.sync_influx_meta,
        influx_timescale_assets.collect_influx_raw_data,
        influx_timescale_assets.process_and_store_raw_data,
        influx_timescale_assets.create_timescale_views,
    ]

ingestion_job = define_asset_job(
    "ingestion_job",
    selection=AssetSelection.keys(
        "sync_influx_meta",
        "influx_hist_ingest",
        "ingest_health",
    ),
)

# 10초마다 실행하는 센서
@sensor(job=ingestion_job, minimum_interval_seconds=10)
def influx_ingestion_sensor(context: SensorEvaluationContext):
    """10초마다 InfluxDB 데이터 수집"""
    # 마지막 실행 시간 확인
    last_run_key = "last_influx_ingestion"
    last_run = context.cursor or "0"
    current_time = str(int(time.time()))
    
    # 10초 경과 확인
    if int(current_time) - int(last_run) >= 10:
        context.update_cursor(current_time)
        return RunRequest(
            run_key=f"influx_ingestion_{current_time}",
            tags={"source": "10s_sensor"}
        )
    else:
        return SkipReason("Waiting for 10 seconds interval")

# 1분마다 실행 (백업용 스케줄)
ingestion_schedule = ScheduleDefinition(
    job=ingestion_job,
    cron_schedule="* * * * *",  # 매 1분마다 실행
    name="influx_ingestion_schedule_backup",
    description="InfluxDB 데이터 수집 백업 스케줄 (1분 주기)",
)

# 메타데이터는 하루에 한 번만 동기화
meta_sync_job = define_asset_job(
    "meta_sync_job",
    selection=AssetSelection.keys("sync_influx_meta"),
)

meta_sync_schedule = ScheduleDefinition(
    job=meta_sync_job,
    cron_schedule="0 0 * * *",  # 매일 자정에 실행
    name="meta_sync_schedule",
    description="InfluxDB 메타데이터 동기화 (일 1회)",
)

defs = Definitions(
    assets=asset_list,
    jobs=[ingestion_job, meta_sync_job],
    resources={},
    schedules=[ingestion_schedule, meta_sync_schedule],
    sensors=[influx_ingestion_sensor],  # 10초 센서 추가
)
