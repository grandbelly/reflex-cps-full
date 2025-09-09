from dagster import asset, AssetExecutionContext, Failure
import asyncio
import psycopg
from psycopg_pool import AsyncConnectionPool
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timedelta
import json
import os

# 환경 변수로 연결 정보 가져오기 (레거시 기본값 폴백 유지)
INFLUX_URL = os.getenv("INFLUX_URL", "http://192.168.1.80:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "vFq54W9Y0FoUvVIO9suUeeZYmxhYwAGsA3pdxRfFqeNLBrNTybpiyIZ5qWHoOCSRgWB23eXTPmnn-Uqz6yAQvw==")
INFLUX_ORG = os.getenv("INFLUX_ORG", "EON")
RAW_BUCKET = os.getenv("INFLUX_RAW_BUCKET", "5603a3eb-89e2-4e15-8cbb-60750c6588d3_raw")
META_BUCKET = os.getenv("INFLUX_META_BUCKET", "5603a3eb-89e2-4e15-8cbb-60750c6588d3_meta")
INFLUX_MEASUREMENT = os.getenv("INFLUX_MEASUREMENT", "*")
INFLUX_RANGE = os.getenv("INFLUX_RANGE", "5m")  # e.g., 5m, 1h
INGEST_TAG = os.getenv("INGEST_TAG")  # optional narrow to a specific _field (tag_id)
INGEST_LIMIT = int(os.getenv("INGEST_LIMIT", "0") or 0)  # 0 = no cap
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

TS_DSN = os.getenv("TS_DSN", "postgresql://ecoanp_user:ecoanp_password@timescaledb:5432/ecoanp")

def _dsn_with_timeout(dsn: str, seconds: int = 5) -> str:
    if not dsn:
        return dsn
    return dsn + ("&" if "?" in dsn else "?") + f"connect_timeout={seconds}"

# ============================================================================
# 1. 메타데이터 동기화 (Node-RED 첫 번째 플로우 대체)
# ============================================================================

@asset
def sync_influx_meta(context: AssetExecutionContext):
    """InfluxDB 메타데이터를 TimescaleDB influx_tag 테이블에 동기화"""
    context.log.info("InfluxDB 메타데이터 동기화 시작...")
    # 환경 변수 검증
    missing = [k for k,v in {
        'INFLUX_URL': INFLUX_URL,
        'INFLUX_TOKEN': INFLUX_TOKEN,
        'INFLUX_ORG': INFLUX_ORG,
        'INFLUX_META_BUCKET': META_BUCKET,
    }.items() if not v]
    if missing:
        # 폴백이 있어도 비정상 환경이면 명시적 실패
        raise Failure(f"Influx env missing: {', '.join(missing)}",
                      metadata={"missing": missing, "url": INFLUX_URL, "org": INFLUX_ORG})
    
    try:
        # InfluxDB 클라이언트 설정
        client = influxdb_client.InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG
        )
        
        # 쿼리 API
        query_api = client.query_api()
        
        # META_BUCKET에서 schema measurement의 json 필드 쿼리 (최근 60일)
        query = f'''
        from(bucket: "{META_BUCKET}")
          |> range(start: -60d)
          |> filter(fn: (r) => r._measurement == "schema" and r._field == "json")
          |> last()
          |> keep(columns: ["_value"])
        '''
        
        result = query_api.query(query)
        
        if not result or not result[0].records:
            context.log.warning("메타데이터를 찾을 수 없습니다.")
            return {"synced": False, "reason": "no_metadata_found"}
        
        # JSON 파싱
        meta_json = result[0].records[0].get_value()
        meta_data = json.loads(meta_json)
        
        # RawDataColumns 추출
        raw_data_columns = meta_data.get('RawDataColumns', [])
        
        context.log.info(f"메타데이터 파싱 완료: {len(raw_data_columns)}개 컬럼")
        
        # TimescaleDB에 동기화
        async def sync_to_db():
            pool = AsyncConnectionPool(_dsn_with_timeout(TS_DSN), min_size=1, max_size=10)
            await pool.open()
            
            try:
                async with pool.connection() as conn:
                    async with conn.cursor() as cur:
                        # influx_tag 테이블 생성
                        await cur.execute("""
                            CREATE TABLE IF NOT EXISTS influx_tag (
                                key TEXT PRIMARY KEY,
                                tag_id TEXT NOT NULL,
                                tag_name TEXT NOT NULL,
                                tag_type TEXT,
                                meta JSONB,
                                updated_at TIMESTAMPTZ DEFAULT NOW()
                            );
                        """)
                        
                        # 메타데이터 UPSERT
                        for column in raw_data_columns:
                            await cur.execute("""
                                INSERT INTO influx_tag (key, tag_id, tag_name, tag_type, meta, updated_at)
                                VALUES (%s, %s, %s, %s, %s, now())
                                ON CONFLICT (key)
                                DO UPDATE SET
                                    tag_id = EXCLUDED.tag_id,
                                    tag_name = EXCLUDED.tag_name,
                                    tag_type = EXCLUDED.tag_type,
                                    meta = EXCLUDED.meta,
                                    updated_at = now();
                            """, (
                                column.get('DataId'),
                                column.get('DataId'),
                                column.get('DataName'),
                                column.get('DataType'),
                                json.dumps(column)
                            ))
                        
                        # 동기화된 태그 수 확인
                        await cur.execute("SELECT COUNT(*) FROM influx_tag")
                        tag_count = await cur.fetchone()
                        
                        context.log.info(f"메타데이터 동기화 완료: {tag_count[0]}개 태그")
                        
                        return {
                            "synced": True,
                            "tags_count": tag_count[0],
                            "sync_time": datetime.now().isoformat(),
                            "raw_data_columns": len(raw_data_columns)
                        }
                        
            except Exception as e:
                context.log.error(f"TimescaleDB 동기화 실패: {str(e)}")
                raise e
            finally:
                await pool.close()
        
        # 비동기 함수 실행
        result = asyncio.run(sync_to_db())
        
        # 클라이언트 정리
        client.close()
        
        return result
        
    except Exception as e:
        context.log.error(f"메타데이터 동기화 실패: {str(e)}")
        raise e

# ============================================================================
# 2. 원시 데이터 수집 및 저장 (Node-RED 두 번째 플로우 대체)
# ============================================================================

@asset
def collect_influx_raw_data(context: AssetExecutionContext):
    """InfluxDB에서 원시 센서 데이터 수집 (최근 5분)"""
    context.log.info("InfluxDB 원시 데이터 수집 시작...")
    # 환경 변수 검증
    missing = [k for k,v in {
        'INFLUX_URL': INFLUX_URL,
        'INFLUX_TOKEN': INFLUX_TOKEN,
        'INFLUX_ORG': INFLUX_ORG,
        'INFLUX_RAW_BUCKET': RAW_BUCKET,
    }.items() if not v]
    if missing:
        raise Failure(f"Influx env missing: {', '.join(missing)}",
                      metadata={"missing": missing, "bucket": RAW_BUCKET})
    
    try:
        # InfluxDB 클라이언트 설정
        client = influxdb_client.InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG
        )
        
        # 쿼리 API
        query_api = client.query_api()
        
        # RAW_BUCKET에서 최근 데이터 쿼리
        m_filter = "" if INFLUX_MEASUREMENT in (None, "", "*") else f" |> filter(fn: (r) => r._measurement == \"{INFLUX_MEASUREMENT}\")"
        f_filter = "" if not INGEST_TAG else f" |> filter(fn: (r) => r._field == \"{INGEST_TAG}\")"
        query = f'''from(bucket: "{RAW_BUCKET}")
          |> range(start: -{INFLUX_RANGE})
          {m_filter}
          {f_filter}
          |> keep(columns: ["_time", "_field", "_value", "_measurement"])'''
        
        result = query_api.query(query)
        
        # 데이터 정리
        raw_data = []
        for table in result:
            for record in table.records:
                data_point = {
                    "_time": record.get_time(),
                    "_field": record.get_field(),
                    "_value": record.get_value(),
                    "_measurement": record.get_measurement()
                }
                raw_data.append(data_point)
        
        # 샘플 로그
        context.log.info(json.dumps({
            "stage": "collect",
            "range": INFLUX_RANGE,
            "measurement": INFLUX_MEASUREMENT,
            "tag_filter": INGEST_TAG,
            "raw_count": len(raw_data),
            "sample": raw_data[:3]
        }, ensure_ascii=False, default=str))
        context.log.info(f"원시 데이터 수집 완료: {len(raw_data)}개 데이터 포인트 (range={INFLUX_RANGE}, measurement={INFLUX_MEASUREMENT}, tag={INGEST_TAG or '*'})")
        if not raw_data:
            raise Failure("Influx returned no data",
                          metadata={"range": INFLUX_RANGE, "measurement": INFLUX_MEASUREMENT, "bucket": RAW_BUCKET})
        
        # 클라이언트 정리
        client.close()
        
        return {
            "raw_data": raw_data,
            "collection_time": datetime.now().isoformat(),
            "source": "InfluxDB_RAW",
            "bucket": RAW_BUCKET,
            "time_range": "5m",
            "measurement": "1"
        }
        
    except Exception as e:
        context.log.error(f"원시 데이터 수집 실패: {str(e)}")
        raise e

@asset
def process_and_store_raw_data(context: AssetExecutionContext, collect_influx_raw_data, sync_influx_meta):
    """원시 데이터를 처리하고 TimescaleDB influx_hist에 저장"""
    context.log.info("원시 데이터 처리 및 저장 시작...")
    
    raw_data = collect_influx_raw_data["raw_data"]
    
    if not raw_data:
        raise Failure("No raw_data to process; upstream returned empty result")
    
    async def process_and_store():
        pool = AsyncConnectionPool(_dsn_with_timeout(TS_DSN), min_size=1, max_size=10)
        
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    # 절대 DDL 수행하지 않음: 하이퍼테이블/테이블/인덱스는 DDL 단계에서만 생성
                    pass
                    
                    # 데이터 처리 및 저장
                    from math import isfinite
                    processed_data = []
                    for point in raw_data:
                        # QC 규칙 적용 (간단한 버전)
                        qc_code = 0
                        qc_reasons = ['ok']
                        
                        value = float(point["_value"]) if point["_value"] is not None else 0.0
                        if (value is None) or (not isfinite(value)):
                            qc_code = 5
                            qc_reasons = ['invalid']
                            value = 0.0
                        elif value < 0:
                            qc_code = 6
                            qc_reasons = ['negative_not_allowed']
                        
                        # 메타데이터 준비
                        meta = {
                            "source": "influx",
                            "measurement": point["_measurement"],
                            "tag_id": point["_field"],
                            "qc": {"code": qc_code, "reason": qc_reasons}
                        }
                        
                        processed_data.append({
                            "ts": point["_time"].isoformat(),
                            "tag_id": point["_field"],
                            "value": value,
                            "qc": qc_code,
                            "meta": meta
                        })
                    
                    # 제한 적용
                    if INGEST_LIMIT and len(processed_data) > INGEST_LIMIT:
                        processed_data = processed_data[:INGEST_LIMIT]
                    # 배치 삽입 (청크 단위로 분할)
                    chunk_size = 500
                    total_stored = 0
                    total_batches = 0
                    
                    for i in range(0, len(processed_data), chunk_size):
                        chunk = processed_data[i:i + chunk_size]
                        
                        # JSON 배열로 변환 (NaN 금지)
                        chunk_json = json.dumps(chunk, allow_nan=False)
                        
                        # UPSERT 실행 (또는 DRY_RUN)
                        if DRY_RUN:
                            context.log.info(json.dumps({
                                "stage": "dry_run",
                                "batch_index": i//chunk_size,
                                "batch_size": len(chunk)
                            }, ensure_ascii=False))
                            total_stored += len(chunk)
                            total_batches += 1
                            continue

                        await cur.execute("""
                            WITH rows AS (
                                SELECT (x->>'ts')::timestamptz AS ts,
                                       (x->>'tag_id') AS tag_id,
                                       (x->>'value')::float8 AS value,
                                       (x->>'qc')::int2 AS qc,
                                       (x->'meta')::jsonb AS meta
                                FROM jsonb_array_elements(%s::jsonb) x
                            )
                            INSERT INTO influx_hist (ts, tag_name, value, qc, meta)
                            SELECT r.ts, COALESCE(t.tag_name, r.tag_id) AS tag_name, r.value, r.qc, r.meta
                            FROM rows r
                            LEFT JOIN influx_tag t ON t.tag_id = r.tag_id
                            ON CONFLICT (ts, tag_name) DO UPDATE
                            SET value = EXCLUDED.value,
                                qc = EXCLUDED.qc,
                                meta = EXCLUDED.meta;
                        """, (chunk_json,))
                        total_stored += len(chunk)
                        total_batches += 1
                        await conn.commit()

                    context.log.info(json.dumps({
                        "stage": "store",
                        "batches": total_batches,
                        "stored_records": total_stored,
                        "dry_run": DRY_RUN,
                        "limit": INGEST_LIMIT
                    }, ensure_ascii=False))
                    
                    # 저장된 데이터 확인
                    await cur.execute("""
                        SELECT COUNT(*) FROM influx_hist
                        WHERE ts >= NOW() - INTERVAL '1 hour'
                    """)
                    recent_count = await cur.fetchone()
                    
                    return {
                        "stored": True,
                        "stored_records": total_stored,
                        "recent_total": recent_count[0] if recent_count else 0,
                        "storage_time": datetime.now().isoformat(),
                        "table": "influx_hist",
                        "database": "TimescaleDB"
                    }
                    
        except Exception as e:
            context.log.error(f"데이터 처리 및 저장 실패: {str(e)}")
            raise e
        finally:
            await pool.close()
    
    # 비동기 함수 실행
    return asyncio.run(process_and_store())

# ============================================================================
# 3. 유틸리티 Asset들
# ============================================================================

@asset
def create_timescale_views(context: AssetExecutionContext, process_and_store_raw_data):
    """TimescaleDB에 유용한 뷰 생성"""
    context.log.info("TimescaleDB 뷰 생성 시작...")
    
    async def create_views():
        pool = AsyncConnectionPool(TS_DSN, min_size=1, max_size=10)
        
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    # 1시간 단위 집계 뷰
                    await cur.execute("""
                        CREATE OR REPLACE VIEW influx_hourly_stats AS
                        SELECT 
                            time_bucket('1 hour', ts) AS bucket,
                            tag_name,
                            COUNT(*) as readings_count,
                            AVG(value) as avg_value,
                            MIN(value) as min_value,
                            MAX(value) as max_value,
                            STDDEV(value) as stddev_value,
                            AVG(qc) as avg_qc
                        FROM influx_hist
                        GROUP BY bucket, tag_name
                        ORDER BY bucket DESC, tag_name;
                    """)
                    
                    # 일일 집계 뷰
                    await cur.execute("""
                        CREATE OR REPLACE VIEW influx_daily_stats AS
                        SELECT 
                            time_bucket('1 day', ts) AS bucket,
                            tag_name,
                            COUNT(*) as readings_count,
                            AVG(value) as avg_value,
                            MIN(value) as min_value,
                            MAX(value) as max_value,
                            STDDEV(value) as stddev_value,
                            AVG(qc) as avg_qc
                        FROM influx_hist
                        GROUP BY bucket, tag_name
                        ORDER BY bucket DESC, tag_name;
                    """)
                    
                    # 태그별 최근 상태 뷰
                    await cur.execute("""
                        CREATE OR REPLACE VIEW influx_latest_status AS
                        SELECT DISTINCT ON (tag_name)
                            tag_name,
                            value as latest_value,
                            ts as latest_reading,
                            qc as latest_qc,
                            meta
                        FROM influx_hist
                        ORDER BY tag_name, ts DESC;
                    """)
                    
                    context.log.info("TimescaleDB 뷰 생성 완료")
                    
                    return {
                        "views_created": [
                            "influx_hourly_stats",
                            "influx_daily_stats", 
                            "influx_latest_status"
                        ],
                        "creation_time": datetime.now().isoformat(),
                        "database": "TimescaleDB"
                    }
                    
        except Exception as e:
            context.log.error(f"뷰 생성 실패: {str(e)}")
            raise e
        finally:
            await pool.close()
    
    return asyncio.run(create_views())


@asset
def ingest_health(context: AssetExecutionContext):
    """Report recent influx_hist counts to validate ingestion."""
    async def run():
        pool = AsyncConnectionPool(_dsn_with_timeout(TS_DSN), min_size=1, max_size=5)
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT tag_name, COUNT(*) AS rows
                        FROM public.influx_hist
                        WHERE ts >= NOW() - INTERVAL '15 minutes'
                        GROUP BY tag_name
                        ORDER BY rows DESC
                        LIMIT 10
                    """)
                    rows = await cur.fetchall()
                    report = {"top_tags": [{"tag_name": r[0], "rows": int(r[1])} for r in rows]}
                    context.log.info(json.dumps(report, ensure_ascii=False))
                    return report
        finally:
            await pool.close()

    return asyncio.run(run())


@asset
def influx_hist_ingest(context: AssetExecutionContext, sync_influx_meta):
    """One-shot ingestion: read from Influx, write to Timescale, return summary.
    Honors INFLUX_RANGE / INFLUX_MEASUREMENT / INGEST_TAG / INGEST_LIMIT / DRY_RUN.
    """
    # 1) Read from Influx
    client = influxdb_client.InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    m_filter = "" if INFLUX_MEASUREMENT in (None, "", "*") else f" |> filter(fn: (r) => r._measurement == \"{INFLUX_MEASUREMENT}\")"
    f_filter = "" if not INGEST_TAG else f" |> filter(fn: (r) => r._field == \"{INGEST_TAG}\")"
    query = f'''from(bucket: "{RAW_BUCKET}")
      |> range(start: -{INFLUX_RANGE})
      {m_filter}
      {f_filter}
      |> keep(columns: ["_time", "_field", "_value", "_measurement"])'''
    tables = client.query_api().query(query)
    raw = []
    for t in tables:
        for r in t.records:
            raw.append({
                "_time": r.get_time(),
                "_field": r.get_field(),
                "_value": r.get_value(),
                "_measurement": r.get_measurement()
            })
    
    # Debug output
    debug_info = {
        "stage": "collect",
        "timestamp": datetime.now().isoformat(),
        "range": INFLUX_RANGE,
        "bucket": RAW_BUCKET,
        "count": len(raw),
        "unique_fields": list(set(r["_field"] for r in raw)) if raw else [],
        "sample": raw[:3] if raw else []
    }
    context.log.info(json.dumps(debug_info, ensure_ascii=False, default=str))
    
    if not raw:
        raise Failure("Influx returned no data", metadata={"query": query})

    # 2) Transform
    from math import isfinite
    processed = []
    for p in raw:
        v = float(p["_value"]) if p["_value"] is not None else 0.0
        qc = 0
        if (v is None) or (not isfinite(v)):
            qc = 5; v = 0.0
        elif v < 0:
            qc = 6
        processed.append({
            "ts": p["_time"].isoformat(),
            "tag_id": p["_field"],
            "value": v,
            "qc": qc,
            "meta": {"source": "influx", "measurement": p["_measurement"], "tag_id": p["_field"], "qc": {"code": qc}}
        })
    if INGEST_LIMIT and len(processed) > INGEST_LIMIT:
        processed = processed[:INGEST_LIMIT]

    # 3) Store to Timescale
    async def store():
        pool = AsyncConnectionPool(_dsn_with_timeout(TS_DSN), min_size=1, max_size=5)
        await pool.open()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    # 절대 DDL 수행하지 않음: 하이퍼테이블/테이블/인덱스는 DDL 단계에서만 생성
                    pass
                    # Pre-check FK: ensure all tags exist in influx_tag
                    tag_ids = sorted({str(p["tag_id"]) for p in processed})
                    if tag_ids:
                        tags_json = json.dumps([{"tag": t} for t in tag_ids])
                        await cur.execute(
                            """
                            WITH tags AS (
                              SELECT (x->>'tag') AS tag
                              FROM jsonb_array_elements(%s::jsonb) x
                            )
                            SELECT t.tag
                            FROM tags t
                            LEFT JOIN influx_tag it ON it.tag_id = t.tag
                            WHERE it.tag_id IS NULL
                            LIMIT 50
                            """,
                            (tags_json,),
                        )
                        missing = [r[0] for r in await cur.fetchall()]
                        if missing:
                            # Auto-create missing tags
                            context.log.warning(f"Auto-creating {len(missing)} missing tags: {missing[:5]}")
                            for tag_id in missing:
                                await cur.execute("""
                                    INSERT INTO influx_tag (key, tag_id, tag_name, tag_type, meta, updated_at)
                                    VALUES (%s, %s, %s, 'auto', %s, now())
                                    ON CONFLICT (key) DO NOTHING;
                                """, (
                                    str(tag_id),
                                    str(tag_id),
                                    f"TAG_{tag_id}",  # Default tag name
                                    json.dumps({"auto_created": True, "tag_id": tag_id})
                                ))
                    total = 0
                    for i in range(0, len(processed), 500):
                        chunk = processed[i:i+500]
                        if DRY_RUN:
                            context.log.info(json.dumps({"stage": "dry_run", "batch": i//500, "size": len(chunk)}, ensure_ascii=False))
                            total += len(chunk)
                            continue
                        cj = json.dumps(chunk, allow_nan=False)
                        await cur.execute("""
                            WITH rows AS (
                                SELECT (x->>'ts')::timestamptz AS ts,
                                       (x->>'tag_id') AS tag_id,
                                       (x->>'value')::float8 AS value,
                                       (x->>'qc')::int2 AS qc,
                                       (x->'meta')::jsonb AS meta
                                FROM jsonb_array_elements(%s::jsonb) x
                            )
                            INSERT INTO influx_hist (ts, tag_name, value, qc, meta)
                            SELECT r.ts, COALESCE(t.tag_name, r.tag_id) AS tag_name, r.value, r.qc, r.meta
                            FROM rows r
                            LEFT JOIN influx_tag t ON t.tag_name = r.tag_id OR t.tag_id = r.tag_id
                            ON CONFLICT (ts, tag_name) DO UPDATE
                            SET value = EXCLUDED.value,
                                qc = EXCLUDED.qc,
                                meta = EXCLUDED.meta;
                        """, (cj,))
                        total += len(chunk)
                        await conn.commit()
                    
                    # Get statistics for debugging
                    await cur.execute("""
                        SELECT 
                            COUNT(*) as recent_total,
                            COUNT(DISTINCT tag_name) as unique_tags,
                            MIN(ts) as earliest,
                            MAX(ts) as latest
                        FROM influx_hist 
                        WHERE ts >= now() - interval '15 minutes'
                    """)
                    stats = await cur.fetchone()
                    
                    result = {
                        "stored": total,
                        "recent15m": int(stats[0]) if stats else 0,
                        "unique_tags": int(stats[1]) if stats else 0,
                        "earliest": str(stats[2]) if stats else None,
                        "latest": str(stats[3]) if stats else None,
                        "timestamp": datetime.now().isoformat()
                    }
                    return result
        finally:
            await pool.close()

    result = asyncio.run(store())
    
    # Final debug output
    final_info = {
        "stage": "done",
        "timestamp": datetime.now().isoformat(),
        "ingestion_result": result,
        "env": {
            "INFLUX_RANGE": INFLUX_RANGE,
            "INFLUX_MEASUREMENT": INFLUX_MEASUREMENT,
            "INGEST_TAG": INGEST_TAG,
            "INGEST_LIMIT": INGEST_LIMIT,
            "DRY_RUN": DRY_RUN
        }
    }
    context.log.info(json.dumps(final_info, ensure_ascii=False, indent=2))
    return result


@asset
def influx_hist_ingest_min(context: AssetExecutionContext):
    """Minimal ingestion sanity check: insert a single recent point.
    Assumes schema/hypertable already exist. Uses INFLUX_RANGE/INGEST_TAG.
    """
    # 1) Read one point from Influx
    client = influxdb_client.InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    m_filter = "" if INFLUX_MEASUREMENT in (None, "", "*") else f" |> filter(fn: (r) => r._measurement == \"{INFLUX_MEASUREMENT}\")"
    f_filter = "" if not INGEST_TAG else f" |> filter(fn: (r) => r._field == \"{INGEST_TAG}\")"
    q = f'''from(bucket: "{RAW_BUCKET}") |> range(start: -{INFLUX_RANGE}) {m_filter} {f_filter}
            |> keep(columns:["_time","_field","_value","_measurement"]) |> limit(n:1)'''
    tables = client.query_api().query(q)
    rec = None
    for t in tables:
        if t.records:
            rec = t.records[0]
            break
    if not rec:
        raise Failure("No point from Influx", metadata={"query": q})
    point = {
        "ts": rec.get_time(),
        "tag_id": rec.get_field(),
        "value": float(rec.get_value() or 0.0),
        "measurement": rec.get_measurement(),
    }
    context.log.info(f"sample_point: ts={point['ts']} tag_id={point['tag_id']} value={point['value']}")

    # 2) Insert single row into Timescale
    async def insert_one():
        pool = AsyncConnectionPool(_dsn_with_timeout(TS_DSN), min_size=1, max_size=2)
        await pool.open()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    # Get proper tag_name from influx_tag table
                    await cur.execute(
                        """
                        INSERT INTO influx_hist (ts, tag_name, value, qc, meta)
                        SELECT %s, COALESCE(t.tag_name, %s), %s, %s, %s
                        FROM (VALUES (1)) AS dummy
                        LEFT JOIN influx_tag t ON t.tag_id = %s
                        ON CONFLICT (ts, tag_name) DO UPDATE
                        SET value=EXCLUDED.value, qc=EXCLUDED.qc, meta=EXCLUDED.meta;
                        """,
                        (
                            point["ts"],
                            str(point["tag_id"]),  # fallback if not found
                            point["value"],
                            0,
                            json.dumps({"source": "influx", "measurement": point["measurement"]}),
                            str(point["tag_id"]),  # for JOIN
                        ),
                    )
                    await conn.commit()
                    await cur.execute("SELECT COUNT(*) FROM influx_hist WHERE ts>=now()-interval '15 minutes'")
                    cnt = (await cur.fetchone())[0]
                    return {"recent15m": int(cnt)}
        finally:
            await pool.close()

    res = asyncio.run(insert_one())
    context.log.info(json.dumps({"stage": "min_insert", **res}, ensure_ascii=False, default=str))
    return res
