"""
지식베이스 초기화 스크립트 - 센서 메타데이터 및 도메인 지식 주입
"""

import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ksys_app.db import create_pool, q
from datetime import datetime


# 센서 메타데이터 정의
SENSOR_METADATA = [
    # D100 시리즈 - 온도 센서
    {
        'tag_name': 'D100',
        'content_type': 'sensor_spec',
        'content': 'D100은 주요 반응기 온도 센서입니다. 정상 작동 범위는 10-180°C이며, 경고 임계값은 180°C, 위험 임계값은 200°C입니다.',
        'metadata': {
            'sensor_tag': 'D100',
            'type': '온도',
            'unit': '°C',
            'location': '반응기 1',
            'criticality': 'HIGH'
        }
    },
    {
        'tag_name': 'D101',
        'content_type': 'sensor_spec',
        'content': 'D101은 보조 반응기 온도 센서입니다. 정상 작동 범위는 10-180°C이며, 경고 임계값은 180°C, 위험 임계값은 200°C입니다.',
        'metadata': {
            'sensor_tag': 'D101',
            'type': '온도',
            'unit': '°C',
            'location': '반응기 2',
            'criticality': 'HIGH'
        }
    },
    {
        'tag_name': 'D102',
        'content_type': 'sensor_spec',
        'content': 'D102는 냉각 시스템 온도 센서입니다. 정상 작동 범위는 10-180°C이며, 경고 임계값은 180°C, 위험 임계값은 200°C입니다.',
        'metadata': {
            'sensor_tag': 'D102',
            'type': '온도',
            'unit': '°C',
            'location': '냉각 시스템',
            'criticality': 'MEDIUM'
        }
    },
    
    # D200 시리즈 - 압력 센서
    {
        'tag_name': 'D200',
        'content_type': 'sensor_spec',
        'content': 'D200은 메인 파이프라인 압력 센서입니다. 정상 작동 범위는 100-1800 bar이며, 경고 임계값은 1800 bar, 위험 임계값은 2000 bar입니다.',
        'metadata': {
            'sensor_tag': 'D200',
            'type': '압력',
            'unit': 'bar',
            'location': '메인 파이프라인',
            'criticality': 'CRITICAL'
        }
    },
    {
        'tag_name': 'D201',
        'content_type': 'sensor_spec',
        'content': 'D201은 보조 파이프라인 압력 센서입니다. 정상 작동 범위는 100-1800 bar이며, 경고 임계값은 1800 bar, 위험 임계값은 2000 bar입니다.',
        'metadata': {
            'sensor_tag': 'D201',
            'type': '압력',
            'unit': 'bar',
            'location': '보조 파이프라인',
            'criticality': 'HIGH'
        }
    },
    
    # D300 시리즈 - 회전속도 센서
    {
        'tag_name': 'D300',
        'content_type': 'sensor_spec',
        'content': 'D300은 메인 터빈 회전속도 센서입니다. 정상 작동 범위는 1000-18000 rpm이며, 경고 임계값은 18000 rpm, 위험 임계값은 20000 rpm입니다.',
        'metadata': {
            'sensor_tag': 'D300',
            'type': '회전속도',
            'unit': 'rpm',
            'location': '메인 터빈',
            'criticality': 'HIGH'
        }
    },
]

# 도메인 지식
DOMAIN_KNOWLEDGE = [
    {
        'content_type': 'best_practice',
        'content': '온도 센서가 경고 임계값에 도달하면 즉시 냉각 시스템을 점검하고, 필요시 출력을 낮춰야 합니다.',
        'metadata': {'category': 'temperature_management'}
    },
    {
        'content_type': 'best_practice',
        'content': '압력 센서가 위험 임계값의 90%에 도달하면 즉시 안전 밸브를 점검하고 압력 해제 절차를 준비해야 합니다.',
        'metadata': {'category': 'pressure_management'}
    },
    {
        'content_type': 'troubleshooting',
        'content': '센서 값이 급격히 변동하는 경우, 센서 자체의 고장일 가능성이 있으므로 캘리브레이션을 확인해야 합니다.',
        'metadata': {'category': 'sensor_maintenance'}
    },
    {
        'content_type': 'safety_rule',
        'content': '동시에 3개 이상의 센서가 경고 상태일 경우, 시스템 전체 점검이 필요하며 필요시 가동을 중단해야 합니다.',
        'metadata': {'category': 'system_safety'}
    },
]


async def init_knowledge_base():
    """지식베이스 테이블 생성 및 데이터 초기화"""
    
    print("📚 지식베이스 초기화 시작...")
    
    # 1. 테이블 생성 (이미 있으면 스킵)
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS ai_knowledge_base (
        id SERIAL PRIMARY KEY,
        content_type VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        embedding VECTOR(1536),  -- OpenAI 임베딩 크기
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- 인덱스 생성
    CREATE INDEX IF NOT EXISTS idx_knowledge_content_type ON ai_knowledge_base(content_type);
    CREATE INDEX IF NOT EXISTS idx_knowledge_metadata ON ai_knowledge_base USING GIN(metadata);
    """
    
    try:
        await q(create_table_sql, ())
        print("✅ 지식베이스 테이블 생성/확인 완료")
    except Exception as e:
        print(f"⚠️ 테이블 생성 중 오류 (이미 존재할 수 있음): {e}")
    
    # 2. 기존 데이터 삭제 (선택적)
    clear_sql = "DELETE FROM ai_knowledge_base WHERE content_type IN ('sensor_spec', 'best_practice', 'troubleshooting', 'safety_rule')"
    await q(clear_sql, ())
    print("🗑️ 기존 데이터 정리 완료")
    
    # 3. 센서 메타데이터 삽입
    insert_sql = """
    INSERT INTO ai_knowledge_base (content_type, content, metadata)
    VALUES (%s, %s, %s)
    """
    
    print("📝 센서 메타데이터 삽입 중...")
    for sensor in SENSOR_METADATA:
        await q(insert_sql, (
            sensor['content_type'],
            sensor['content'],
            json.dumps(sensor.get('metadata', {}), ensure_ascii=False)
        ))
    print(f"  ✅ {len(SENSOR_METADATA)}개 센서 메타데이터 삽입 완료")
    
    # 4. 도메인 지식 삽입
    print("📝 도메인 지식 삽입 중...")
    for knowledge in DOMAIN_KNOWLEDGE:
        await q(insert_sql, (
            knowledge['content_type'],
            knowledge['content'],
            json.dumps(knowledge.get('metadata', {}), ensure_ascii=False)
        ))
    print(f"  ✅ {len(DOMAIN_KNOWLEDGE)}개 도메인 지식 삽입 완료")
    
    # 5. 통계 확인
    count_sql = """
    SELECT content_type, COUNT(*) as count
    FROM ai_knowledge_base
    GROUP BY content_type
    ORDER BY content_type
    """
    
    stats = await q(count_sql, ())
    
    print("\n📊 지식베이스 통계:")
    total = 0
    for stat in stats:
        print(f"  - {stat['content_type']}: {stat['count']}개")
        total += stat['count']
    print(f"  📌 총 {total}개 지식 항목")
    
    print("\n✅ 지식베이스 초기화 완료!")
    
    # 6. 샘플 쿼리 테스트
    test_sql = """
    SELECT content_type, content, metadata
    FROM ai_knowledge_base
    WHERE metadata->>'sensor_tag' = 'D101'
    LIMIT 1
    """
    
    test_result = await q(test_sql, ())
    if test_result:
        print("\n🧪 테스트 쿼리 (D101 센서):")
        print(f"  - Type: {test_result[0]['content_type']}")
        print(f"  - Content: {test_result[0]['content'][:100]}...")
        

if __name__ == "__main__":
    import json
    
    # PostgreSQL 연결 정보 설정
    os.environ['POSTGRES_CONNECTION_STRING'] = os.getenv(
        'POSTGRES_CONNECTION_STRING',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    # 실행
    asyncio.run(init_knowledge_base())