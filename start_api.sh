#!/usr/bin/env bash
# Render.com deployment script for API Server

echo "=========================================="
echo "ELARA API Server - Render Deployment"
echo "=========================================="

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✓ Dependencies installed"

# Verify environment variables
echo ""
echo "🔍 Checking environment variables..."

if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "✗ ERROR: OPENROUTER_API_KEY not set"
    exit 1
fi
echo "✓ OPENROUTER_API_KEY configured"

if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  WARNING: DATABASE_URL not set (caching disabled)"
else
    echo "✓ DATABASE_URL configured"
fi

# Set Render-specific port (Render provides this)
export FLASK_PORT=${PORT:-10000}
export FLASK_HOST="0.0.0.0"

echo ""
echo "🚀 Starting API server on port $FLASK_PORT..."
echo "=========================================="

# Start the API server
exec python api_server.py
