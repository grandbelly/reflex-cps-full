#!/bin/bash

# =====================================================
# EcoAnP Node-RED 중지 스크립트 (라즈베리파이용)
# =====================================================

echo "🛑 EcoAnP Node-RED 중지 중..."

# Docker Compose로 서비스 중지
docker-compose -f docker-compose.node-red.yml down

echo "✅ Node-RED 서비스가 중지되었습니다."

# 정리된 컨테이너 확인
echo "📊 남은 컨테이너:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(ecoanp_node_red|ecoanp_influxdb)" || echo "모든 Node-RED 관련 컨테이너가 중지되었습니다."

