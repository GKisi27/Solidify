"""
Celery application configuration for Solidify worker.
"""
import os
import sys
from pathlib import Path
from celery import Celery
from dotenv import load_dotenv

# Ensure proper module resolution for imports
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Load environment variables
load_dotenv()

# Initialize Celery app
celery_app = Celery(
    "solidify_worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    result_expires=86400,  # Results expire after 24 hours
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    broker_connection_retry_on_startup=True,
)

# Auto-discover tasks from the tasks module
celery_app.autodiscover_tasks(["worker.tasks"])

@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f"Request: {self.request!r}")
    return "Celery is working!"
