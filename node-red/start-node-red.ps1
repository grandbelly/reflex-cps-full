# =====================================================
# EcoAnP Node-RED Windows 실행 스크립트
# =====================================================

Write-Host "🔄 EcoAnP Node-RED 시작 중..." -ForegroundColor Green

# 1. 디렉토리 생성
Write-Host "📁 디렉토리 생성 중..." -ForegroundColor Yellow
$nodeRedPath = "$env:USERPROFILE\node-red\data"
if (!(Test-Path $nodeRedPath)) {
    New-Item -ItemType Directory -Path $nodeRedPath -Force | Out-Null
}

# 2. 기존 컨테이너 중지 및 제거 (있다면)
Write-Host "🛑 기존 컨테이너 정리 중..." -ForegroundColor Yellow
docker stop nodered_host 2>$null
docker rm nodered_host 2>$null

# 3. Node-RED 컨테이너 실행
Write-Host "🚀 Node-RED 컨테이너 시작 중..." -ForegroundColor Yellow
docker run -d `
  --name nodered_host `
  --restart=always `
  -p 1880:1880 `
  -v "${nodeRedPath}:/data" `
  -v "${PWD}\settings\settings.js:/data/settings.js" `
  -v "${PWD}\flows\flows.json:/data/flows.json" `
  -e TZ=Asia/Seoul `
  -e NODE_RED_ENABLE_PROJECTS=true `
  nodered/node-red:latest

# 4. 상태 확인
Write-Host "✅ 상태 확인 중..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$container = docker ps --filter name=nodered_host --format "{{.Names}}"
if ($container -eq "nodered_host") {
    Write-Host "🎉 Node-RED가 성공적으로 시작되었습니다!" -ForegroundColor Green
    Write-Host "🌐 웹 인터페이스: http://localhost:1880" -ForegroundColor Cyan
} else {
    Write-Host "❌ Node-RED 시작 실패" -ForegroundColor Red
    docker logs nodered_host
}

Write-Host ""
Write-Host "📊 실행 중인 Node-RED 컨테이너:" -ForegroundColor Blue
docker ps --filter name=nodered_host --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host ""
Write-Host "🎯 다음 단계:" -ForegroundColor Green
Write-Host "1. Node-RED 웹 인터페이스에 접속 (http://localhost:1880)"
Write-Host "2. PostgreSQL 노드 설치: node-red-contrib-postgresql"
Write-Host "3. TimescaleDB 연결 설정 (host.docker.internal:5433)"
