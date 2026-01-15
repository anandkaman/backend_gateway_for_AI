#!/bin/bash

# AI Gateway Quick Start Script

set -e

echo "🚀 AI Gateway - Quick Start"
echo "=============================="
echo ""

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the backend_ai directory"
    exit 1
fi

# Step 1: Setup environment
echo "📦 Step 1: Setting up environment..."
if [ ! -f "docker/.env" ]; then
    echo "Creating .env file..."
    cp docker/.env.example docker/.env
    echo "⚠️  Please edit docker/.env and set a secure JWT_SECRET!"
    echo "   Current value is for development only."
fi

# Step 2: Create logs directory
echo "📁 Step 2: Creating logs directory..."
mkdir -p logs

# Step 3: Start Docker services
echo "🐳 Step 3: Starting Docker services..."
docker-compose -f docker/docker-compose.yml up -d

echo ""
echo "⏳ Waiting for services to start (30 seconds)..."
sleep 30

# Step 4: Check health
echo "🏥 Step 4: Checking health..."
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✅ Gateway is healthy!"
else
    echo "❌ Gateway health check failed"
    echo "   Check logs: docker-compose -f docker/docker-compose.yml logs gateway"
    exit 1
fi

# Step 5: Get token
echo ""
echo "🔑 Step 5: Getting authentication token..."
echo "   (Using demo credentials: admin/admin)"
echo ""

TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8080/auth/token" \
    -d "username=admin&password=admin")

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Failed to get token"
    echo "   Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Token obtained!"
echo ""
echo "=============================="
echo "🎉 AI Gateway is ready!"
echo "=============================="
echo ""
echo "API URL: http://localhost:8080"
echo "Access Token: $ACCESS_TOKEN"
echo ""
echo "📚 Quick Commands:"
echo ""
echo "# Check model status"
echo "curl http://localhost:8080/admin/models \\"
echo "  -H \"Authorization: Bearer $ACCESS_TOKEN\""
echo ""
echo "# Start Gemma model"
echo "curl -X POST http://localhost:8080/admin/models/gemma/start \\"
echo "  -H \"Authorization: Bearer $ACCESS_TOKEN\""
echo ""
echo "# Start DeepSeek OCR"
echo "curl -X POST http://localhost:8080/admin/models/deepseek/start \\"
echo "  -H \"Authorization: Bearer $ACCESS_TOKEN\""
echo ""
echo "# Switch OCR to Gundam mode"
echo "curl -X POST \"http://localhost:8080/admin/ocr/resolution?resolution=gundam\" \\"
echo "  -H \"Authorization: Bearer $ACCESS_TOKEN\""
echo ""
echo "# View logs"
echo "docker-compose -f docker/docker-compose.yml logs -f gateway"
echo ""
echo "# Stop services"
echo "docker-compose -f docker/docker-compose.yml down"
echo ""
echo "📖 Full documentation: README.md"
echo ""
