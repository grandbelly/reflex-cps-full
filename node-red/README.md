# EcoAnP Node-RED

**EcoAnP 프로젝트의 Node-RED 데이터 수집 시스템**

## 🚀 빠른 시작

### 라즈베리파이 (Linux)
```bash
# 간단한 방식 (기존 구성 개선)
./simple-start-node-red.sh

# 또는 Docker Compose 방식 (고급)
./start-node-red.sh
```

### Windows
```powershell
# PowerShell에서 실행
.\start-node-red.ps1
```

## 📁 파일 구조

### 실행 스크립트
- **`simple-start-node-red.sh`**: 기존 방식 개선 (Linux)
- **`start-node-red.ps1`**: Windows용 실행 스크립트
- **`start-node-red.sh`**: Docker Compose 방식 (고급)

### 설정 파일
- **`docker-compose.node-red.yml`**: Docker Compose 구성
- **`settings/settings.js`**: Node-RED 설정
- **`flows/flows.json`**: 기본 데이터 브릿지 플로우

## 🔗 접속 정보

- **Node-RED 웹**: http://localhost:1880
- **사용자명**: admin
- **비밀번호**: password

## 🔧 필수 노드 설치

Node-RED 관리 패널에서 설치:
```
node-red-contrib-postgresql
node-red-contrib-influxdb
node-red-dashboard
```

## 🎯 TimescaleDB 연결

**연결 설정**:
- **호스트**: `host.docker.internal` (Windows/Mac) 또는 `localhost` (Linux)
- **포트**: `5433`
- **데이터베이스**: `EcoAnP`
- **사용자**: `postgres`
- **비밀번호**: `admin`

## 📊 데이터 플로우

```
[센서 데이터] → [Node-RED] → [InfluxDB] → [Node-RED 브릿지] → [TimescaleDB] → [Reflex 대시보드]
```

## 🛑 중지

### Linux
```bash
./simple-stop-node-red.sh
```

### Windows
```powershell
.\stop-node-red.ps1
```

## 📋 문제 해결

### 컨테이너 로그 확인
```bash
docker logs nodered_host
```

### 포트 충돌
- 기본 포트 1880이 사용 중인 경우 스크립트를 수정하여 다른 포트 사용

### 권한 문제 (Linux)
```bash
sudo chown -R 1000:1000 /home/$(whoami)/node-red/data
```

