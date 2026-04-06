FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# install dependencies first (better docker layer caching)
COPY backend/requirements.txt ./backend_requirements.txt
COPY worker/requirements.txt ./worker_requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r backend_requirements.txt -r worker_requirements.txt

# copy source code
COPY backend/ /app/
COPY worker/ /worker/

EXPOSE 8000

# 4 workers for prod, no --reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]