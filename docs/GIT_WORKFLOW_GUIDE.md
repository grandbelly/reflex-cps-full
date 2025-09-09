# Git 워크플로우 가이드 - 멀티 PC 환경

## 🎯 목표
여러 PC에서 안전하고 효율적으로 협업하기

## 📋 기본 원칙

### 1. **작업 시작 전 항상 동기화**
```bash
# 작업 시작할 때마다 필수!
git fetch origin
git pull origin main
```

### 2. **기능별 브랜치 사용**
```bash
# 새 기능 작업시
git checkout -b feature/security-enhancement
git checkout -b fix/database-connection
git checkout -b docs/user-guide

# 작업 완료 후
git push origin feature/security-enhancement
```

### 3. **자주 커밋, 자주 푸시**
```bash
# 작은 단위로 자주 커밋
git add .
git commit -m "feat: 환경변수 검증 추가"
git push origin 브랜치명
```

## 🔄 권장 워크플로우

### A) 단순한 방법 (현재 방식 개선)
```bash
# 1. 작업 시작 전
git pull origin main

# 2. 작업 중 - 자주 저장
git add .
git commit -m "작업 내용"

# 3. 작업 완료 시
git pull origin main  # 혹시 다른 PC에서 변경사항 있는지 확인
git push origin main
```

### B) 안전한 방법 (브랜치 활용)
```bash
# PC A에서
git checkout -b feature/new-dashboard
# ... 작업 ...
git commit -m "대시보드 개선"
git push origin feature/new-dashboard

# PC B에서
git fetch origin
git checkout feature/new-dashboard
# ... 계속 작업 ...
git commit -m "대시보드 테스트 추가"
git push origin feature/new-dashboard

# 작업 완료 후 main에 병합
git checkout main
git pull origin main
git merge feature/new-dashboard
git push origin main
git branch -d feature/new-dashboard  # 브랜치 삭제
```

## ⚠️ 충돌 방지 전략

### 1. **파일별 역할 분담**
```
PC A (메인 개발): 
- ksys_app/ (핵심 코드)
- components/
- states/

PC B (문서/테스트):
- docs/
- tests/  
- README.md
- 설정 파일들
```

### 2. **시간대별 작업**
```
오전: PC A 작업
오후: PC B 작업
저녁: 통합 및 정리
```

### 3. **실시간 소통**
- 작업 시작/종료시 서로 알림
- 같은 파일 수정시 사전 조율

## 🚨 충돌 발생시 해결법

### 자동 병합 실패시
```bash
# 1. 현재 작업 임시 저장
git stash push -m "현재 작업 저장"

# 2. 최신 변경사항 가져오기
git pull origin main

# 3. 작업 복원 및 충돌 해결
git stash pop

# 4. 충돌 해결 후
git add .
git commit -m "충돌 해결: 변경사항 병합"
git push origin main
```

### 복잡한 충돌시
```bash
# 1. 백업 브랜치 생성
git checkout -b backup-$(date +%Y%m%d-%H%M)

# 2. main으로 돌아가서 최신화
git checkout main
git pull origin main

# 3. 변경사항을 새 브랜치로 적용
git checkout -b fix-conflicts
# 파일별로 수동 병합...
```

## 🛠️ 유용한 Git 명령어

### 상태 확인
```bash
git status                    # 현재 상태
git log --oneline -5          # 최근 5개 커밋
git diff                      # 변경사항 확인
git remote -v                 # 원격 저장소 확인
```

### 브랜치 관리
```bash
git branch -a                 # 모든 브랜치 확인
git checkout 브랜치명          # 브랜치 전환
git branch -d 브랜치명         # 브랜치 삭제
```

### 되돌리기
```bash
git reset --hard HEAD         # 모든 변경사항 취소
git reset --soft HEAD~1       # 마지막 커밋 취소 (변경사항 유지)
git checkout -- 파일명        # 특정 파일 변경사항 취소
```

## 📱 추천 도구

### Git GUI 도구
- **GitHub Desktop**: 초보자 친화적
- **SourceTree**: 고급 기능
- **VS Code Git**: 에디터 통합

### 모바일 알림
- GitHub 모바일 앱으로 푸시 알림 설정

## 🎯 프로젝트별 맞춤 전략

### Reflex-Ksys 프로젝트용
```bash
# 매일 작업 시작 루틴
git pull origin main
source venv/bin/activate
python -m pytest tests/ -v  # 테스트 먼저 실행

# 작업 완료 루틴  
python -m pytest tests/ -v  # 테스트 재실행
git add .
git commit -m "feat: 작업 내용"
git push origin main
```

### 환경별 설정
```bash
# .env 파일은 각 PC별로 다르게 관리
cp .env.example .env
# 각 PC에 맞는 설정값 입력

# .gitignore에 .env 추가 (이미 되어있음)
echo ".env" >> .gitignore
```

## 📋 체크리스트

### 작업 시작 전
- [ ] `git pull origin main` 실행
- [ ] 테스트 실행 확인
- [ ] 환경변수 설정 확인

### 작업 중
- [ ] 30분마다 커밋
- [ ] 의미있는 커밋 메시지 작성
- [ ] 테스트 추가/수정

### 작업 완료 후
- [ ] 전체 테스트 실행
- [ ] 코드 리뷰 (혼자라도 다시 확인)
- [ ] `git push origin main`
- [ ] 다른 PC에 작업 완료 알림

## 🚀 고급 전략 (나중에)

### Pull Request 활용
1. 브랜치에서 작업
2. GitHub에서 Pull Request 생성
3. 코드 리뷰 후 병합

### 자동화
```bash
# pre-commit 훅 설정
pip install pre-commit
pre-commit install

# 푸시 전 자동 테스트
echo "python -m pytest tests/" > .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

이 가이드를 따르면 충돌을 90% 이상 방지할 수 있습니다!