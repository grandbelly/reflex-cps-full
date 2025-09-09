# 읽기 전용 환경 설정 가이드

## 🎯 목적
다른 PC에서 안전하게 코드를 가져와서 테스트만 실행

## 🚀 초기 설정 (한 번만)

### 1. 저장소 클론
```bash
git clone https://github.com/grandbelly/reflex-ksys.git
cd reflex-ksys
```

### 2. 가상환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt
pip install python-dotenv pytest
```

### 3. 환경변수 설정
```bash
# 환경설정 파일 복사
cp .env.example .env

# .env 파일 수정 (각 PC의 DB 설정)
# TS_DSN=postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable
```

## 📋 일상 루틴 (매번 실행)

### 1. 최신 코드 가져오기
```bash
# 작업 디렉터리로 이동
cd reflex-ksys

# 가상환경 활성화
source venv/bin/activate

# 최신 변경사항 가져오기
git pull origin main
```

### 2. 동기화 상태 확인
```bash
# 동기화 스크립트 실행
./scripts/sync_check.sh
```

### 3. 테스트 실행
```bash
# 모든 테스트 실행
python -m pytest tests/ -v

# 특정 테스트만 실행
python -m pytest tests/test_kpi_calculations.py -v
python -m pytest tests/test_database_integration.py -v
python -m pytest tests/test_security_isolated.py -v
```

### 4. 애플리케이션 실행 (선택사항)
```bash
# 보안 검증 테스트
python ksys_app/security.py

# Reflex 앱 실행 (테스트용)
reflex run --env dev
```

## 🛡️ 안전 수칙

### ✅ **해도 되는 것**
- `git pull` - 최신 코드 가져오기
- `git status` - 상태 확인
- `git log` - 커밋 히스토리 보기
- 테스트 실행
- 로컬에서 코드 수정해서 테스트 (푸시 안함)

### ❌ **하지 말 것**
- `git push` - 변경사항 업로드
- `git commit` - 변경사항 커밋
- `git add` - 파일 스테이징
- `.env` 파일 수정 후 커밋

## 🔧 유용한 스크립트

### 빠른 테스트 스크립트
```bash
# scripts/quick_test.sh 생성
cat > scripts/quick_test.sh << 'EOF'
#!/bin/bash
echo "🚀 빠른 테스트 시작..."

# 가상환경 활성화 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  가상환경을 먼저 활성화하세요: source venv/bin/activate"
    exit 1
fi

# 최신 코드 가져오기
echo "📥 최신 코드 가져오는 중..."
git pull origin main

# 보안 검증
echo "🛡️  보안 검증 중..."
python ksys_app/security.py

# 테스트 실행
echo "🧪 테스트 실행 중..."
python -m pytest tests/ -v --tb=short

echo "✅ 테스트 완료!"
EOF

chmod +x scripts/quick_test.sh
```

### 환경 체크 스크립트
```bash
# scripts/env_check.sh 생성
cat > scripts/env_check.sh << 'EOF'
#!/bin/bash
echo "🔍 환경 설정 확인..."

# Python 버전 확인
echo "🐍 Python: $(python --version)"

# 가상환경 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ 가상환경이 활성화되지 않음"
    echo "   실행: source venv/bin/activate"
else
    echo "✅ 가상환경: $VIRTUAL_ENV"
fi

# 핵심 패키지 확인
echo "📦 패키지 확인:"
python -c "
try:
    import reflex; print('✅ Reflex:', reflex.__version__)
except: print('❌ Reflex 없음')

try:
    import psycopg; print('✅ psycopg 설치됨')
except: print('❌ psycopg 없음')

try:
    import pytest; print('✅ pytest 설치됨')
except: print('❌ pytest 없음')
"

# 환경변수 확인
if [ -f ".env" ]; then
    echo "✅ .env 파일 존재"
else
    echo "❌ .env 파일 없음"
    echo "   실행: cp .env.example .env"
fi

# DB 연결 테스트
echo "🗄️  DB 연결 테스트:"
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
dsn = os.getenv('TS_DSN')
if dsn:
    print('✅ TS_DSN 설정됨')
    try:
        import psycopg
        conn = psycopg.connect(dsn, connect_timeout=3)
        print('✅ DB 연결 성공')
        conn.close()
    except Exception as e:
        print(f'❌ DB 연결 실패: {e}')
else:
    print('❌ TS_DSN 환경변수 없음')
"
EOF

chmod +x scripts/env_check.sh
```

## 📱 사용법 요약

### 매일 시작할 때
```bash
# 1. 프로젝트 디렉터리로 이동
cd reflex-ksys

# 2. 가상환경 활성화
source venv/bin/activate

# 3. 환경 체크
./scripts/env_check.sh

# 4. 빠른 테스트
./scripts/quick_test.sh
```

### 새로운 변경사항 확인할 때
```bash
# 동기화 상태 확인
./scripts/sync_check.sh

# 최신 코드 가져오기
git pull origin main

# 테스트 재실행
python -m pytest tests/ -v
```

## 🎯 테스트 시나리오

### 1. 기본 기능 테스트
```bash
# KPI 계산 로직 테스트
python -m pytest tests/test_kpi_calculations.py::TestKPICalculations::test_gauge_pct_with_qc_rule -v

# 데이터베이스 연결 테스트  
python -m pytest tests/test_database_integration.py::TestDatabaseIntegration::test_database_connection -v
```

### 2. 성능 테스트
```bash
# 쿼리 성능 테스트
python -m pytest tests/test_database_integration.py::TestDatabaseIntegration::test_query_performance -v -s
```

### 3. 보안 테스트
```bash
# 보안 기능 테스트
python -m pytest tests/test_security_isolated.py -v
```

## 🚨 문제 발생시 해결법

### Git 관련 문제
```bash
# 로컬 변경사항 무시하고 최신 코드로 리셋
git fetch origin
git reset --hard origin/main

# 가상환경 재생성
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 테스트 실패시
```bash
# 상세한 오류 정보 확인
python -m pytest tests/ -v -s --tb=long

# 특정 테스트만 실행해서 디버깅
python -m pytest tests/test_database_integration.py::TestDatabaseIntegration::test_database_connection -v -s
```

## 💡 팁

1. **북마크 추가**: 자주 사용하는 명령어를 bash alias로 등록
2. **로그 확인**: 테스트 실패시 상세 로그 분석
3. **환경 분리**: 각 PC별로 다른 .env 설정 유지
4. **정기 업데이트**: 하루 1-2회 pull 실행

이 방법으로 안전하게 코드를 테스트하고 검증할 수 있습니다! 🎯