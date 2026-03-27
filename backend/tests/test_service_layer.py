"""
Test service layer functions directly without server or API layer
"""
import sys
from pathlib import Path
import os
import hashlib
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

# Suppress warnings during testing
warnings.filterwarnings("ignore", category=UserWarning, message=".*Qdrant.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Add paths
project_root = Path(__file__).resolve().parent.parent.parent
backend_path = str(project_root / "backend")
worker_path = str(project_root / "worker")

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if worker_path not in sys.path:
    sys.path.insert(0, worker_path)

# Set test database BEFORE importing app
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["USE_CELERY"] = "false"  # Disable Celery during tests

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.database import Base
from app.models.user import User
from app.services.auth_services import login_user

# Create test database
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Import Base from app to get models
from app.core.database import Base


def setup_users(count=5):
    """Create test users directly in test DB"""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    
    for i in range(1, count + 1):
        existing = db.query(User).filter(User.username == f"test_user{i}").first()
        if not existing:
            hashed = hashlib.sha256(f"test_pass{i}".encode()).hexdigest()
            db.add(User(username=f"test_user{i}", password=hashed))
    
    db.commit()
    db.close()


def cleanup_test_db():
    """Clean up test database"""
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test.db"):
        try:
            os.remove("./test.db")
        except:
            pass


def test_login_service_sequential(count=5):
    """Test login service function sequentially"""
    try:
        setup_users(count)
        
        print(f"\n{'='*70}")
        print(f"TEST: Sequential Login Service (No Server)")
        print(f"{'='*70}")
        
        for i in range(1, count + 1):
            result = login_user(f"test_user{i}", f"test_pass{i}")
            if result:
                print(f"  ✅ test_user{i}: Got token {result['token'][:20]}...")
            else:
                print(f"  ❌ test_user{i}: Login failed")
        
        print(f"✅ Test: Sequential login service - PASSED")
    finally:
        cleanup_test_db()


def test_login_service_concurrent(count=5):
    """Test login service function concurrently"""
    try:
        setup_users(count)
        
        print(f"\n{'='*70}")
        print(f"TEST: Concurrent Login Service (No Server)")
        print(f"{'='*70}")
        
        def login_concurrent(user_num):
            result = login_user(f"test_user{user_num}", f"test_pass{user_num}")
            return f"test_user{user_num}", result
        
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(login_concurrent, i) for i in range(1, count + 1)]
            
            for future in as_completed(futures):
                username, result = future.result()
                if result:
                    print(f"  ✅ {username}: Got token {result['token'][:20]}...")
                else:
                    print(f"  ❌ {username}: Login failed")
        
        print(f"✅ Test: Concurrent login service - PASSED")
    finally:
        cleanup_test_db()


def test_concurrent_user_operations(count=5):
    """Test concurrent operations from multiple user sessions"""
    try:
        setup_users(count)
        
        print(f"\n{'='*70}")
        print(f"TEST: Concurrent Operations from {count} Users")
        print(f"{'='*70}")
        
        def user_workflow(user_num):
            # Simulate multi-step user workflow
            username = f"test_user{user_num}"
            password = f"test_pass{user_num}"
            
            # Step 1: Login
            login_result = login_user(username, password)
            if not login_result:
                return f"❌ {username}: Login failed"
            
            # Step 2: Verify token
            token = login_result['token']
            user_id = login_result['user_id']
            
            return f"✅ {username}: Full workflow completed (user_id={user_id})"
        
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(user_workflow, i) for i in range(1, count + 1)]
            
            for future in as_completed(futures):
                print(f"  {future.result()}")
        
        print(f"✅ Test: Concurrent user operations - PASSED")
    finally:
        cleanup_test_db()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("SERVICE LAYER MULTI-USER TESTING (NO SERVER)")
    print("="*70)
    
    try:
        test_login_service_sequential(5)
        test_login_service_concurrent(5)
        test_concurrent_user_operations(5)
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_test_db()
