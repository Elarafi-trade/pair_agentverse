#!/usr/bin/env bash
# Render.com deployment script for ELARA Agent

echo "=========================================="
echo "ELARA Agent - Render Deployment"
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

if [ -z "$AGENTVERSE_API_KEY" ]; then
    echo "⚠️  WARNING: AGENTVERSE_API_KEY not set (agent won't register)"
else
    echo "✓ AGENTVERSE_API_KEY configured"
fi

if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  WARNING: DATABASE_URL not set (caching disabled)"
else
    echo "✓ DATABASE_URL configured"
fi

echo ""
echo "🚀 Starting ELARA agent..."
echo "=========================================="

# Start the agent
exec python agentverse_deploy.py
