# Solidify Worker

> Celery Background Task Processor

## 📁 Structure

```
worker/
├── celery_app.py      # Celery configuration
├── tasks/             # Individual task definitions
│   ├── image_processing.py
│   ├── json_generation.py
│   ├── json_cleaning.py
│   └── onshape_creation.py
├── pipelines/         # Task orchestration
│   └── conversion_pipeline.py
└── tests/
```

## 🚀 Quick Start

```bash
# Start Celery worker
celery -A celery_app worker --loglevel=info

# Start with concurrency
celery -A celery_app worker --loglevel=info --concurrency=4
```

## 📋 Tasks

| Task | Description |
|------|-------------|
| `image_processing` | Analyze image with Gemini AI |
| `json_generation` | Generate coordinate JSON |
| `json_cleaning` | Clean & validate JSON output |
| `onshape_creation` | Create 3D model in OnShape |

## 🔄 Conversion Pipeline

```
Image Upload
     │
     ▼
┌─────────────────┐
│ image_processing │
└────────┬────────┘
         ▼
┌─────────────────┐
│ json_generation  │
└────────┬────────┘
         ▼
┌─────────────────┐
│ json_cleaning    │
└────────┬────────┘
         ▼
┌─────────────────┐
│ onshape_creation │
└────────┬────────┘
         ▼
   STEP File Ready
```

## ⚙️ Environment Variables

| Variable | Description |
|----------|-------------|
| `CELERY_BROKER_URL` | Redis broker URL |
| `CELERY_RESULT_BACKEND` | Redis result backend |
