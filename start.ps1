# PowerShell startup script for Retail Insights Assistant
# This script starts Redis and the Streamlit application

Write-Host "🚀 Starting Retail Insights Assistant..." -ForegroundColor Green

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Start Redis container
Write-Host "📦 Starting Redis container..." -ForegroundColor Cyan
docker-compose up -d redis

# Wait for Redis to be ready
Write-Host "⏳ Waiting for Redis to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Check Redis health
$redisStatus = docker-compose ps redis
if ($redisStatus -match "Up") {
    Write-Host "✅ Redis is running" -ForegroundColor Green
} else {
    Write-Host "❌ Redis failed to start" -ForegroundColor Red
    exit 1
}

# Build Docker executor image if it doesn't exist
$imageExists = docker images | Select-String "retail_insights_executor"
if (-not $imageExists) {
    Write-Host "🔨 Building Docker executor image..." -ForegroundColor Cyan
    docker build -t retail_insights_executor ./docker
}

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Start Streamlit
Write-Host ""
Write-Host "🎯 Starting Streamlit application..." -ForegroundColor Green
Write-Host "🌐 App will be available at: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""
streamlit run app.py
