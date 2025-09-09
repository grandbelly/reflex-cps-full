"""
API 키 교체 스크립트
TASK_003: 새 API 키 발급 및 암호화
"""

import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key

# 암호화 키 생성 또는 로드
KEY_FILE = Path(__file__).parent / '.encryption_key'

def get_or_create_key():
    """암호화 키 가져오기 또는 생성"""
    if KEY_FILE.exists():
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        print(f"[NEW] 암호화 키 생성: {KEY_FILE}")
        return key

def encrypt_api_key(api_key: str) -> str:
    """API 키 암호화"""
    key = get_or_create_key()
    cipher = Fernet(key)
    encrypted = cipher.encrypt(api_key.encode())
    return encrypted.decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """API 키 복호화"""
    key = get_or_create_key()
    cipher = Fernet(key)
    decrypted = cipher.decrypt(encrypted_key.encode())
    return decrypted.decode()

def rotate_api_key():
    """API 키 교체 프로세스"""
    print("=" * 60)
    print("API 키 보안 처리")
    print("=" * 60)
    
    # .env 파일 경로
    env_path = Path(__file__).parent.parent.parent / '.env'
    
    # 현재 API 키 읽기
    load_dotenv(env_path)
    current_key = os.getenv('OPENAI_API_KEY')
    
    if current_key and current_key.startswith('sk-'):
        print("[WARN] 평문 API 키 감지됨!")
        print("[INFO] 암호화 진행 중...")
        
        # API 키 암호화
        encrypted = encrypt_api_key(current_key)
        
        # .env.encrypted 파일에 저장
        encrypted_env = env_path.parent / '.env.encrypted'
        set_key(encrypted_env, 'OPENAI_API_KEY_ENCRYPTED', encrypted)
        
        # 원본 .env에서 API 키 제거 (주석 처리)
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        with open(env_path, 'w') as f:
            for line in lines:
                if line.startswith('OPENAI_API_KEY='):
                    f.write(f"# {line}")  # 주석 처리
                    f.write("# API 키는 .env.encrypted에 암호화되어 저장됨\n")
                else:
                    f.write(line)
        
        print(f"[OK] API 키 암호화 완료")
        print(f"[OK] 암호화된 키: {encrypted_env}")
        print(f"[OK] 암호화 키 파일: {KEY_FILE}")
        
        # 테스트: 복호화 확인
        test_decrypt = decrypt_api_key(encrypted)
        if test_decrypt == current_key:
            print("[OK] 복호화 테스트 성공")
        else:
            print("[ERROR] 복호화 테스트 실패")
        
        # 보안 경고
        print("\n[SECURITY] 중요 보안 사항:")
        print("1. .encryption_key 파일을 안전하게 보관하세요")
        print("2. .env.encrypted 파일도 .gitignore에 추가하세요")
        print("3. 실제 운영 환경에서는 키 관리 서비스 사용을 권장합니다")
        
    else:
        print("[INFO] 이미 보안 처리됨 또는 API 키 없음")
    
    print("\n" + "=" * 60)
    print("작업 완료")
    print("=" * 60)

if __name__ == "__main__":
    rotate_api_key()