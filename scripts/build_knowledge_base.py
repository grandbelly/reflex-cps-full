"""
지식베이스 구축 스크립트
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 환경 변수 로드
def load_env():
    env_path = project_root / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

from ksys_app.ai_engine.knowledge_builder import build_knowledge_base


async def main():
    """지식베이스 구축 실행"""
    print("🚀 AI 지식베이스 구축을 시작합니다...")
    
    try:
        count = await build_knowledge_base()
        print(f"✅ 지식베이스 구축 완료! {count}개 항목이 추가되었습니다.")
        
    except Exception as e:
        print(f"❌ 지식베이스 구축 실패: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)