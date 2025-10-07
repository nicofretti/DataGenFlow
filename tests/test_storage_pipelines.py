import os
import tempfile

import pytest

from lib.storage import Storage
from models import Record, RecordStatus


@pytest.mark.asyncio
async def test_save_and_get_pipeline():
    # use temporary file for testing
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    try:
        storage = Storage(db_path)
        await storage.init_db()

        pipeline_def = {
            "name": "Test Pipeline",
            "blocks": [
                {"type": "TransformerBlock", "config": {"operation": "lowercase"}}
            ],
        }

        pipeline_id = await storage.save_pipeline("Test Pipeline", pipeline_def)
        assert pipeline_id > 0

        retrieved = await storage.get_pipeline(pipeline_id)
        assert retrieved is not None
        assert retrieved["name"] == "Test Pipeline"
        assert retrieved["definition"] == pipeline_def
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


@pytest.mark.asyncio
async def test_list_pipelines():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    try:
        storage = Storage(db_path)
        await storage.init_db()

        await storage.save_pipeline("Pipeline 1", {"name": "Pipeline 1", "blocks": []})
        await storage.save_pipeline("Pipeline 2", {"name": "Pipeline 2", "blocks": []})

        pipelines = await storage.list_pipelines()
        assert len(pipelines) == 2
        assert pipelines[0]["name"] == "Pipeline 2"  # ordered by created_at desc
        assert pipelines[1]["name"] == "Pipeline 1"
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


@pytest.mark.asyncio
async def test_delete_pipeline():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    try:
        storage = Storage(db_path)
        await storage.init_db()

        pipeline_id = await storage.save_pipeline(
            "Test", {"name": "Test", "blocks": []}
        )

        deleted = await storage.delete_pipeline(pipeline_id)
        assert deleted is True

        retrieved = await storage.get_pipeline(pipeline_id)
        assert retrieved is None
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


@pytest.mark.asyncio
async def test_save_record_with_pipeline_id():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    try:
        storage = Storage(db_path)
        await storage.init_db()

        pipeline_id = await storage.save_pipeline(
            "Test", {"name": "Test", "blocks": []}
        )

        record = Record(
            system="test system",
            user="test user",
            assistant="test assistant",
            metadata={},
            status=RecordStatus.PENDING,
        )

        record_id = await storage.save_record(record, pipeline_id=pipeline_id)
        assert record_id > 0

        # verify pipeline_id is stored (would need to add getter for this)
        retrieved = await storage.get_by_id(record_id)
        assert retrieved is not None
    finally:
        try:
            os.unlink(db_path)
        except:
            pass
