#!/usr/bin/env python3
"""
데이터베이스 연결 테스트 스크립트
"""

import asyncio
import os
import sys
from pathlib import Path

# Windows asyncio 이벤트 루프 문제 해결
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        # 환경변수 설정
        if not os.getenv("TS_DSN"):
            print("🔧 TS_DSN 환경변수 설정 중...")
            os.environ["TS_DSN"] = "postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable"
            print(f"✅ TS_DSN 설정됨: {os.environ['TS_DSN']}")
        
        print("🔍 데이터베이스 연결 테스트 중...")
        
        # db 모듈 import 시도
        try:
            from ksys_app.db import q
            print("✅ ksys_app.db 모듈 import 성공")
        except Exception as e:
            print(f"❌ ksys_app.db 모듈 import 실패: {e}")
            return False
        
        # 간단한 쿼리 실행
        try:
            result = await q("SELECT version()", ())
            print(f"✅ 데이터베이스 연결 성공!")
            print(f"   PostgreSQL 버전: {result[0]['version'][:50]}...")
            return True
        except Exception as e:
            print(f"❌ 데이터베이스 쿼리 실행 실패: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 연결 테스트 실패: {e}")
        return False

async def main():
    """메인 함수"""
    print("🚀 데이터베이스 연결 테스트 시작!")
    print("=" * 50)
    
    success = await test_connection()
    
    if success:
        print("\n🎉 데이터베이스 연결이 성공했습니다!")
        print("pg_vector 업그레이드를 진행할 수 있습니다.")
    else:
        print("\n❌ 데이터베이스 연결에 실패했습니다.")
        print("연결 문제를 해결한 후 다시 시도해주세요.")

if __name__ == "__main__":
    asyncio.run(main())

