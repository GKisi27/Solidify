# Solidify

> **Raster-to-3D CAD Conversion Platform**

Transform 2D raster images into 3D CAD models using AI-powered analysis and OnShape integration.

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

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Or use Make
make dev
```

### Access Points

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

## 🧪 Testing

```bash
# Run all tests
make test

# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test
```

## 📚 Documentation

See the [docs/](./docs/) directory for:
- [Architecture Overview](./docs/architecture/system-overview.md)
- [API Reference](./docs/api/endpoints.md)
- [Deployment Guide](./docs/deployment/aws-deployment.md)

## 📄 License

[MIT License](./LICENSE)
