#!/bin/bash

# =====================================================
# EcoAnP Node-RED 시작 스크립트 (라즈베리파이용)
# =====================================================

echo "🔄 EcoAnP Node-RED 시작 중..."

# 디렉토리 권한 설정
echo "📁 디렉토리 권한 설정 중..."
chmod -R 755 data flows settings nodes projects
chmod -R 755 influxdb

# Docker Compose로 서비스 시작
echo "🐳 Docker 서비스 시작 중..."
docker-compose -f docker-compose.node-red.yml up -d

# 서비스 상태 확인
echo "✅ 서비스 상태 확인 중..."
sleep 10

# Node-RED 상태 확인
if curl -f http://localhost:1880/ > /dev/null 2>&1; then
    echo "🎉 Node-RED가 성공적으로 시작되었습니다!"
    echo "🌐 웹 인터페이스: http://localhost:1880"
    echo "👤 사용자명: admin"
    echo "🔐 비밀번호: password"
else
    echo "❌ Node-RED 시작 실패"
fi

# InfluxDB 상태 확인
if curl -f http://localhost:8086/ping > /dev/null 2>&1; then
    echo "🎉 InfluxDB가 성공적으로 시작되었습니다!"
    echo "🌐 InfluxDB API: http://localhost:8086"
else
    echo "❌ InfluxDB 시작 실패"
fi

# 컨테이너 상태 표시
echo ""
echo "📊 실행 중인 컨테이너:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🎯 다음 단계:"
echo "1. Node-RED 웹 인터페이스에 접속 (http://localhost:1880)"
echo "2. PostgreSQL 노드 설치: node-red-contrib-postgresql"
echo "3. 데이터 브릿지 플로우 설정 확인"
echo "4. TimescaleDB 연결 테스트"

