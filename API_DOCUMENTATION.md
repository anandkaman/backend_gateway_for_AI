# AI Gateway - API Documentation

## Base URL
```
http://localhost:8080
```

## Authentication

All endpoints (except `/health` and `/auth/token`) require JWT authentication.

### Get Token

**Endpoint:** `POST /auth/token`

**Request:**
```bash
curl -X POST "http://localhost:8080/auth/token" \
  -d "username=admin&password=admin"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Use the token in all subsequent requests:**
```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Core Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**No authentication required**

```bash
curl http://localhost:8080/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-15T17:00:00.000000"
}
```

---

## Model Endpoints

### 2. Chat Completion (Gemma-3-4B)

**Endpoint:** `POST /api/chat`

**Headers:**
- `Authorization`: Bearer token (required)
- `X-Client-ID`: Your application ID (required)
- `X-Priority`: `low`, `normal`, or `high` (optional, default: `normal`)

**Request:**
```bash
curl -X POST "http://localhost:8080/api/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Client-ID: my_app" \
  -H "X-Priority: normal" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-3-4b-it",
    "messages": [
      {"role": "user", "content": "What is 2+2?"}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

**Response:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Request queued for processing"
}
```

---

### 3. OCR Processing (DeepSeek-OCR)

**Endpoint:** `POST /api/ocr`

**Headers:**
- `Authorization`: Bearer token (required)
- `X-Client-ID`: Your application ID (required)
- `X-Resolution`: `tiny`, `small`, `base`, `large`, or `gundam` (optional, default: `large`)
- `X-Priority`: `low`, `normal`, or `high` (optional, default: `normal`)

**Request with Base64 Image:**
```bash
# First, encode your image
IMAGE_BASE64=$(base64 -w 0 your_image.jpg)

curl -X POST "http://localhost:8080/api/ocr" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Client-ID: my_app" \
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

**Response:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "queued",
  "resolution": "large",
  "message": "Request queued for OCR processing"
}
```

**OCR Resolution Modes:**

| Mode | Resolution | Vision Tokens | Accuracy | Speed | Use Case |
|------|------------|---------------|----------|-------|----------|
| `tiny` | 512×512 | 64 | 85-90% | Fastest | Quick scans |
| `small` | 640×640 | 100 | 90-93% | Fast | Standard docs |
| `base` | 1024×1024 | 256 | 95-97% | Medium | High quality |
| `large` | 1280×1280 | 400 | 97-99% | Slow | Detailed scans |
| `gundam` | Dynamic | Variable | 98-99.5% | Slowest | Complex docs |

---

## Admin Endpoints

### 4. Get All Models Status

**Endpoint:** `GET /admin/models`

```bash
curl "http://localhost:8080/admin/models" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "gemma": {
    "name": "gemma",
    "status": "running",
    "port": 8000,
    "started_at": "2026-01-15T16:00:00.000000",
    "uptime_seconds": 3600,
    "resolution": null,
    "is_healthy": true
  },
  "deepseek": {
    "name": "deepseek",
    "status": "running",
    "port": 8001,
    "started_at": "2026-01-15T16:00:00.000000",
    "uptime_seconds": 3600,
    "resolution": "large",
    "is_healthy": true
  }
}
```

---

### 5. Start a Model

**Endpoint:** `POST /admin/models/{model_name}/start`

**Parameters:**
- `model_name`: `gemma` or `deepseek`
- `resolution` (query param, optional): For DeepSeek-OCR only

```bash
# Start Gemma
curl -X POST "http://localhost:8080/admin/models/gemma/start" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Start DeepSeek with Gundam mode
curl -X POST "http://localhost:8080/admin/models/deepseek/start?resolution=gundam" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "status": "started",
  "model": "gemma"
}
```

---

### 6. Stop a Model

**Endpoint:** `POST /admin/models/{model_name}/stop`

**Parameters:**
- `graceful` (query param, optional): Wait for active requests (default: `true`)

```bash
# Graceful stop (wait for active requests)
curl -X POST "http://localhost:8080/admin/models/deepseek/stop?graceful=true" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Force stop
curl -X POST "http://localhost:8080/admin/models/deepseek/stop?graceful=false" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "status": "stopped",
  "model": "deepseek"
}
```

---

### 7. Switch OCR Resolution

**Endpoint:** `POST /admin/ocr/resolution`

**Parameters:**
- `resolution` (query param, required): `tiny`, `small`, `base`, `large`, or `gundam`
- `graceful` (query param, optional): Wait for active requests (default: `true`)

```bash
# Switch to Gundam mode (highest accuracy)
curl -X POST "http://localhost:8080/admin/ocr/resolution?resolution=gundam&graceful=true" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Switch to Large mode
curl -X POST "http://localhost:8080/admin/ocr/resolution?resolution=large" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "status": "switched",
  "resolution": "gundam",
  "message": "OCR resolution switched to gundam"
}
```

---

### 8. Get Queue Metrics

**Endpoint:** `GET /admin/queue/{model_name}`

```bash
curl "http://localhost:8080/admin/queue/gemma" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "model": "gemma",
  "processing": 5,
  "waiting": 3,
  "max_concurrent": 10,
  "max_waiting": 10,
  "total_processed": 1234,
  "total_failed": 12,
  "total_timeout": 3,
  "utilization": 0.5
}
```

**Metrics Explained:**
- `processing`: Currently processing requests
- `waiting`: Requests in queue
- `max_concurrent`: Maximum concurrent requests (primary queue)
- `max_waiting`: Maximum waiting requests (secondary queue)
- `utilization`: Processing / max_concurrent (0.0 to 1.0)

---

### 9. Get Crash Logs

**Endpoint:** `GET /admin/crashes`

**Parameters:**
- `limit` (query param, optional): Number of logs to return (default: 100)

```bash
curl "http://localhost:8080/admin/crashes?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
[
  {
    "timestamp": "2026-01-15T16:30:00.000000",
    "error": "Connection timeout",
    "model": "gemma",
    "request_id": "550e8400-e29b-41d4-a716-446655440002",
    "stack_trace": "..."
  }
]
```

---

### 10. Get Missing Model Requests

**Endpoint:** `GET /admin/missing-models`

**Parameters:**
- `limit` (query param, optional): Number of records to return (default: 100)

```bash
curl "http://localhost:8080/admin/missing-models?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
[
  {
    "model_name": "gpt-4",
    "client_id": "my_app",
    "timestamp": "2026-01-15T16:45:00.000000"
  }
]
```

---

## Priority Levels

Requests can be prioritized using the `X-Priority` header:

| Priority | Description | Use Case |
|----------|-------------|----------|
| `high` | Processed first | Critical requests |
| `normal` | Default priority | Standard requests |
| `low` | Processed last | Background tasks |

**Example:**
```bash
curl -X POST "http://localhost:8080/api/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Client-ID: my_app" \
  -H "X-Priority: high" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma-3-4b-it", "messages": [...]}'
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid token"
}
```

### 404 Not Found
```json
{
  "detail": "Model deepseek not available"
}
```

### 503 Service Unavailable
```json
{
  "detail": "Queue is full, please try again later"
}
```

---

## Rate Limiting

Default rate limits (configurable in `config.yaml`):
- **60 requests per minute** per client
- **Burst**: 10 requests

---

## Complete Examples

### Example 1: OCR a Document

```bash
#!/bin/bash

# Get token
TOKEN=$(curl -s -X POST "http://localhost:8080/auth/token" \
  -d "username=admin&password=admin" | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Encode image
IMAGE_BASE64=$(base64 -w 0 document.jpg)

# Process OCR
curl -X POST "http://localhost:8080/api/ocr" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Client-ID: my_ocr_app" \
  -H "X-Resolution: gundam" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"deepseek-ai/DeepSeek-OCR\",
    \"messages\": [{
      \"role\": \"user\",
      \"content\": [
        {\"type\": \"image_url\", \"image_url\": {\"url\": \"data:image/jpeg;base64,$IMAGE_BASE64\"}},
        {\"type\": \"text\", \"text\": \"<|grounding|>Convert the document to markdown.\"}
      ]
    }],
    \"max_tokens\": 4096
  }"
```

### Example 2: Chat with Gemma

```bash
#!/bin/bash

# Get token
TOKEN=$(curl -s -X POST "http://localhost:8080/auth/token" \
  -d "username=admin&password=admin" | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Chat
curl -X POST "http://localhost:8080/api/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Client-ID: my_chat_app" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-3-4b-it",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Explain quantum computing in simple terms."}
    ],
    "max_tokens": 500,
    "temperature": 0.7
  }'
```

### Example 3: Monitor Queue Status

```bash
#!/bin/bash

TOKEN="YOUR_TOKEN"

while true; do
  clear
  echo "=== Queue Status ==="
  curl -s "http://localhost:8080/admin/queue/gemma" \
    -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
  
  echo ""
  echo "=== DeepSeek Queue ==="
  curl -s "http://localhost:8080/admin/queue/deepseek" \
    -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
  
  sleep 5
done
```

---

## Python SDK Example

```python
import httpx
import base64

class AIGatewayClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.token = self._get_token(username, password)
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Client-ID": "python_sdk"
        }
    
    def _get_token(self, username: str, password: str) -> str:
        response = httpx.post(
            f"{self.base_url}/auth/token",
            data={"username": username, "password": password}
        )
        return response.json()["access_token"]
    
    def chat(self, messages: list, priority: str = "normal") -> dict:
        headers = {**self.headers, "X-Priority": priority}
        response = httpx.post(
            f"{self.base_url}/api/chat",
            headers=headers,
            json={
                "model": "gemma-3-4b-it",
                "messages": messages,
                "max_tokens": 500
            }
        )
        return response.json()
    
    def ocr(self, image_path: str, resolution: str = "large") -> dict:
        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        headers = {**self.headers, "X-Resolution": resolution}
        response = httpx.post(
            f"{self.base_url}/api/ocr",
            headers=headers,
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
        return response.json()

# Usage
client = AIGatewayClient("http://localhost:8080", "admin", "admin")

# Chat
result = client.chat([
    {"role": "user", "content": "Hello!"}
])

# OCR
result = client.ocr("document.jpg", resolution="gundam")
```

---

## Interactive TUI Console

Monitor and control the gateway with the interactive console:

```bash
# Get token first
TOKEN=$(curl -s -X POST "http://localhost:8080/auth/token" \
  -d "username=admin&password=admin" | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Run TUI
python -m console.tui http://localhost:8080 $TOKEN
```

**Features:**
- Real-time model status
- Queue metrics with utilization bars
- Health monitoring
- Keyboard controls

---

## Configuration

Edit `config/config.yaml` to customize:

```yaml
# Queue settings
queue:
  max_waiting: 10        # Secondary queue size
  timeout: 300          # Request timeout (seconds)
  
# Auto-switching
auto_switch:
  enabled: true
  pattern_window_days: 7
  min_requests_for_switch: 10
  
# OCR default resolution
models:
  deepseek:
    resolution_mode: "large"  # or "gundam"
```

---

## Support

For issues:
1. Check `/admin/crashes` for error logs
2. Check `/admin/queue/{model}` for queue status
3. View Docker logs: `docker-compose logs -f gateway`
