# Docker Configuration

## 📁 Structure

```
docker/
├── backend/
│   └── Dockerfile     # FastAPI container
├── frontend/
│   └── Dockerfile     # React build & nginx
├── worker/
│   └── Dockerfile     # Celery worker
└── nginx/
    ├── Dockerfile     # Reverse proxy
    └── nginx.conf     # Nginx configuration
```

## 🚀 Usage

### Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Production

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production stack
docker-compose -f docker-compose.prod.yml up -d
```

## 🏗️ Images

| Image | Base | Port |
|-------|------|------|
| solidify-backend | python:3.11-slim | 8000 |
| solidify-frontend | node:18-alpine → nginx | 80 |
| solidify-worker | python:3.11-slim | - |
| solidify-nginx | nginx:alpine | 80/443 |
