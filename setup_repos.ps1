# PowerShell script to setup Full and Part repositories

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setting up Full and Part repositories" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$baseDir = "C:\reflex"
$sourceDir = "C:\reflex\reflex-ksys-refactor"

# Full Version Setup
Write-Host "`n[1/2] Setting up Full version..." -ForegroundColor Green
$fullDir = "$baseDir\reflex-cps-full"

if (Test-Path $fullDir) {
    Remove-Item -Recurse -Force $fullDir
}

New-Item -ItemType Directory -Path $fullDir | Out-Null
Set-Location $fullDir

# Initialize git and set remote
git init
git remote add origin https://github.com/grandbelly/reflex-cps-full.git

# Copy all files for Full version
Write-Host "Copying Full version files..." -ForegroundColor Yellow
$excludeDirs = @(".git", ".web", "__pycache__", "dagster\dagster_home", "nul")

Get-ChildItem -Path $sourceDir -Recurse | Where-Object {
    $relativePath = $_.FullName.Substring($sourceDir.Length + 1)
    $shouldInclude = $true
    
    foreach ($exclude in $excludeDirs) {
        if ($relativePath -like "$exclude*") {
            $shouldInclude = $false
            break
        }
    }
    
    if ($shouldInclude -and -not $_.PSIsContainer) {
        $destinationPath = Join-Path $fullDir $relativePath
        $destinationDir = Split-Path $destinationPath -Parent
        
        if (-not (Test-Path $destinationDir)) {
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        
        Copy-Item $_.FullName -Destination $destinationPath -Force
    }
}

# Part Version Setup
Write-Host "`n[2/2] Setting up Part version..." -ForegroundColor Green
$partDir = "$baseDir\reflex-ksys-lite"

if (Test-Path $partDir) {
    Remove-Item -Recurse -Force $partDir
}

New-Item -ItemType Directory -Path $partDir | Out-Null
Set-Location $partDir

# Initialize git and set remote
git init
git remote add origin https://github.com/grandbelly/reflex-ksys-lite.git

# Copy files for Part version (excluding AI/ML)
Write-Host "Copying Part version files (excluding AI/ML)..." -ForegroundColor Yellow
$excludeDirs = @(".git", ".web", "__pycache__", "dagster", "ksys_app\ai_engine", "ksys_app\ml", "nul")

Get-ChildItem -Path $sourceDir -Recurse | Where-Object {
    $relativePath = $_.FullName.Substring($sourceDir.Length + 1)
    $shouldInclude = $true
    
    foreach ($exclude in $excludeDirs) {
        if ($relativePath -like "$exclude*") {
            $shouldInclude = $false
            break
        }
    }
    
    # Also exclude AI-related component files
    if ($relativePath -like "*\ai_*") {
        $shouldInclude = $false
    }
    
    if ($shouldInclude -and -not $_.PSIsContainer) {
        $destinationPath = Join-Path $partDir $relativePath
        $destinationDir = Split-Path $destinationPath -Parent
        
        if (-not (Test-Path $destinationDir)) {
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        
        Copy-Item $_.FullName -Destination $destinationPath -Force
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Setup complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. cd C:\reflex\reflex-cps-full" -ForegroundColor White
Write-Host "   git add ." -ForegroundColor White
Write-Host "   git commit -m 'Initial commit: Full version with AI/ML'" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host "`n2. cd C:\reflex\reflex-ksys-lite" -ForegroundColor White
Write-Host "   git add ." -ForegroundColor White
Write-Host "   git commit -m 'Initial commit: Lightweight version for Raspberry Pi'" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White