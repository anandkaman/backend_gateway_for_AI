# VPS Testing Guide - AI Gateway via PuTTY

## Prerequisites

- ✅ VPS with public IP
- ✅ PuTTY installed on your local machine
- ✅ AI Gateway running on VPS (port 8080)
- ✅ DeepSeek-OCR running on VPS (port 8001)

---

## Step 1: Configure Firewall on VPS

First, SSH into your VPS via PuTTY and open the required ports:

```bash
# Allow port 8080 (AI Gateway)
sudo ufw allow 8080/tcp

# Allow port 8001 (DeepSeek-OCR) - Optional, only if you want direct access
sudo ufw allow 8001/tcp

# Check firewall status
sudo ufw status
```

---

## Step 2: Get Your Public IP

On your VPS, run:

```bash
curl -s ifconfig.me
# Or
curl -s icanhazip.com
```

**Save this IP address** - you'll use it for testing.

Example: `203.0.113.45`

---

## Step 3: Update Docker Configuration for External Access

The current Docker setup binds to `0.0.0.0`, which is correct for external access. Verify:

```bash
cd /root/server_ai/backend_ai
docker-compose -f docker/docker-compose.yml ps
```

You should see ports mapped like `0.0.0.0:8080->8080/tcp`

---

## Step 4: Test from Your Local Machine

### Test 1: Health Check

Open a terminal on your **local machine** (not VPS):

```bash
# Replace YOUR_VPS_IP with your actual IP
curl http://YOUR_VPS_IP:8080/health
```

**Expected Response:**
```json
{"status":"healthy","timestamp":"2026-01-15T..."}
```

### Test 2: Get JWT Token

```bash
curl -X POST "http://YOUR_VPS_IP:8080/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"
```

**Expected Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Save the access_token** for next steps.

### Test 3: Test OCR with Image

```bash
# First, encode your image to base64
IMAGE_BASE64=$(base64 -w 0 your_image.jpg)

# Send OCR request
curl -X POST "http://YOUR_VPS_IP:8080/api/ocr" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Client-ID: test_client" \
  -H "X-Resolution: large" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"deepseek-ai/DeepSeek-OCR\",
    \"messages\": [{
      \"role\": \"user\",
      \"content\": [
        {\"type\": \"image_url\", \"image_url\": {\"url\": \"data:image/jpeg;base64,$IMAGE_BASE64\"}},
        {\"type\": \"text\", \"text\": \"Free OCR.\"}
      ]
    }],
    \"max_tokens\": 2048
  }"
```

---

## Step 5: Test from Windows (PuTTY)

### Using PowerShell

Open PowerShell on Windows:

```powershell
# Test health
Invoke-RestMethod -Uri "http://YOUR_VPS_IP:8080/health"

# Get token
$response = Invoke-RestMethod -Uri "http://YOUR_VPS_IP:8080/auth/token" `
  -Method POST `
  -Body @{username="admin"; password="admin"}

$token = $response.access_token
Write-Host "Token: $token"
```

### Using Python on Windows

```python
import requests
import base64

VPS_IP = "YOUR_VPS_IP"
BASE_URL = f"http://{VPS_IP}:8080"

# Get token
response = requests.post(
    f"{BASE_URL}/auth/token",
    data={"username": "admin", "password": "admin"}
)
token = response.json()["access_token"]
print(f"Token: {token}")

# Test OCR
with open("your_image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

response = requests.post(
    f"{BASE_URL}/api/ocr",
    headers={
        "Authorization": f"Bearer {token}",
        "X-Client-ID": "windows_client",
        "X-Resolution": "large"
    },
    json={
        "model": "deepseek-ai/DeepSeek-OCR",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                {"type": "text", "text": "Free OCR."}
            ]
        }],
        "max_tokens": 2048
    }
)

print(response.json())
```

---

## Step 6: Monitor Logs on VPS

While testing, monitor logs on your VPS via PuTTY:

```bash
# Gateway logs
docker-compose -f /root/server_ai/backend_ai/docker/docker-compose.yml logs -f gateway

# DeepSeek-OCR logs
tail -f /root/server_ai/deepseek_ocr_server.log
```

---

## Step 7: Security Recommendations

### For Production:

1. **Enable HTTPS**
   ```bash
   # Install certbot
   sudo apt install certbot python3-certbot-nginx
   
   # Get SSL certificate
   sudo certbot --nginx -d your-domain.com
   ```

2. **Change Default Credentials**
   - Update JWT secret in `/root/server_ai/backend_ai/docker/.env`
   - Implement proper user authentication (currently uses demo auth)

3. **Rate Limiting**
   - Already configured: 60 requests/minute per client
   - Adjust in `config/config.yaml` if needed

4. **Firewall Rules**
   ```bash
   # Only allow specific IPs (optional)
   sudo ufw allow from YOUR_CLIENT_IP to any port 8080
   ```

---

## Troubleshooting

### Issue: Connection Refused

**Solution:**
```bash
# Check if services are running
docker-compose -f /root/server_ai/backend_ai/docker/docker-compose.yml ps

# Check if ports are open
sudo netstat -tulpn | grep 8080

# Restart services
docker-compose -f /root/server_ai/backend_ai/docker/docker-compose.yml restart
```

### Issue: Timeout

**Solution:**
- Check VPS firewall: `sudo ufw status`
- Check cloud provider firewall (AWS Security Groups, etc.)
- Verify Docker is binding to `0.0.0.0` not `127.0.0.1`

### Issue: 502 Bad Gateway

**Solution:**
```bash
# Check gateway logs
docker-compose -f /root/server_ai/backend_ai/docker/docker-compose.yml logs gateway

# Restart gateway
docker-compose -f /root/server_ai/backend_ai/docker/docker-compose.yml restart gateway
```

---

## Quick Test Script

Save this as `test_vps.sh` on your **local machine**:

```bash
#!/bin/bash

VPS_IP="YOUR_VPS_IP"
BASE_URL="http://$VPS_IP:8080"

echo "Testing AI Gateway on VPS: $VPS_IP"
echo "=================================="

# Test 1: Health
echo -e "\n1. Health Check..."
curl -s "$BASE_URL/health" | python3 -m json.tool

# Test 2: Get Token
echo -e "\n2. Getting Token..."
TOKEN_JSON=$(curl -s -X POST "$BASE_URL/auth/token" -d "username=admin&password=admin")
echo "$TOKEN_JSON" | python3 -m json.tool

# Test 3: Check Models
echo -e "\n3. Checking Models..."
TOKEN=$(echo "$TOKEN_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")
if [ ! -z "$TOKEN" ]; then
    curl -s "$BASE_URL/admin/models" \
        -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
fi

echo -e "\n=================================="
echo "Tests complete!"
```

Run it:
```bash
chmod +x test_vps.sh
./test_vps.sh
```

---

## Performance Tips

1. **Use Compression**
   - Images are base64 encoded (33% larger)
   - Consider using multipart/form-data for large files

2. **Batch Requests**
   - Queue multiple OCR requests
   - Gateway handles up to 12 concurrent (2 processing + 10 waiting)

3. **Monitor Resources**
   ```bash
   # On VPS
   docker stats
   nvidia-smi
   ```

---

## Next Steps

1. ✅ Test health endpoint from local machine
2. ✅ Get JWT token
3. ✅ Test OCR with sample image
4. ✅ Monitor logs during testing
5. ✅ Set up HTTPS for production
6. ✅ Implement proper authentication
7. ✅ Configure domain name (optional)

---

## Support

If you encounter issues:
1. Check VPS logs: `docker-compose logs -f`
2. Check firewall: `sudo ufw status`
3. Verify services: `docker-compose ps`
4. Test locally first: `curl http://localhost:8080/health`
