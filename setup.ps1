# setup for the config

Write-Host "Setting up Robot Management System..." -ForegroundColor Cyan

$secretKey = ""
if (Get-Command python -ErrorAction SilentlyContinue) {
    $secretKey = python -c "import secrets; print(secrets.token_urlsafe(32))"
    Write-Host "Generated secret key using Python." -ForegroundColor Green
} else {
    # Fallback: generate a random string using PowerShell
    $secretKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    Write-Host "Python not found, used fallback random string." -ForegroundColor Yellow
}

# Create the .env file
$envContent = @"
SECRET_KEY=$secretKey
ROBOT_API_URL=http://robot_sim:5000
ROBOT_WS_URL=ws://robot_sim:5000/ws/telemetry
DATABASE_URL=postgresql://postgres:password@db:5432/robot_db
REDIS_URL=redis://redis:6379/0
"@

$envPath = "backend\.env"
$envContent | Out-File -FilePath $envPath -Encoding ascii
Write-Host "Created $envPath" -ForegroundColor Green

# Stop any old containers and start fresh
Write-Host "Stopping any old containers..." -ForegroundColor Cyan
docker-compose down -v

Write-Host "Building and starting all services..." -ForegroundColor Cyan
docker-compose up --build

Write-Host "System is ready! Open http://localhost:3000 in your browser." -ForegroundColor Green