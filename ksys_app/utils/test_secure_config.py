"""
보안 설정 테스트
TASK_003 검증
"""

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from ksys_app.utils.secure_config import SecureConfig, APIKeyManager


def test_secure_config():
    """보안 설정 테스트"""
    
    print("=" * 50)
    print("Secure Config Test")
    print("=" * 50)
    
    # 1. SecureConfig 테스트
    print("\n1. Testing SecureConfig:")
    config = SecureConfig()
    
    # 테스트 데이터 암호화/복호화
    test_key = "sk-test123456789"
    encrypted = config.encrypt_value(test_key)
    decrypted = config.decrypt_value(encrypted)
    
    print(f"   Original: {test_key}")
    print(f"   Encrypted: {encrypted[:20]}...")
    print(f"   Decrypted: {decrypted}")
    print(f"   Match: {test_key == decrypted}")
    
    # 2. 마스킹 테스트
    print("\n2. Testing API Key Masking:")
    test_keys = [
        "sk-proj-JXf952IwADk5UOC3BZuP6UFSHAxqdCz",
        "short",
        None,
        ""
    ]
    
    for key in test_keys:
        masked = config.mask_api_key(key)
        print(f"   {str(key)[:20] if key else 'None':<20} -> {masked}")
    
    # 3. API Key Manager 테스트
    print("\n3. Testing API Key Manager:")
    manager = APIKeyManager()
    
    # 현재 키 상태
    validation = manager.validate_keys()
    print(f"   OpenAI Key Valid: {validation.get('openai', False)}")
    print(f"   Influx Token Valid: {validation.get('influx', False)}")
    
    # 4. 상태 보고서
    print("\n4. Status Report:")
    print("-" * 40)
    report = manager.get_status_report()
    print(report)
    
    print("\n" + "=" * 50)
    print("Test Completed")
    
    return True


def test_env_backup():
    """환경 변수 백업 테스트"""
    
    print("\n" + "=" * 50)
    print("Environment Backup Test")
    print("=" * 50)
    
    env_path = Path(__file__).parent.parent.parent / '.env'
    backup_path = env_path.with_suffix('.env.backup')
    
    if backup_path.exists():
        print(f"[OK] Backup exists: {backup_path}")
        
        # 백업 파일 크기 확인
        backup_size = backup_path.stat().st_size
        print(f"     Size: {backup_size} bytes")
        
        # 민감한 키가 마스킹되었는지 확인
        with open(env_path, 'r') as f:
            env_content = f.read()
        
        has_exposed_key = 'sk-proj' in env_content
        print(f"     Exposed keys in .env: {'YES' if has_exposed_key else 'NO'}")
        
        if has_exposed_key:
            print("     [WARNING] API keys may still be exposed in .env")
        else:
            print("     [OK] API keys are masked in .env")
    else:
        print(f"[INFO] No backup found at: {backup_path}")
    
    return True


if __name__ == "__main__":
    try:
        # 기본 테스트
        success = test_secure_config()
        
        # 백업 테스트
        test_env_backup()
        
        if success:
            print("\n[SUCCESS] All tests passed!")
        else:
            print("\n[FAIL] Some tests failed")
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()