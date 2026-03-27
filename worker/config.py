"""
Configuration settings for Celery worker.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class CeleryConfig:
    """Celery configuration class."""
    
    # Broker settings
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    
    # Task settings
    task_serializer = "json"
    accept_content = ["json"]
    result_serializer = "json"
    timezone = "UTC"
    enable_utc = True
    
    # Performance settings
    worker_prefetch_multiplier = 1
    worker_max_tasks_per_child = 50
    
    # Task execution settings
    task_track_started = True
    task_time_limit = 3600  # 1 hour
    task_soft_time_limit = 3300  # 55 minutes
    task_acks_late = True
    task_reject_on_worker_lost = True
    
    # Result backend settings
    result_expires = 86400  # 24 hours
    result_persistent = True
    
    # Retry settings
    task_default_retry_delay = 60  # 1 minute
    task_max_retries = 3
    
    # Connection settings
    broker_connection_retry_on_startup = True
    broker_connection_retry = True
    broker_connection_max_retries = 10
