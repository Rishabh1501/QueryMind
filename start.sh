#!/bin/bash
# Startup script for Retail Insights Assistant
# This script starts Redis and the Streamlit application

set -e  # Exit on error

echo "🚀 Starting Retail Insights Assistant..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Start Redis container
echo "📦 Starting Redis container..."
docker-compose up -d redis

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
sleep 3

# Check Redis health
if docker-compose ps redis | grep -q "Up"; then
    echo "✅ Redis is running"
else
    echo "❌ Redis failed to start"
    exit 1
fi

# Build Docker executor image if it doesn't exist
if ! docker images | grep -q "retail_insights_executor"; then
    echo "🔨 Building Docker executor image..."
    docker build -t retail_insights_executor ./docker
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Start Streamlit
echo "🎯 Starting Streamlit application..."
echo "🌐 App will be available at: http://localhost:8501"
echo ""
streamlit run app.py
