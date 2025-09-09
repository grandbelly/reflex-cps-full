#!/bin/bash

# =====================================================
# EcoAnP Node-RED 간단 중지 스크립트
# =====================================================

echo "🛑 Node-RED 중지 중..."

# Node-RED 컨테이너 중지 및 제거
docker stop nodered_host 2>/dev/null || echo "⚠️ nodered_host 컨테이너가 실행 중이 아닙니다."
docker rm nodered_host 2>/dev/null || echo "⚠️ nodered_host 컨테이너가 존재하지 않습니다."

echo "✅ Node-RED가 중지되었습니다."

# 남은 컨테이너 확인
echo "📊 실행 중인 컨테이너:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -v "NAMES" || echo "실행 중인 컨테이너가 없습니다."

