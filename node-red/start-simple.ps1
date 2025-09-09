# =====================================================
# EcoAnP Node-RED 간단 실행 스크립트 (문제 해결용)
# =====================================================

Write-Host "🔄 Node-RED 간단 모드 시작 중..." -ForegroundColor Green

# 1. 기존 컨테이너 중지 및 제거
Write-Host "🛑 기존 컨테이너 정리 중..." -ForegroundColor Yellow
docker stop nodered_host 2>$null
docker rm nodered_host 2>$null

# 2. 간단한 Node-RED 컨테이너 실행 (권한 문제 방지)
Write-Host "🚀 Node-RED 간단 모드 시작 중..." -ForegroundColor Yellow
docker run -d `
  --name nodered_host `
  --restart=always `
  -p 1880:1880 `
  -e TZ=Asia/Seoul `
  -e NODE_RED_ENABLE_PROJECTS=false `
  nodered/node-red:latest

# 3. 상태 확인
Write-Host "✅ 상태 확인 중..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$container = docker ps --filter name=nodered_host --format "{{.Names}}"
if ($container -eq "nodered_host") {
    Write-Host "🎉 Node-RED가 성공적으로 시작되었습니다!" -ForegroundColor Green
    Write-Host "🌐 웹 인터페이스: http://localhost:1880" -ForegroundColor Cyan
    Write-Host "🔓 인증: 비활성화 (개발 모드)" -ForegroundColor Yellow
} else {
    Write-Host "❌ Node-RED 시작 실패" -ForegroundColor Red
    docker logs nodered_host
}

Write-Host ""
Write-Host "📊 실행 중인 Node-RED 컨테이너:" -ForegroundColor Blue
docker ps --filter name=nodered_host --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Green
Write-Host "1. Access http://localhost:1880 (no login required)"
Write-Host "2. Install PostgreSQL node: node-red-contrib-postgresql"
Write-Host "3. Test TimescaleDB connection with simple flow"
