"""
보안 설정 초기화 스크립트
TASK_003: API 키를 안전하게 저장
"""

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from ksys_app.utils.secure_config import SecureConfig, APIKeyManager


def setup_secure_api_keys():
    """API 키 보안 설정"""
    
    print("=" * 50)
    print("API Key Security Setup Wizard")
    print("=" * 50)
    
    secure_config = SecureConfig()
    
    # 기존 .env 파일에서 읽기
    env_path = Path(__file__).parent.parent.parent / '.env'
    current_keys = {}
    
    if env_path.exists():
        print(f"\n[INFO] .env file found: {env_path}")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    current_keys[key] = value
    
    # OpenAI API 키 처리
    if 'OPENAI_API_KEY' in current_keys:
        openai_key = current_keys['OPENAI_API_KEY']
        if openai_key.startswith('sk-'):
            print(f"\n[OK] OpenAI API key found")
            print(f"   현재 키: {openai_key[:10]}...{openai_key[-4:]}")
            
            response = input("이 키를 암호화하여 저장하시겠습니까? (y/n): ")
            if response.lower() == 'y':
                secure_config.rotate_api_key('OPENAI_API_KEY', openai_key)
                print("   [OK] OpenAI API key encrypted and saved.")
                
                # .env 파일에서 마스킹
                current_keys['OPENAI_API_KEY'] = 'ENCRYPTED_SEE_SECURE_CONFIG'
    
    # InfluxDB 토큰 처리  
    if 'INFLUX_TOKEN' in current_keys:
        influx_token = current_keys['INFLUX_TOKEN']
        if len(influx_token) > 20:
            print(f"\n[OK] InfluxDB token found")
            print(f"   현재 토큰: {influx_token[:10]}...{influx_token[-4:]}")
            
            response = input("이 토큰을 암호화하여 저장하시겠습니까? (y/n): ")
            if response.lower() == 'y':
                secure_config.rotate_api_key('INFLUX_TOKEN', influx_token)
                print("   [OK] InfluxDB token encrypted and saved.")
                
                # .env 파일에서 마스킹
                current_keys['INFLUX_TOKEN'] = 'ENCRYPTED_SEE_SECURE_CONFIG'
    
    # .env 파일 업데이트
    update_env = input("\n.env 파일을 업데이트하시겠습니까? (민감한 키를 마스킹) (y/n): ")
    if update_env.lower() == 'y':
        # 백업 생성
        backup_path = env_path.with_suffix('.env.backup')
        with open(env_path, 'r') as f:
            backup_content = f.read()
        with open(backup_path, 'w') as f:
            f.write(backup_content)
        print(f"   [BACKUP] Created: {backup_path}")
        
        # 새 .env 작성
        with open(env_path, 'w') as f:
            f.write("# Ksys Dashboard Environment Variables\n\n")
            f.write("# TimescaleDB Connection\n")
            f.write(f"TS_DSN={current_keys.get('TS_DSN', '')}\n")
            f.write(f"POSTGRES_CONNECTION_STRING={current_keys.get('POSTGRES_CONNECTION_STRING', '')}\n\n")
            f.write("# Application Environment\n")
            f.write(f"APP_ENV={current_keys.get('APP_ENV', 'development')}\n")
            f.write(f"TZ={current_keys.get('TZ', 'Asia/Seoul')}\n\n")
            f.write("# API Keys (Encrypted - See secure_config)\n")
            f.write("# OPENAI_API_KEY=ENCRYPTED_SEE_SECURE_CONFIG\n")
            f.write("# INFLUX_TOKEN=ENCRYPTED_SEE_SECURE_CONFIG\n\n")
            f.write("# Original keys have been moved to secure storage\n")
            f.write("# Location: ~/.ksys/secure_config.enc\n")
        
        print("   [OK] .env file updated.")
    
    # 상태 확인
    print("\n" + "=" * 50)
    print("Final Status")
    print("=" * 50)
    
    api_manager = APIKeyManager()
    print(api_manager.get_status_report())
    
    print("\nUsage:")
    print("from ksys_app.utils.secure_config import get_api_key_manager")
    print("api_manager = get_api_key_manager()")
    print("openai_key = api_manager.get_openai_key()")
    
    print("\n[SUCCESS] Security setup completed!")


if __name__ == "__main__":
    try:
        setup_secure_api_keys()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Setup cancelled.")
    except Exception as e:
        print(f"\n[ERROR] Error occurred: {e}")
        import traceback
        traceback.print_exc()