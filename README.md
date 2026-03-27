# Solidify

> **Raster-to-3D CAD Conversion Platform**

Transform 2D raster images into 3D CAD models using AI-powered analysis and OnShape integration.

## 🎉 What's New

**✅ Celery Implementation Complete!** 
Distributed task queue now fully implemented with Redis broker, automatic retries, and real-time monitoring.

- 🚀 **Async Processing**: Tasks run in background workers
- 📊 **Monitoring**: Flower UI at http://localhost:5555
- 🔄 **Auto-Retry**: Failed tasks automatically retry with exponential backoff
- 📈 **Scalable**: Add more workers to increase throughput
- 🔧 **Graceful Fallback**: Falls back to ThreadPoolExecutor if Celery unavailable

**Quick Test**: `python test_celery_setup.py` ✨

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   React.js  │────▶│   FastAPI   │────▶│   Celery    │
│  Frontend   │◀────│   Backend   │◀────│   Worker    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │    Redis    │     │  Gemini AI  │
                    │  (Queue)    │     │  OnShape    │
                    └─────────────┘     └─────────────┘
```

## 📁 Project Structure

| Directory | Description |
|-----------|-------------|
| `backend/` | FastAPI REST API |
| `frontend/` | React.js web application |
| `worker/` | Celery background tasks |
| `docker/` | Container configurations |
| `aws/` | AWS deployment configs |
| `docs/` | Documentation |
| `scripts/` | Utility scripts |

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+
- Python 3.11+

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd solidify

# Copy environment file and add your API keys (IMPORTANT!)
cp .env.example .env
# Edit .env - see ENV_SETUP_GUIDE.md for details

# Start all services with Docker
docker-compose up -d

# Or use Make
make dev

# Or start manually (local development):
# 1. Install dependencies: cd backend && pip install -r requirements.txt
# 2. Start Redis: docker run -p 6379:6379 redis:7
# 3. Start Celery: python start_celery_worker.py
# 4. Start API: cd backend && uvicorn app.main:app --reload
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | React web application |
| Backend API | http://localhost:8000 | FastAPI REST API |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| Flower | http://localhost:5555 | Celery task monitoring |

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ENV_SETUP_GUIDE.md](./ENV_SETUP_GUIDE.md) | **How to set up .env with API keys** ⭐ |
| [WHATS_NEXT.md](./WHATS_NEXT.md) | What to do after setup |
| [TROUBLESHOOTING_CELERY.md](./TROUBLESHOOTING_CELERY.md) | **Fix "ModuleNotFoundError" and other issues** ⚠️ |
| [QUICK_START_CELERY.md](./QUICK_START_CELERY.md) | Quick reference for Celery |
| [TESTING_CELERY.md](./TESTING_CELERY.md) | Testing guide |
| [RUNNING_CELERY_LOCALLY.md](./RUNNING_CELERY_LOCALLY.md) | Local development with startup scripts |
| [worker/README.md](./worker/README.md) | Complete worker documentation |
| [Architecture Overview](./docs/architecture/system-overview.md) | System design |
| [API Reference](./docs/api/endpoints.md) | API documentation |
| [Deployment Guide](./docs/deployment/aws-deployment.md) | AWS deployment |

## 🧪 Testing

```bash
# Test Celery setup
python test_celery_setup.py

# Run all tests
make test

# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test

# Celery worker tests
python worker\tests\test_celery.py
```

## 📄 License

[MIT License](./LICENSE)
