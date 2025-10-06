"""
Test configuration and fixtures
"""
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


# Set test environment before any imports
os.environ["DATABASE_PATH"] = "data/test_qa_records.db"
os.environ["DEBUG"] = "false"


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """Clean up test database before and after test session"""
    test_db = Path("data/test_qa_records.db")

    # Remove test database before tests
    if test_db.exists():
        test_db.unlink()

    yield

    # Remove test database after tests
    if test_db.exists():
        test_db.unlink()


@pytest.fixture(scope="function")
def client():
    """Create test client with lifespan handling"""
    # Import app after env vars are set
    from app import app

    # TestClient handles lifespan events
    with TestClient(app) as client:
        yield client
