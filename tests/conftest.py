"""
Test configuration and fixtures
"""

import os
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

# use test database file (not :memory: to avoid async threading issues)
os.environ["DATABASE_PATH"] = "data/test_qa_records.db"
os.environ["DEBUG"] = "false"


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """clean up test database before and after test session"""
    test_db = Path("data/test_qa_records.db")
    if test_db.exists():
        test_db.unlink()
    yield
    if test_db.exists():
        test_db.unlink()


@pytest.fixture(scope="function")
def client():
    """create test client with lifespan handling"""
    from app import app

    client = TestClient(app)
    yield client
    client.close()


@pytest.fixture
def sample_record():
    """sample record with new model structure"""
    from models import Record, RecordStatus

    return Record(
        output="test output", metadata={"test_key": "test_value"}, status=RecordStatus.PENDING
    )


@pytest.fixture
def sample_seed():
    """sample seed file data with new format"""
    return {
        "repetitions": 2,
        "metadata": {
            "system": "You are a {{ role }}.",
            "user": "Test question about {{ topic }}",
            "role": "teacher",
            "topic": "testing",
        },
    }


@pytest_asyncio.fixture
async def storage():
    """create storage for tests using test database"""
    from lib.storage import Storage

    storage = Storage("data/test_qa_records.db")
    await storage.init_db()
    yield storage

    # close database connection
    if hasattr(storage, 'conn') and storage.conn:
        await storage.conn.close()


@pytest.fixture
def sample_pipeline_def():
    """sample pipeline definition"""
    return {
        "name": "Test Pipeline",
        "blocks": [
            {"type": "TextGenerator", "config": {"temperature": 0.7}},
            {"type": "ValidatorBlock", "config": {"min_length": 10}},
        ],
    }
