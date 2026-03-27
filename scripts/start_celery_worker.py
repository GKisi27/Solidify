#!/usr/bin/env python
"""
Celery Worker Startup Script
Run from project root: python start_celery_worker.py
"""
import os
import sys
from pathlib import Path

# Get project root (where this script is located)
project_root = Path(__file__).resolve().parent

# Add project root to Python path so 'worker' module can be found
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Change to project root directory
os.chdir(project_root)

print("=" * 70)
print("STARTING CELERY WORKER")
print("=" * 70)
print(f"Project root: {project_root}")
print(f"Working directory: {os.getcwd()}")
print(f"Python path includes: {project_root}")
print()

# Import and run Celery
try:
    from celery.bin import celery as celery_bin
    from worker.celery_app import celery_app
    
    print("✅ Celery app loaded successfully")
    print(f"   App: {celery_app.main}")
    print(f"   Broker: {celery_app.conf.broker_url}")
    print()
    print("Starting worker with 4 concurrent processes...")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    # Run the worker
    celery_bin.main(
        [
            'celery',
            'worker',
            '-A', 'worker.celery_app',
            '--loglevel=info',
            '--concurrency=4'
        ]
    )
    
except ImportError as e:
    print(f"❌ Failed to import Celery or worker module: {e}")
    print()
    print("Possible solutions:")
    print("1. Install dependencies: cd backend && pip install -r requirements.txt")
    print("2. Use Docker instead: docker-compose up -d")
    print()
    sys.exit(1)
except KeyboardInterrupt:
    print("\n\n✅ Celery worker stopped")
    sys.exit(0)
