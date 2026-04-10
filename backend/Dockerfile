FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/

WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY backend/requirements.txt ./backend_requirements.txt
COPY worker/requirements.txt ./worker_requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r backend_requirements.txt -r worker_requirements.txt

# Copy application code
COPY backend/ /app/
COPY worker/ /worker/ 

EXPOSE 8000

# This is the default for the 'backend' service. 
# The 'celery_worker' service overrides this command in docker-compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]