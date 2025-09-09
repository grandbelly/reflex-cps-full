# EcoAnP Node-RED 배포 가이드

## 🎯 개요

**EcoAnP 프로젝트의 Node-RED 데이터 수집 시스템**을 라즈베리파이에 배포하는 가이드입니다.

## 🏗️ 아키텍처

```
[센서 데이터] → [Node-RED] → [InfluxDB] → [Node-RED 브릿지] → [TimescaleDB] → [Reflex 대시보드]
```

## 📦 구성 요소

### 1. Node-RED (포트: 1880)
- **역할**: 데이터 수집, 변환, 라우팅
- **이미지**: `nodered/node-red:latest`
- **볼륨**: 설정, 플로우, 프로젝트 데이터 영속화

### 2. InfluxDB 1.8 (포트: 8086)
- **역할**: 기존 시계열 데이터 저장소
- **데이터베이스**: `iot_data`
- **사용자**: `admin/admin123`, `iot_user/iot_pass`

## 🚀 배포 단계

### 1. 라즈베리파이 준비
```bash
# Docker 설치 (라즈베리파이)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pi

# Docker Compose 설치
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

### 2. 프로젝트 복사
```bash
# 프로젝트 클론 또는 복사
scp -r ./node-red pi@raspberry-pi-ip:/home/pi/ecoanp-node-red
```

### 3. Node-RED 시작
```bash
cd /home/pi/ecoanp-node-red
chmod +x start-node-red.sh stop-node-red.sh
./start-node-red.sh
```

## 🔧 Node-RED 설정

### 1. 웹 인터페이스 접속
- **URL**: `http://라즈베리파이-IP:1880`
- **사용자명**: `admin`
- **비밀번호**: `password`

### 2. 필수 노드 설치
Node-RED 관리 패널에서 다음 노드들을 설치:
```
node-red-contrib-postgresql
node-red-contrib-influxdb
node-red-dashboard
node-red-contrib-moment
```

### 3. TimescaleDB 연결 설정
- **호스트**: `host.docker.internal` (로컬) 또는 `TimescaleDB-서버-IP`
- **포트**: `5433`
- **데이터베이스**: `EcoAnP`
- **사용자**: `postgres`
- **비밀번호**: `admin`

## 📊 데이터 플로우

### 기본 플로우 구성
1. **주기적 트리거** (5분마다)
2. **InfluxDB 쿼리** (최근 5분 데이터)
3. **데이터 변환** (InfluxDB → TimescaleDB 형식)
4. **TimescaleDB 삽입**
5. **로깅 및 모니터링**

### 커스텀 플로우 예제
```javascript
// InfluxDB 쿼리 함수 노드
const query = `
    SELECT * FROM iot_data 
    WHERE time > now() - 5m
    ORDER BY time DESC
`;

msg.payload = {
    query: query,
    database: 'iot_data'
};

return msg;
```

## 🔍 모니터링

### 1. 서비스 상태 확인
```bash
docker ps
docker logs ecoanp_node_red
docker logs ecoanp_influxdb
```

### 2. Node-RED 디버그
- Node-RED 웹 인터페이스의 디버그 탭 활용
- 로그 파일: `./data/node-red.log`

### 3. 데이터 검증
```sql
-- TimescaleDB에서 데이터 확인
SELECT COUNT(*) FROM influx_hist WHERE created_at > NOW() - INTERVAL '1 hour';
```

## 🛠️ 트러블슈팅

### Node-RED 접속 불가
```bash
# 컨테이너 재시작
docker restart ecoanp_node_red

# 포트 확인
netstat -tlnp | grep 1880
```

### InfluxDB 연결 오류
```bash
# InfluxDB 상태 확인
curl http://localhost:8086/ping

# 데이터베이스 생성 확인
curl -G http://localhost:8086/query --data-urlencode "q=SHOW DATABASES"
```

### TimescaleDB 연결 오류
- Docker 네트워크 확인
- 방화벽 설정 확인
- PostgreSQL 연결 문자열 검증

## 📈 성능 최적화

### 라즈베리파이 최적화
- **메모리 제한**: 512MB
- **CPU 제한**: 1.0 코어
- **데이터 배치 처리**: 5분 간격
- **로그 로테이션**: 5개 파일, 10MB 제한

### 네트워크 최적화
- **연결 풀링**: PostgreSQL 연결 재사용
- **배치 삽입**: 여러 레코드 한번에 처리
- **압축**: gzip 압축 활용

## 🔐 보안 설정

### 프로덕션 권장사항
1. **Node-RED 인증** 강화
2. **HTTPS** 활성화
3. **방화벽** 설정
4. **정기 업데이트**

### 설정 예제
```javascript
// settings.js - 강화된 보안
adminAuth: {
    type: "credentials",
    users: [{
        username: "admin",
        password: "$2b$08$강화된해시값",
        permissions: "*"
    }]
}
```

## 🔄 백업 및 복구

### 데이터 백업
```bash
# Node-RED 설정 백업
tar -czf node-red-backup-$(date +%Y%m%d).tar.gz data/ flows/ settings/

# InfluxDB 백업
docker exec ecoanp_influxdb influxd backup -database iot_data /backup/
```

### 복구 절차
```bash
# 설정 복구
tar -xzf node-red-backup-YYYYMMDD.tar.gz

# 서비스 재시작
./start-node-red.sh
```

## 📞 지원

문제 발생 시:
1. 로그 파일 확인
2. GitHub Issues 등록
3. 개발팀 연락

---

**마지막 업데이트**: 2025-09-03  
**버전**: 1.0.0

