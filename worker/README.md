# Solidify Worker

> **✅ IMPLEMENTED** - Celery Background Task Processor

## 🎯 Overview

The Solidify Worker is a Celery-based distributed task queue that handles background processing for the 2D-to-3D CAD conversion pipeline. It provides asynchronous, scalable processing with Redis as the message broker.

## 📁 Structure

```
worker/
├── celery_app.py           # ✅ Celery configuration & app instance
├── config.py               # ✅ Celery settings and configuration
├── tasks/                  # ✅ Individual task definitions
│   ├── __init__.py
│   ├── image_processing.py     # Image analysis & part type detection
│   ├── json_generation.py      # Gemini AI JSON generation
│   ├── json_cleaning.py        # JSON validation & cleaning
│   └── onshape_creation.py     # OnShape 3D model creation
├── pipelines/              # ✅ Task orchestration
│   ├── __init__.py
│   └── conversion_pipeline.py  # Celery chain for full workflow
└── tests/
    └── ...
```

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Start all services including Celery worker
docker-compose up -d

# View Celery worker logs
docker logs -f celery_worker

# Access Flower monitoring UI
open http://localhost:5555
```

### Manual Start (Development)

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Start Celery worker
cd ..
celery -A worker.celery_app worker --loglevel=info

# Start with concurrency
celery -A worker.celery_app worker --loglevel=info --concurrency=4

# Start Flower monitoring (optional)
celery -A worker.celery_app flower --port=5555
```

## 📋 Tasks

| Task | Module | Description |
|------|--------|-------------|
| `process_image_task` | `image_processing.py` | Analyze image with Gemini AI, detect part type (plate/shaft) |
| `generate_json_task` | `json_generation.py` | Generate coordinate JSON using Gemini |
| `clean_json_task` | `json_cleaning.py` | Clean & validate JSON output |
| `create_onshape_model_task` | `onshape_creation.py` | Create 3D model in OnShape |

## 🔄 Conversion Pipeline

The pipeline is implemented as a Celery chain that executes tasks sequentially:

```
┌─────────────────────────┐
│   Image Upload (API)    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  process_image_task     │  ← Detect part type (plate/shaft)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  generate_json_task     │  ← Call Gemini AI for coordinates
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  clean_json_task        │  ← Validate & clean JSON
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ create_onshape_model    │  ← Build 3D model in OnShape
└───────────┬─────────────┘
            │
            ▼
    ✅ STEP File Ready
```

## 💻 Usage Examples

### From FastAPI Backend

The FastAPI `/files/convert` endpoint automatically uses Celery when available:

```python
# POST /files/convert
# Returns:
{
    "message": "Conversion started",
    "task_id": "abc123-def456-...",
    "status": "PENDING",
    "backend": "celery",
    "status_url": "/files/task/abc123-def456-..."
}

# GET /files/task/{task_id}
# Check task status
```

### Direct Python Usage

```python
from worker.pipelines.conversion_pipeline import convert_image_to_3d

# Start conversion
with open("drawing.png", "rb") as f:
    image_bytes = f.read()

result = convert_image_to_3d(image_bytes, "my_part")

# Check status
print(result.ready())  # False if still processing

# Wait for result (blocking)
final_result = result.get()
print(final_result["doc_url"])
```

## ⚙️ Environment Variables

Required environment variables (set in `.env`):

| Variable | Description | Example |
|----------|-------------|---------|
| `CELERY_BROKER_URL` | Redis broker URL | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis result backend | `redis://localhost:6379/1` |
| `USE_CELERY` | Enable Celery mode | `true` |
| `GEMINI_PAID_KEY` | Gemini API key | `your-api-key` |
| `access` | OnShape access key | `your-access-key` |
| `secret` | OnShape secret key | `your-secret-key` |

## 🔍 Monitoring

### Flower Web UI

Celery Flower provides real-time monitoring:

- **URL**: http://localhost:5555
- **Features**: Task progress, worker status, task history, broker stats

### Command Line

```bash
# List active tasks
celery -A worker.celery_app inspect active

# List registered tasks
celery -A worker.celery_app inspect registered

# Check worker stats
celery -A worker.celery_app inspect stats
```

## 🐛 Debugging

### Enable Debug Logging

```bash
celery -A worker.celery_app worker --loglevel=debug
```

### Test Celery Connection

```python
from worker.celery_app import celery_app, debug_task

# Test if Celery is working
result = debug_task.delay()
print(result.get())  # Should print "Celery is working!"
```

## 🔧 Configuration

Task settings are configured in `worker/config.py`:

- **Task timeout**: 1 hour (3600s)
- **Soft timeout**: 55 minutes (3300s)
- **Result expiration**: 24 hours
- **Max retries**: 3
- **Retry delay**: 60 seconds

## 📝 Fallback Mode

If Celery is not available or `USE_CELERY=false`, the system automatically falls back to ThreadPoolExecutor for in-process task execution. This ensures the API continues working even without Celery.

## ⚠️ Common Issues

### Celery worker won't start

```bash
# Check if Redis is running
docker ps | grep redis

# Check environment variables
echo $CELERY_BROKER_URL
```

### Tasks stuck in PENDING

- Worker might not be running
- Check Redis connection
- Verify task autodiscovery in `celery_app.py`

### Import errors

- Ensure `backend/` is in Python path
- Check that all dependencies are installed

## 📚 More Information

- [Celery Documentation](https://docs.celeryq.dev/)
- [Flower Documentation](https://flower.readthedocs.io/)
- [Redis Documentation](https://redis.io/documentation)

## Docker Shortcut
docker compose -f docker-compose.dev.yml up --build
docker compose down --remove-orphans 