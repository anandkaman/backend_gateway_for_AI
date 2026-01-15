#!/bin/bash

# Quick VPS Setup for External Access

echo "🚀 Setting up AI Gateway for External Access"
echo "=============================================="
echo ""

# Step 1: Get public IP
echo "1️⃣  Getting your public IP..."
PUBLIC_IP=$(curl -s ifconfig.me || curl -s icanhazip.com)
echo "   Your VPS Public IP: $PUBLIC_IP"
echo ""

# Step 2: Configure firewall
echo "2️⃣  Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 8080/tcp
    echo "   ✅ Port 8080 opened"
    sudo ufw status | grep 8080
else
    echo "   ⚠️  UFW not installed, skipping firewall config"
    echo "   Make sure port 8080 is open in your cloud provider's firewall"
fi
echo ""

# Step 3: Verify services
echo "3️⃣  Checking services..."
docker-compose -f /root/server_ai/backend_ai/docker/docker-compose.yml ps
echo ""

# Step 4: Test locally
echo "4️⃣  Testing locally..."
HEALTH=$(curl -s http://localhost:8080/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo "   ✅ Gateway is healthy!"
else
    echo "   ❌ Gateway health check failed!"
    exit 1
fi
echo ""

# Step 5: Create test command
echo "5️⃣  Test from your local machine with:"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "# Health Check"
echo "curl http://$PUBLIC_IP:8080/health"
echo ""
echo "# Get Token"
echo "curl -X POST \"http://$PUBLIC_IP:8080/auth/token\" \\"
echo "  -H \"Content-Type: application/x-www-form-urlencoded\" \\"
echo "  -d \"username=admin&password=admin\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "✅ Setup complete!"
echo ""
echo "📚 Full testing guide: /root/server_ai/backend_ai/VPS_TESTING_GUIDE.md"
echo ""
