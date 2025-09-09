# =====================================================
# EcoAnP Node-RED Windows 중지 스크립트
# =====================================================

Write-Host "🛑 Node-RED 중지 중..." -ForegroundColor Yellow

# Node-RED 컨테이너 중지 및 제거
$stopResult = docker stop nodered_host 2>$null
$removeResult = docker rm nodered_host 2>$null

if ($stopResult -eq "nodered_host") {
    Write-Host "✅ Node-RED가 중지되었습니다." -ForegroundColor Green
} else {
    Write-Host "⚠️ nodered_host 컨테이너가 실행 중이 아니었습니다." -ForegroundColor Yellow
}

# 남은 컨테이너 확인
Write-Host ""
Write-Host "📊 실행 중인 컨테이너:" -ForegroundColor Blue
$containers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
if ($containers) {
    $containers
} else {
    Write-Host "실행 중인 컨테이너가 없습니다." -ForegroundColor Gray
}

