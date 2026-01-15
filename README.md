# AI Gateway - Production-Grade Model Management System

A production-ready FastAPI gateway for managing multiple AI models with intelligent routing, crash-proof queuing, and comprehensive monitoring.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🚀 Features

### Core Capabilities
- **Multi-Model Support**: Manage multiple AI models (text generation, OCR, etc.)
- **Crash-Proof Queue**: MongoDB-backed queue with automatic recovery (10+10 per model)
- **JWT Authentication**: Secure API access with token-based auth
- **Dynamic Configuration**: Switch model parameters on-the-fly
- **15-Day History**: Auto-cleanup of old data
- **Crash Logging**: Track and recover from failures
- **Pattern-Based Auto-Switching**: Automatically load frequently used models

### Queue System
- **Primary Queue**: 10 concurrent requests per model
- **Secondary Queue**: 10 waiting requests per model
- **Priority Handling**: HIGH > NORMAL > LOW
- **Automatic Retry**: Up to 3 retries on failure
- **Timeout Management**: Auto-fail stuck requests
- **Persistence**: Survives server crashes

### OCR Support (DeepSeek-OCR)
- **Multilingual**: Auto-detects 50+ languages
- **High Accuracy**: 97-99.5% accuracy
- **Multiple Resolutions**: Tiny, Small, Base, Large, Gundam modes
- **PDF Support**: Single and multi-page documents
- **File Formats**: JPEG, PNG, WebP, BMP, TIFF, PDF
- **Max File Size**: 10 MB

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Docker Deployment](#docker-deployment)
- [Security](#security)
- [Architecture](#architecture)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

---

## ⚡ Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- MongoDB 7.0+
- NVIDIA GPU (for AI models)
- 16GB+ RAM

### 1. Clone Repository

```bash
git clone https://github.com/anandkaman/backend_gateway_for_AI.git
cd backend_gateway_for_AI
```

### 2. Configure Environment

```bash
# Copy environment template
cp docker/.env.example docker/.env

# Edit .env and set your JWT secret
nano docker/.env
```

**Important**: Change `JWT_SECRET` to a secure random string:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3. Start Services

```bash
# Using Docker Compose (recommended)
docker-compose -f docker/docker-compose.yml up -d

# Or use the quick start script
./quickstart.sh
```

### 4. Verify Deployment

```bash
# Check health
curl http://localhost:8080/health

# Get authentication token
curl -X POST "http://localhost:8080/auth/token" \
  -d "username=admin&password=admin"
```

---

## 📦 Installation

### Option 1: Docker (Recommended)

```bash
# Build and start
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f gateway

# Stop services
docker-compose -f docker/docker-compose.yml down
```

### Option 2: Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export JWT_SECRET="your-secret-key"

# Run server
python -m app.main
```

---

## ⚙️ Configuration

### Main Configuration (`config/config.yaml`)

```yaml
# Server settings
server:
  host: "0.0.0.0"
  port: 8080
  workers: 4

# Queue configuration
queue:
  max_waiting: 10
  timeout: 300
  persistence_enabled: true

# Auto-switching
auto_switch:
  enabled: true
  pattern_window_days: 7

# Models
models:
  your_model:
    port: 8001
    max_concurrent: 10
    enabled: true
```

### Environment Variables (`.env`)

```bash
JWT_SECRET=your-secure-secret-key
MONGODB_URI=mongodb://mongodb:27017
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
```

---

## 📚 API Documentation

### Authentication

All endpoints (except `/health`) require JWT authentication.

**Get Token:**
```bash
curl -X POST "http://localhost:8080/auth/token" \
  -d "username=admin&password=admin"
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### Core Endpoints

#### Health Check
```bash
GET /health
```

#### Chat/Completion
```bash
POST /api/chat
Headers:
  Authorization: Bearer YOUR_TOKEN
  X-Client-ID: your_app
  X-Priority: normal|high|low
```

#### OCR Processing
```bash
POST /api/ocr
Headers:
  Authorization: Bearer YOUR_TOKEN
  X-Client-ID: your_app
  X-Resolution: large|gundam
```

### Admin Endpoints

- `GET /admin/models` - Get all models status
- `POST /admin/models/{model}/start` - Start a model
- `POST /admin/models/{model}/stop` - Stop a model
- `GET /admin/queue/{model}` - Get queue metrics
- `GET /admin/crashes` - Get crash logs

**Full API documentation**: See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)  
**Client guide**: See [CLIENT_API_GUIDE.md](CLIENT_API_GUIDE.md)

---

## 🐳 Docker Deployment

### Build Custom Image

```bash
docker build -f docker/Dockerfile -t ai-gateway:latest .
```

### Docker Compose

```yaml
version: '3.8'
services:
  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
  
  gateway:
    build: .
    ports:
      - "8080:8080"
    environment:
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - mongodb
```

---

## 🔒 Security

### For Production

1. **Enable HTTPS**
   ```bash
   # Install certbot
   sudo apt install certbot python3-certbot-nginx
   
   # Get SSL certificate (free)
   sudo certbot --nginx -d your-domain.com
   ```

2. **Change Default Credentials**
   - Update `JWT_SECRET` in `.env`
   - Implement proper user authentication

3. **Configure Firewall**
   ```bash
   sudo ufw allow 8080/tcp
   sudo ufw enable
   ```

4. **Rate Limiting**
   - Default: 60 requests/minute per client
   - Configure in `config/config.yaml`

**Security guide**: See [SECURITY_GUIDE.md](SECURITY_GUIDE.md)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         Client Applications              │
│    (JWT Auth + Request Headers)         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      FastAPI Gateway (Port 8080)        │
│  ┌──────────┐  ┌──────────┐            │
│  │ JWT Auth │  │ Queue    │            │
│  │          │  │ (10+10)  │            │
│  └──────────┘  └──────────┘            │
│  ┌──────────┐  ┌──────────┐            │
│  │ MongoDB  │  │ Metrics  │            │
│  │ (15d)    │  │ Collector│            │
│  └──────────┘  └──────────┘            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│        AI Models (vLLM/etc)             │
│  • Text Generation                      │
│  • OCR Processing                       │
│  • Custom Models                        │
└─────────────────────────────────────────┘
```

### Components

- **FastAPI Gateway**: Request routing and management
- **MongoDB**: Queue persistence and history
- **Queue System**: Crash-proof request handling
- **Auto-Switcher**: Pattern-based model loading
- **Metrics Collector**: Performance monitoring

---

## 🧪 Testing

### Run Tests

```bash
# Health check
./test_gateway.sh

# Full API test
./test_complete_api.sh

# OCR test
python3 test_ocr_client.py
```

### Example Test

```python
import requests

# Get token
response = requests.post(
    "http://localhost:8080/auth/token",
    data={"username": "admin", "password": "admin"}
)
token = response.json()["access_token"]

# Test health
response = requests.get(
    "http://localhost:8080/health",
    headers={"Authorization": f"Bearer {token}"}
)
print(response.json())
```

---

## 📊 Monitoring

### Queue Metrics

```bash
curl http://localhost:8080/admin/queue/your_model \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "processing": 5,
  "waiting": 3,
  "utilization": 0.5,
  "total_processed": 1234
}
```

### Logs

```bash
# Gateway logs
docker-compose logs -f gateway

# MongoDB logs
docker-compose logs -f mongodb
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [vLLM](https://github.com/vllm-project/vllm) - LLM serving
- [MongoDB](https://www.mongodb.com/) - Database
- [DeepSeek-OCR](https://huggingface.co/deepseek-ai/DeepSeek-OCR) - OCR model

---

## 📞 Support

- **Documentation**: See [docs/](docs/) folder
- **Issues**: [GitHub Issues](https://github.com/anandkaman/backend_gateway_for_AI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/anandkaman/backend_gateway_for_AI/discussions)

---

## 🗺️ Roadmap

- [ ] Web UI dashboard
- [ ] More model integrations
- [ ] Kubernetes deployment
- [ ] Prometheus metrics
- [ ] GraphQL API
- [ ] WebSocket support

---

**Made with ❤️ for the AI community**
