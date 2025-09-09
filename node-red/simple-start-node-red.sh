#!/bin/bash

# =====================================================
# EcoAnP Node-RED 간단 실행 스크립트 (기존 방식 개선)
# =====================================================

echo "🔄 EcoAnP Node-RED 간단 실행 중..."

# 1. 디렉토리 생성
echo "📁 디렉토리 생성 중..."
sudo mkdir -p /home/$(whoami)/node-red/data
sudo chown -R 1000:1000 /home/$(whoami)/node-red/data

# 2. 기존 컨테이너 중지 및 제거 (있다면)
echo "🛑 기존 컨테이너 정리 중..."
docker stop nodered_host 2>/dev/null || true
docker rm nodered_host 2>/dev/null || true

# 3. Node-RED 컨테이너 실행
echo "🚀 Node-RED 컨테이너 시작 중..."
docker run -d \
  --name nodered_host \
  --restart=always \
  --network host \
  -v /home/$(whoami)/node-red/data:/data \
  -v $(pwd)/settings/settings.js:/data/settings.js \
  -v $(pwd)/flows/flows.json:/data/flows.json \
  -e TZ=Asia/Seoul \
  -e NODE_RED_ENABLE_PROJECTS=true \
  nodered/node-red:latest

# 4. 상태 확인
echo "✅ 상태 확인 중..."
sleep 5

if docker ps | grep -q nodered_host; then
    echo "🎉 Node-RED가 성공적으로 시작되었습니다!"
    echo "🌐 웹 인터페이스: http://localhost:1880"
    
    # 라즈베리파이 IP 자동 감지 시도
    RPI_IP=$(hostname -I | awk '{print $1}')
    if [ ! -z "$RPI_IP" ]; then
        echo "🥧 라즈베리파이 접속: http://$RPI_IP:1880"
    fi
else
    echo "❌ Node-RED 시작 실패"
    docker logs nodered_host
fi

echo ""
echo "📊 실행 중인 Node-RED 컨테이너:"
docker ps --filter name=nodered_host --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🎯 다음 단계:"
echo "1. Node-RED 웹 인터페이스에 접속"
echo "2. PostgreSQL 노드 설치: node-red-contrib-postgresql"
echo "3. TimescaleDB 연결 설정 (host.docker.internal:5433)"

