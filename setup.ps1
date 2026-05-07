Set-Location -Path $PSScriptRoot

Write-Host "Setting up Robot Management System..." -ForegroundColor Cyan

$secretKey = ""
if (Get-Command python -ErrorAction SilentlyContinue) {
    $secretKey = python -c "import secrets; print(secrets.token_urlsafe(32))"
    Write-Host "Generated secret key using Python." -ForegroundColor Green
} else {
    $secretKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    Write-Host "Python not found, used fallback random string." -ForegroundColor Yellow
}

$envContent = @"
SECRET_KEY=$secretKey
ROBOT_API_URL=http://robot_sim:5000
ROBOT_WS_URL=ws://robot_sim:5000/ws/telemetry
DATABASE_URL=postgresql://postgres:password@db:5432/robot_db
REDIS_URL=redis://redis:6379/0
"@

if (-not (Test-Path "backend")) {
    Write-Host "ERROR: backend folder not found. Run this script from repository root." -ForegroundColor Red
    exit 1
}

$envPath = "backend\.env"
$envContent | Out-File -FilePath $envPath -Encoding ascii -Force
Write-Host "Created $envPath" -ForegroundColor Green

Write-Host "Stopping and removing old containers, networks, volumes..." -ForegroundColor Cyan
docker-compose down -v

Write-Host "Building all images from scratch (no cache)..." -ForegroundColor Cyan
docker-compose build --no-cache

Write-Host "Starting all services..." -ForegroundColor Cyan
docker-compose up -d

Write-Host "Waiting for backend to become healthy..." -ForegroundColor Cyan
$maxAttempts = 30
$attempt = 0
$backendReady = $false
while ($attempt -lt $maxAttempts -and -not $backendReady) {
    Start-Sleep -Seconds 2
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            Write-Host "Backend is ready." -ForegroundColor Green
        }
    } catch {
        Write-Host "   Waiting for backend... (attempt $attempt/$maxAttempts)" -ForegroundColor Yellow
    }
}

if (-not $backendReady) {
    Write-Host "ERROR: Backend did not become ready in time. Check logs: docker-compose logs backend" -ForegroundColor Red
    exit 1
}

$backendContainer = docker ps -q --filter "label=com.docker.compose.service=backend"
if (-not $backendContainer) {
    $backendContainer = docker-compose ps -q backend
}

if ($backendContainer) {
    Write-Host "Found backend container: $backendContainer" -ForegroundColor Cyan
    Write-Host "Running backend tests..." -ForegroundColor Cyan
    docker exec -w /app $backendContainer sh -c "PYTHONPATH=/app pytest tests/ -v"
    Write-Host "Tests completed." -ForegroundColor Green
} else {
    Write-Host "WARNING: Could not find backend container. Tests skipped." -ForegroundColor Red
}

Write-Host ""
Write-Host "System is ready!" -ForegroundColor Green
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Backend API docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Robot Simulator API: http://localhost:5000/docs" -ForegroundColor Cyan