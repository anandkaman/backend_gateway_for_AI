# AI Gateway - Client API Guide

**Version:** 1.0.0  
**Base URL:** `https://your-gateway-domain.com` (or `http://localhost:8080` for testing)

---

## Quick Start

### 1. Get Your API Token

Contact your administrator to get your API credentials. Then obtain a token:

```bash
curl -X POST "https://your-gateway-domain.com/auth/token" \
  -d "username=YOUR_USERNAME&password=YOUR_PASSWORD"
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

**Save this token** - you'll need it for all API calls.

---

## Authentication

Include your token in every request:

```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Available Services

### 1. Text Generation (Chat)
- **Model:** Gemma-3-4B
- **Use for:** Conversations, Q&A, text completion
- **Endpoint:** `/api/chat`

### 2. OCR (Document Processing)
- **Model:** DeepSeek-OCR
- **Use for:** Extract text from images, PDFs, documents
- **Endpoint:** `/api/ocr`

---

## API Endpoints

### Chat / Text Generation

**POST** `/api/chat`

Generate text responses, have conversations, or complete prompts.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
X-Client-ID: your_app_name
Content-Type: application/json
```

**Request Body:**
```json
{
  "model": "gemma-3-4b-it",
  "messages": [
    {"role": "user", "content": "Your question or prompt here"}
  ],
  "max_tokens": 500,
  "temperature": 0.7
}
```

**Example:**
```bash
curl -X POST "https://your-gateway-domain.com/api/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Client-ID: my_app" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-3-4b-it",
    "messages": [
      {"role": "user", "content": "Explain machine learning in simple terms"}
    ],
    "max_tokens": 500
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

### OCR / Document Processing

**POST** `/api/ocr`

Extract text from images or documents.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
X-Client-ID: your_app_name
X-Resolution: large
Content-Type: application/json
```

**Resolution Options:**
- `large` - Best quality (recommended)
- `gundam` - Highest accuracy for complex documents
- `base` - Balanced speed/quality
- `small` - Faster processing

**Request Body:**
```json
{
  "model": "deepseek-ai/DeepSeek-OCR",
  "messages": [{
    "role": "user",
    "content": [
      {
        "type": "image_url",
        "image_url": {
          "url": "data:image/jpeg;base64,YOUR_BASE64_IMAGE"
        }
      },
      {
        "type": "text",
        "text": "Free OCR."
      }
    ]
  }],
  "max_tokens": 2048
}
```

**Example (Bash):**
```bash
# Encode your image
IMAGE_BASE64=$(base64 -w 0 your_document.jpg)

# Send OCR request
curl -X POST "https://your-gateway-domain.com/api/ocr" \
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

---

## Code Examples

### Python

```python
import requests
import base64

class AIGatewayClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.token = self._get_token(username, password)
    
    def _get_token(self, username, password):
        response = requests.post(
            f"{self.base_url}/auth/token",
            data={"username": username, "password": password}
        )
        return response.json()["access_token"]
    
    def chat(self, message):
        """Send a chat message"""
        response = requests.post(
            f"{self.base_url}/api/chat",
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-Client-ID": "python_client",
                "Content-Type": "application/json"
            },
            json={
                "model": "gemma-3-4b-it",
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 500
            }
        )
        return response.json()
    
    def ocr(self, image_path, resolution="large"):
        """Extract text from image"""
        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        response = requests.post(
            f"{self.base_url}/api/ocr",
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-Client-ID": "python_client",
                "X-Resolution": resolution,
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-ai/DeepSeek-OCR",
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        },
                        {"type": "text", "text": "Free OCR."}
                    ]
                }],
                "max_tokens": 2048
            }
        )
        return response.json()

# Usage
client = AIGatewayClient(
    "https://your-gateway-domain.com",
    "your_username",
    "your_password"
)

# Chat
result = client.chat("What is artificial intelligence?")
print(result)

# OCR
result = client.ocr("document.jpg", resolution="gundam")
print(result)
```

### JavaScript / Node.js

```javascript
const axios = require('axios');
const fs = require('fs');

class AIGatewayClient {
  constructor(baseUrl, username, password) {
    this.baseUrl = baseUrl;
    this.token = null;
    this.init(username, password);
  }

  async init(username, password) {
    const response = await axios.post(`${this.baseUrl}/auth/token`, 
      `username=${username}&password=${password}`,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );
    this.token = response.data.access_token;
  }

  async chat(message) {
    const response = await axios.post(
      `${this.baseUrl}/api/chat`,
      {
        model: "gemma-3-4b-it",
        messages: [{ role: "user", content: message }],
        max_tokens: 500
      },
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'X-Client-ID': 'nodejs_client',
          'Content-Type': 'application/json'
        }
      }
    );
    return response.data;
  }

  async ocr(imagePath, resolution = 'large') {
    const imageBuffer = fs.readFileSync(imagePath);
    const imageBase64 = imageBuffer.toString('base64');

    const response = await axios.post(
      `${this.baseUrl}/api/ocr`,
      {
        model: "deepseek-ai/DeepSeek-OCR",
        messages: [{
          role: "user",
          content: [
            {
              type: "image_url",
              image_url: { url: `data:image/jpeg;base64,${imageBase64}` }
            },
            { type: "text", text: "Free OCR." }
          ]
        }],
        max_tokens: 2048
      },
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'X-Client-ID': 'nodejs_client',
          'X-Resolution': resolution,
          'Content-Type': 'application/json'
        }
      }
    );
    return response.data;
  }
}

// Usage
(async () => {
  const client = new AIGatewayClient(
    'https://your-gateway-domain.com',
    'your_username',
    'your_password'
  );

  // Chat
  const chatResult = await client.chat('Hello, how are you?');
  console.log(chatResult);

  // OCR
  const ocrResult = await client.ocr('document.jpg', 'large');
  console.log(ocrResult);
})();
```

---

## Request Priority

You can prioritize urgent requests using the `X-Priority` header:

```bash
-H "X-Priority: high"
```

**Priority Levels:**
- `high` - Processed first (for urgent requests)
- `normal` - Default priority
- `low` - Processed last (for background tasks)

**Example:**
```bash
curl -X POST "https://your-gateway-domain.com/api/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Client-ID: my_app" \
  -H "X-Priority: high" \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma-3-4b-it", "messages": [...]}'
```

---

## Error Handling

### Common Errors

**401 Unauthorized**
```json
{"detail": "Invalid token"}
```
→ Your token is invalid or expired. Get a new token.

**503 Service Unavailable**
```json
{"detail": "Queue is full, please try again later"}
```
→ The system is at capacity. Wait a few seconds and retry.

**404 Not Found**
```json
{"detail": "Model not available"}
```
→ The requested model is not currently running. Contact support.

### Best Practices

1. **Handle errors gracefully** - Implement retry logic with exponential backoff
2. **Cache tokens** - Tokens are valid for 60 minutes
3. **Use appropriate timeouts** - Set reasonable request timeouts (30-60 seconds)
4. **Monitor rate limits** - Default: 60 requests/minute per client

---

## Rate Limits

- **60 requests per minute** per client
- **Burst**: Up to 10 requests in quick succession

If you exceed the limit, you'll receive a `429 Too Many Requests` error.

---

## Supported File Types & Limits

### OCR Service

**Supported Formats:**
- ✅ **Images**: JPEG, PNG, WebP, BMP, TIFF
- ✅ **Documents**: PDF (single or multi-page)
- ✅ **Screenshots**: PNG, JPEG

**File Size Limits:**
- **Maximum file size**: 10 MB per request
- **Recommended size**: 1-5 MB for best performance
- **Image dimensions**: Up to 4096×4096 pixels

**Encoding:**
- All files must be base64 encoded
- Use `data:image/jpeg;base64,` or `data:application/pdf;base64,` prefix

### Chat Service

**Input:**
- Text only
- Maximum tokens: 2048 (configurable)

---

## OCR Tips

### For Best Results:

1. **Use high-quality images** - Clear, well-lit scans (300 DPI recommended)
2. **Optimize file size:**
   - Compress large images before uploading
   - Use JPEG for photos, PNG for text/screenshots
   - Keep under 5MB for faster processing
3. **Choose the right resolution:**
   - `large` - For most documents (recommended)
   - `gundam` - For complex legal documents, forms, or multi-page PDFs
4. **Supported languages:** Auto-detected (English, Chinese, Japanese, Korean, Arabic, Hindi, European languages, etc.)

### OCR Prompts:

- **Extract all text:** `"Free OCR."`
- **Convert to markdown:** `"<|grounding|>Convert the document to markdown."`
- **Specific extraction:** `"<|grounding|>OCR this image."`

---

## Support

**Questions or Issues?**
- Contact: support@your-company.com
- Documentation: https://docs.your-gateway-domain.com

**Status Page:**
- Check system status: `GET /health`

---

## Changelog

### Version 1.0.0 (2026-01-15)
- Initial release
- Chat API (Gemma-3-4B)
- OCR API (DeepSeek-OCR)
- Priority queuing
- Multi-resolution OCR support

---

## Legal

**Terms of Service:** https://your-company.com/terms  
**Privacy Policy:** https://your-company.com/privacy

© 2026 Your Company. All rights reserved.
