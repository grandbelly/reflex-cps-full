#!/usr/bin/env python3
"""
네트워크 환경 전환 도구
Usage: python switch_network.py [local|remote]
"""

import sys
import re

# 네트워크 설정
NETWORK_CONFIGS = {
    'local': {
        'host': '192.168.100.29',
        'description': 'Local network (192.168.100.29)'
    },
    'remote': {
        'host': '192.168.1.80',
        'description': 'Remote network (192.168.1.80)'
    }
}

def switch_network(env_type='local'):
    """네트워크 환경 전환"""
    
    if env_type not in NETWORK_CONFIGS:
        print(f"[ERROR] Invalid environment: {env_type}")
        print("   Available options: local, remote")
        return False
    
    config = NETWORK_CONFIGS[env_type]
    host = config['host']
    
    print(f"[SWITCH] Switching to {config['description']}...")
    
    # .env 파일 읽기
    with open('.env', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # IP 주소 패턴
    ip_pattern = r'192\.168\.\d+\.\d+'
    
    # DB_HOST_TYPE 업데이트
    content = re.sub(r'DB_HOST_TYPE=.*', f'DB_HOST_TYPE={env_type}', content)
    
    # DB_HOST 업데이트
    content = re.sub(r'DB_HOST=.*', f'DB_HOST={host}', content)
    
    # 모든 IP 주소 변경
    content = re.sub(ip_pattern, host, content)
    
    # .env 파일 쓰기
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Network switched to {env_type} ({host})")
    print("\n[INFO] Updated configurations:")
    print(f"   - DB_HOST_TYPE={env_type}")
    print(f"   - DB_HOST={host}")
    print(f"   - TimescaleDB: postgresql://postgres:admin@{host}:5432/EcoAnP")
    print(f"   - InfluxDB: http://{host}:8086")
    print("\n[WARNING] Please restart the Docker container:")
    print("   docker restart reflex-ksys-app")
    
    return True

def show_current():
    """현재 설정 표시"""
    with open('.env', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 현재 호스트 찾기
    match = re.search(r'DB_HOST=(.*)', content)
    if match:
        current_host = match.group(1).strip()
        
        # 어떤 환경인지 확인
        current_env = 'unknown'
        for env, config in NETWORK_CONFIGS.items():
            if config['host'] == current_host:
                current_env = env
                break
        
        print(f"[CURRENT] Network configuration:")
        print(f"   - Environment: {current_env}")
        print(f"   - Host: {current_host}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_current()
        print("\n[USAGE] python switch_network.py [local|remote]")
        print("   local  - Use local network (192.168.100.29)")
        print("   remote - Use remote network (192.168.1.80)")
    else:
        env_type = sys.argv[1].lower()
        switch_network(env_type)