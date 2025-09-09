# Reflex-KSYS-Refactor Docker 배포 가이드

## 개요
로컬에서 코드 변경 후 라즈베리파이 원격 서버에 Docker로 배포하는 전체 과정을 정리한 문서입니다.

## 환경 정보
- **원격 서버**: 192.168.1.80 (라즈베리파이)
- **사용자**: tion
- **프로젝트 경로**: `/home/tion/reflex-ksys-refactor`
- **포트**: 
  - Frontend: 13000
  - Backend: 13001
- **GitHub 저장소**: grandbelly/reflex-ksys-refactor (clean-branch)

## 1단계: SSH 원격 접속
```bash
ssh tion@192.168.1.80
```

## 2단계: 프로젝트 디렉터리로 이동
```bash
cd reflex-ksys-refactor
```

## 3단계: GitHub에서 최신 코드 Pull
```bash
# 현재 브랜치 확인
git branch

# 최신 코드 가져오기
git pull origin clean-branch

# 변경사항 확인
git log --oneline -5
```

## 4단계: Docker 컨테이너 및 이미지 정리
```bash
# 기존 컨테이너 강제 제거 (실행 중이어도 제거)
docker rm -f reflex-ksys-container 2>/dev/null

# 기존 이미지 제거 (선택사항)
# docker rmi reflex-ksys-app 2>/dev/null
```

## 5단계: Docker 이미지 빌드
```bash
docker build -t reflex-ksys-app .
```

## 6단계: Docker 컨테이너 실행
```bash
docker run -d -p 13000:13000 -p 13001:13001 --name reflex-ksys-container reflex-ksys-app
```

## 7단계: 배포 확인
```bash
# 컨테이너 상태 확인
docker ps | grep reflex

# 로그 확인
docker logs --tail 20 reflex-ksys-container

# 포트 확인
sudo netstat -tlnp | grep -E ':(13000|13001)'
```

## 전체 과정 한 번에 실행하는 스크립트
```bash
#!/bin/bash
# deploy.sh

echo "=== Reflex KSYS 배포 시작 ==="

# 1. 프로젝트 디렉터리로 이동
cd /home/tion/reflex-ksys-refactor

# 2. 최신 코드 pull
echo "📥 GitHub에서 최신 코드 가져오는 중..."
git pull origin clean-branch

# 3. 기존 컨테이너 제거
echo "🗑️ 기존 컨테이너 제거 중..."
docker rm -f reflex-ksys-container 2>/dev/null

# 4. 새 이미지 빌드
echo "🔨 Docker 이미지 빌드 중..."
docker build -t reflex-ksys-app .

# 5. 새 컨테이너 실행
echo "🚀 컨테이너 실행 중..."
docker run -d -p 13000:13000 -p 13001:13001 --name reflex-ksys-container reflex-ksys-app

# 6. 상태 확인
echo "✅ 배포 완료! 상태 확인:"
docker ps | grep reflex
echo "📋 최근 로그:"
docker logs --tail 10 reflex-ksys-container

echo "🌐 접속 URL: http://192.168.1.80:13000"
```

## 스크립트 사용법
```bash
# 스크립트 생성
cat > deploy.sh << 'SCRIPT_EOF'
# [위 스크립트 내용 복사]
SCRIPT_EOF

# 실행 권한 부여
chmod +x deploy.sh

# 배포 실행
./deploy.sh
```

## 접속 정보
- **Frontend**: http://192.168.1.80:13000
- **Backend**: http://192.168.1.80:13001

## 트러블슈팅

### 포트 충돌 시
```bash
# 사용 중인 포트 확인
sudo netstat -tlnp | grep -E ':(13000|13001)'

# 프로세스 종료
sudo kill <PID>
```

### 컨테이너 로그 확인
```bash
# 실시간 로그 보기
docker logs -f reflex-ksys-container

# 에러 로그만 보기
docker logs reflex-ksys-container 2>&1 | grep -i error
```

### Docker 용량 정리
```bash
# 사용하지 않는 이미지 제거
docker image prune

# 모든 정지된 컨테이너 제거
docker container prune
```

## 주의사항
1. 포트 13000, 13001이 다른 서비스와 충돌하지 않도록 확인
2. Portainer는 8001:8000 포트를 사용하므로 충돌 방지됨
3. 배포 전 로컬에서 테스트 완료 후 진행
4. 중요한 변경사항은 별도 브랜치에서 테스트 후 clean-branch에 merge

## 현재 설정 파일들

### rxconfig.py
```python
import reflex as rx

config = rx.Config(
    app_name="ksys_app",
    frontend_packages=[],
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    frontend_port=13000,
    backend_port=13001,
)
```

### requirements.txt
```
reflex==0.8.6
psycopg[binary,pool]>=3.1
pydantic>=2.6
cachetools>=5
reflex_chakra
```
