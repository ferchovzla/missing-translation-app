#!/bin/bash

# TransQA Landing Page Startup Script

echo "🚀 Starting TransQA Landing Page..."

# Check if we're in the right directory
if [ ! -f "api/main.py" ]; then
    echo "❌ Error: Please run this script from the landing-page-app directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📚 Installing requirements..."
pip install --upgrade pip
pip install -r requirements-web.txt

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check if TransQA config exists
if [ ! -f "../transqa.toml" ]; then
    echo "⚠️  Warning: TransQA configuration file not found. Using defaults."
fi

# Start the server
echo "🌐 Starting FastAPI server..."
echo "📍 Landing Page: http://localhost:8000"
echo "📋 API Documentation: http://localhost:8000/docs"
echo "📖 API Reference: http://localhost:8000/redoc"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
