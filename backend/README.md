# Solidify Backend

> FastAPI REST API for the Raster-to-3D CAD Conversion Platform

## 📁 Structure

```
backend/
├── app/
│   ├── api/           # REST endpoints
│   ├── core/          # Configuration & security
│   ├── models/        # Pydantic schemas
│   ├── services/      # Business logic
│   ├── storage/       # S3 & Redis clients
│   └── utils/         # Utilities
├── config/            # Config files (users.json)
├── tests/             # Unit, integration, e2e tests
└── requirements/      # Dependencies
```

## 🚀 Quick Start

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | User authentication |
| POST | `/api/v1/upload` | Upload image file |
| POST | `/api/v1/jobs` | Submit processing job |
| GET | `/api/v1/jobs` | List user's jobs |
| GET | `/api/v1/jobs/{id}` | Get job status |
| GET | `/api/v1/jobs/{id}/download` | Download results |

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/unit/test_auth_service.py
```

## ⚙️ Environment Variables

| Variable | Description |
|----------|-------------|
| `REDIS_URL` | Redis connection URL |
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `S3_BUCKET_NAME` | S3 bucket for uploads |
| `GEMINI_API_KEY` | Google Gemini API key |
| `ONSHAPE_ACCESS_KEY` | OnShape API credentials |
