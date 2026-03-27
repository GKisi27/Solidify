"""
pytest configuration for multi-user testing
Place this in: backend/tests/conftest.py
"""

import sys
from pathlib import Path
import os
import pytest
from fastapi.testclient import TestClient
import hashlib
import warnings

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
from app.main import app
from app.models.user import User

# Create test database
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Import Base from app to get models
from app.core.database import Base


@pytest.fixture(scope="session")
def test_client():
    """Provide TestClient for all tests"""
    return TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Provide database session for tests"""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def test_users(db_session):
    """Create multiple test users"""
    users = []
    for i in range(1, 6):  # Create 5 users
        hashed = hashlib.sha256(f"pass{i}".encode()).hexdigest()
        user = User(username=f"testuser{i}", password=hashed)
        db_session.add(user)
        users.append({"username": f"testuser{i}", "password": f"pass{i}"})
    
    db_session.commit()
    return users


@pytest.fixture
def auth_tokens(test_client, test_users):
    """Obtain auth tokens for all test users"""
    tokens = {}
    for user in test_users:
        response = test_client.post(
            "/auth/login",
            data={"username": user["username"], "password": user["password"]}
        )
        if response.status_code == 200:
            tokens[user["username"]] = response.json()["access_token"]
    
    return tokens


@pytest.fixture
def authenticated_headers_list(auth_tokens):
    """Provide list of authenticated headers for concurrent testing"""
    return [
        {"Authorization": f"Bearer {token}"}
        for token in auth_tokens.values()
    ]
