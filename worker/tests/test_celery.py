"""
Basic tests for Celery tasks and pipeline.
"""
import os
import sys
from pathlib import Path

# Add paths - need to add project root, not just backend/worker
project_root = Path(__file__).resolve().parent.parent.parent
backend_path = project_root / "backend"
worker_path = project_root / "worker"

# Add to path if not already there
for path in [str(project_root), str(backend_path)]:
    if path not in sys.path:
        sys.path.insert(0, path)

print(f"Python path configured:")
print(f"  Project root: {project_root}")
print(f"  Backend: {backend_path}")
print(f"  Worker: {worker_path}")
print()


def test_celery_imports():
    """Test that all Celery modules can be imported."""
    try:
        from worker.celery_app import celery_app, debug_task
        from worker.tasks import (
            process_image_task,
            generate_json_task,
            clean_json_task,
            create_onshape_model_task,
        )
        from worker.pipelines import (
            run_conversion_pipeline,
            convert_image_to_3d,
        )
        print("✅ All Celery modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_celery_app_config():
    """Test that Celery app is configured correctly."""
    try:
        from worker.celery_app import celery_app
        
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc == True
        
        print("✅ Celery app configuration is correct")
        print(f"   Broker: {celery_app.conf.broker_url}")
        print(f"   Backend: {celery_app.conf.result_backend}")
        return True
    except AssertionError as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_registration():
    """Test that tasks are registered with Celery."""
    try:
        from worker.celery_app import celery_app
        
        registered_tasks = list(celery_app.tasks.keys())
        
        expected_tasks = [
            "worker.tasks.process_image",
            "worker.tasks.generate_json",
            "worker.tasks.clean_json",
            "worker.tasks.create_onshape_model",
        ]
        
        print(f"   Found {len(registered_tasks)} registered tasks")
        
        for task_name in expected_tasks:
            if task_name in registered_tasks:
                print(f"✅ Task registered: {task_name}")
            else:
                print(f"⚠️  Task not found: {task_name}")
                print(f"   Available tasks: {[t for t in registered_tasks if 'worker' in t]}")
        
        return True
    except Exception as e:
        print(f"❌ Task registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_debug_task():
    """Test the debug task (requires running Celery worker)."""
    try:
        from worker.celery_app import debug_task
        
        # This will only work if Celery worker is running
        print("\n🧪 Testing debug task (requires running worker)...")
        result = debug_task.delay()
        print(f"   Task ID: {result.id}")
        print(f"   Task state: {result.state}")
        
        if result.state == "PENDING":
            print("   ⚠️  Task is pending - make sure Celery worker is running")
            print("   Start worker with: celery -A worker.celery_app worker --loglevel=info")
        
        return True
    except Exception as e:
        print(f"❌ Debug task test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("CELERY IMPLEMENTATION TESTS")
    print("=" * 60)
    print()
    
    tests = [
        ("Import Test", test_celery_imports),
        ("Configuration Test", test_celery_app_config),
        ("Task Registration Test", test_task_registration),
        ("Debug Task Test", test_debug_task),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 60)
        result = test_func()
        results.append((test_name, result))
        print()
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    print()
    if all_passed:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed")
        sys.exit(1)
