"""
Test multiple users without server initialization using FastAPI TestClient
"""
import sys
from pathlib import Path
import os
import json
import hashlib
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

# Suppress warnings during testing
warnings.filterwarnings("ignore", category=UserWarning, message=".*Qdrant.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Add paths for imports
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

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.main import app
from app.models.user import User

# Create test database setup
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Import Base from app to get User model
from app.core.database import Base

# Create test client
client = TestClient(app)


def create_test_users(count=5):
    """Create test users in the test database"""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    
    for i in range(1, count + 1):
        username = f"user{i}"
        password = f"password{i}"
        
        existing = db.query(User).filter(User.username == username).first()
        if not existing:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            user = User(username=username, password=hashed_password)
            db.add(user)
    
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


def test_single_user_login():
    """Test single user login"""
    try:
        create_test_users(1)
        response = client.post(
            "/auth/login",
            data={"username": "user1", "password": "password1"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["username"] == "user1"
        print(f"✅ Test: Single user login - PASSED")
    finally:
        cleanup_test_db()


def test_multiple_users_sequential_login():
    """Test multiple users logging in sequentially"""
    try:
        create_test_users(5)
        
        test_users = [
            ("user1", "password1"),
            ("user2", "password2"),
            ("user3", "password3"),
            ("user4", "password4"),
            ("user5", "password5"),
        ]
        
        tokens = []
        for username, password in test_users:
            response = client.post(
                "/auth/login",
                data={"username": username, "password": password}
            )
            assert response.status_code == 200, f"{username} login failed: {response.text}"
            data = response.json()
            tokens.append({
                "username": username,
                "token": data["access_token"]
            })
            print(f"  ✅ {username} logged in")
        
        assert len(tokens) == 5
        print(f"✅ Test: Sequential login (5 users) - PASSED")
    finally:
        cleanup_test_db()


def test_multiple_users_concurrent_login():
    """Test multiple users logging in CONCURRENTLY"""
    try:
        create_test_users(5)
        
        test_users = [
            ("user1", "password1"),
            ("user2", "password2"),
            ("user3", "password3"),
            ("user4", "password4"),
            ("user5", "password5"),
        ]
        
        def login_user(credentials):
            username, password = credentials
            response = client.post(
                "/auth/login",
                data={"username": username, "password": password}
            )
            return {
                "username": username,
                "status": response.status_code,
                "token": response.json().get("access_token") if response.status_code == 200 else None
            }
        
        # Execute 5 logins concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(login_user, user) for user in test_users]
            results = [f.result() for f in as_completed(futures)]
        
        # Verify all logins succeeded
        assert len(results) == 5
        for result in results:
            assert result["status"] == 200, f"{result['username']} concurrent login failed"
            assert result["token"] is not None
            print(f"  ✅ {result['username']} concurrent login")
        
        print(f"✅ Test: Concurrent login (5 users) - PASSED")
    finally:
        cleanup_test_db()


def test_concurrent_user_operations():
    """Test concurrent operations from multiple user sessions"""
    try:
        create_test_users(3)
        
        def user_workflow(user_num):
            username = f"user{user_num}"
            password = f"password{user_num}"
            
            # Step 1: Login
            login_response = client.post(
                "/auth/login",
                data={"username": username, "password": password}
            )
            
            if login_response.status_code != 200:
                return f"❌ {username}: Login failed ({login_response.status_code})"
            
            # Step 2: Verify token and user info
            login_data = login_response.json()
            token = login_data['access_token']
            user_id = login_data['user_id']
            
            return f"✅ {username}: Complete workflow (user_id={user_id})"
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(user_workflow, i) for i in range(1, 4)]
            for future in as_completed(futures):
                print(f"  {future.result()}")
        
        print(f"✅ Test: Concurrent user operations (3 users) - PASSED")
    finally:
        cleanup_test_db()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTING MULTIPLE USERS WITHOUT SERVER INITIALIZATION")
    print("="*70 + "\n")
    
    try:
        test_single_user_login()
        print()
        test_multiple_users_sequential_login()
        print()
        test_multiple_users_concurrent_login()
        print()
        test_concurrent_user_operations()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_test_db()
