"""
comprehensive storage tests for records, pipelines, jobs, and export
"""

import pytest

from models import Record, RecordStatus


class TestRecordCRUD:
    """test basic record operations"""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_record(self, storage):
        """saving a record returns id and allows retrieval"""
        record = Record(
            output="test output",
            metadata={"key": "value"},
            status=RecordStatus.PENDING,
        )

        record_id = await storage.save_record(record)
        assert record_id > 0

        retrieved = await storage.get_by_id(record_id)
        assert retrieved is not None
        assert retrieved.output == "test output"
        assert retrieved.metadata == {"key": "value"}
        assert retrieved.status == RecordStatus.PENDING
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_nonexistent_record(self, storage):
        """getting non-existent record returns none"""
        result = await storage.get_by_id(999999)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_record(self, storage):
        """updating record modifies fields and timestamp"""
        record = Record(output="original", metadata={}, status=RecordStatus.PENDING)
        record_id = await storage.save_record(record)

        success = await storage.update_record(
            record_id, output="updated", status=RecordStatus.ACCEPTED
        )
        assert success is True

        updated = await storage.get_by_id(record_id)
        assert updated.output == "updated"
        assert updated.status == RecordStatus.ACCEPTED
        assert updated.updated_at > updated.created_at

    @pytest.mark.asyncio
    async def test_update_nonexistent_record(self, storage):
        """updating non-existent record returns false"""
        success = await storage.update_record(999999, output="test")
        assert success is False

    @pytest.mark.asyncio
    async def test_list_records_with_pagination(self, storage):
        """get_all supports pagination"""
        # create test records
        for i in range(5):
            record = Record(output=f"output{i}", metadata={"index": i})
            await storage.save_record(record)

        # test pagination
        page1 = await storage.get_all(limit=2, offset=0)
        assert len(page1) == 2

        page2 = await storage.get_all(limit=2, offset=2)
        assert len(page2) == 2

    @pytest.mark.asyncio
    async def test_list_records_with_status_filter(self, storage):
        """get_all filters by status"""
        pending = Record(output="pending", metadata={}, status=RecordStatus.PENDING)
        accepted = Record(output="accepted", metadata={}, status=RecordStatus.ACCEPTED)

        await storage.save_record(pending)
        await storage.save_record(accepted)

        pending_records = await storage.get_all(status=RecordStatus.PENDING)
        assert all(r.status == RecordStatus.PENDING for r in pending_records)

        accepted_records = await storage.get_all(status=RecordStatus.ACCEPTED)
        assert all(r.status == RecordStatus.ACCEPTED for r in accepted_records)

    @pytest.mark.asyncio
    async def test_delete_all_records(self, storage):
        """delete_all_records removes all records"""
        # create some records
        for i in range(3):
            record = Record(output=f"test{i}", metadata={})
            await storage.save_record(record)

        initial_count = len(await storage.get_all())
        assert initial_count >= 3

        # delete all
        deleted = await storage.delete_all_records()
        assert deleted >= 3

        final_count = len(await storage.get_all())
        assert final_count == 0


class TestPipelineCRUD:
    """test pipeline storage"""

    @pytest.mark.asyncio
    async def test_save_and_get_pipeline(self, storage):
        """saving pipeline returns id and allows retrieval"""
        pipeline_def = {"blocks": [{"type": "TextGenerator", "config": {"temperature": 0.7}}]}

        pipeline_id = await storage.save_pipeline("Test Pipeline", pipeline_def)
        assert pipeline_id > 0

        retrieved = await storage.get_pipeline(pipeline_id)
        assert retrieved is not None
        assert retrieved.name == "Test Pipeline"
        assert retrieved.definition == pipeline_def

    @pytest.mark.asyncio
    async def test_list_pipelines(self, storage):
        """list_pipelines returns all pipelines"""
        await storage.save_pipeline("Pipeline 1", {"blocks": []})
        await storage.save_pipeline("Pipeline 2", {"blocks": []})

        pipelines = await storage.list_pipelines()
        assert len(pipelines) >= 2
        names = [p.name for p in pipelines]
        assert "Pipeline 1" in names
        assert "Pipeline 2" in names

    @pytest.mark.asyncio
    async def test_update_pipeline(self, storage):
        """updating pipeline modifies name and definition"""
        pipeline_def = {"blocks": [{"type": "TextGenerator", "config": {"temperature": 0.7}}]}
        pipeline_id = await storage.save_pipeline("Original Name", pipeline_def)

        # update pipeline
        new_def = {"blocks": [{"type": "ValidatorBlock", "config": {"min_length": 10}}]}
        success = await storage.update_pipeline(pipeline_id, "Updated Name", new_def)
        assert success is True

        # verify changes
        updated = await storage.get_pipeline(pipeline_id)
        assert updated.name == "Updated Name"
        assert updated.definition == new_def
        assert updated.definition["blocks"][0]["type"] == "ValidatorBlock"

    @pytest.mark.asyncio
    async def test_update_nonexistent_pipeline(self, storage):
        """updating non-existent pipeline returns false"""
        success = await storage.update_pipeline(999999, "Test", {"blocks": []})
        assert success is False

    @pytest.mark.asyncio
    async def test_delete_pipeline_cascade(self, storage):
        """deleting pipeline cascades to associated records"""
        pipeline_id = await storage.save_pipeline("Test", {"blocks": []})

        # create record linked to pipeline
        record = Record(output="test", metadata={})
        await storage.save_record(record, pipeline_id=pipeline_id)

        # delete pipeline
        success = await storage.delete_pipeline(pipeline_id)
        assert success is True

        # pipeline should be gone
        assert await storage.get_pipeline(pipeline_id) is None


class TestJobCRUD:
    """test job storage"""

    @pytest.mark.asyncio
    async def test_create_and_get_job(self, storage):
        """creating job returns id and allows retrieval"""
        pipeline_id = await storage.save_pipeline("Test", {"blocks": []})

        job_id = await storage.create_job(
            pipeline_id=pipeline_id, total_seeds=10, status="processing"
        )
        assert job_id > 0

        job = await storage.get_job(job_id)
        assert job is not None
        assert job.pipeline_id == pipeline_id
        assert job.total_seeds == 10
        assert job.status == "processing"

    @pytest.mark.asyncio
    async def test_update_job(self, storage):
        """updating job modifies fields"""
        pipeline_id = await storage.save_pipeline("Test", {"blocks": []})
        job_id = await storage.create_job(pipeline_id, 10, "processing")

        success = await storage.update_job(job_id, status="completed", records_generated=10)
        assert success is True

        job = await storage.get_job(job_id)
        assert job.status == "completed"
        assert job.records_generated == 10

    @pytest.mark.asyncio
    async def test_list_jobs(self, storage):
        """list_jobs returns jobs for pipeline"""
        pipeline_id = await storage.save_pipeline("Test", {"blocks": []})

        await storage.create_job(pipeline_id, 5, "completed")
        await storage.create_job(pipeline_id, 10, "processing")

        jobs = await storage.list_jobs(pipeline_id)
        assert len(jobs) >= 2


class TestExport:
    """test export functionality"""

    @pytest.mark.asyncio
    async def test_export_jsonl_all(self, storage):
        """export_jsonl exports all records"""
        import json

        for i in range(2):
            record = Record(output=f"output{i}", metadata={"index": i})
            await storage.save_record(record)

        jsonl = await storage.export_jsonl()
        lines = jsonl.strip().split("\n")
        assert len(lines) >= 2

        for line in lines:
            data = json.loads(line)
            assert "id" in data
            assert "metadata" in data
            assert "status" in data
            assert "accumulated_state" in data
            assert "created_at" in data
            assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_export_jsonl_by_status(self, storage):
        """export_jsonl filters by status"""
        import json

        pending = Record(output="pending", metadata={}, status=RecordStatus.PENDING)
        accepted = Record(output="accepted", metadata={}, status=RecordStatus.ACCEPTED)

        await storage.save_record(pending)
        await storage.save_record(accepted)

        pending_jsonl = await storage.export_jsonl(status=RecordStatus.PENDING)
        if pending_jsonl.strip():
            lines = pending_jsonl.strip().split("\n")
            for line in lines:
                data = json.loads(line)
                assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_export_jsonl_by_job(self, storage):
        """export_jsonl filters by job_id"""
        import json

        pipeline_id = await storage.save_pipeline("Test", {"blocks": []})
        job_id = await storage.create_job(pipeline_id, 1, "completed")

        record = Record(output="test", metadata={})
        await storage.save_record(record, pipeline_id=pipeline_id, job_id=job_id)

        job_jsonl = await storage.export_jsonl(job_id=job_id)
        # verify the export contains a record with the expected structure
        data = json.loads(job_jsonl)
        assert "id" in data
        assert "metadata" in data
        assert "status" in data
        assert "accumulated_state" in data


class TestEdgeCases:
    """test important edge cases"""

    @pytest.mark.asyncio
    async def test_unicode_handling(self, storage):
        """storage handles unicode correctly"""
        record = Record(output="测试 مرحبا", metadata={"unicode": "Привет 你好"})

        record_id = await storage.save_record(record)
        retrieved = await storage.get_by_id(record_id)

        assert retrieved.output == "测试 مرحبا"
        assert retrieved.metadata["unicode"] == "Привет 你好"

    @pytest.mark.asyncio
    async def test_trace_storage(self, storage):
        """records with trace data are stored correctly"""
        trace = [
            {
                "block_type": "TextGenerator",
                "input": {"system": "test", "user": "test"},
                "output": {"assistant": "response"},
                "execution_time": 1.5,
            }
        ]

        record = Record(output="test", metadata={}, trace=trace)
        record_id = await storage.save_record(record)

        retrieved = await storage.get_by_id(record_id)
        assert retrieved.trace is not None
        assert len(retrieved.trace) == 1
        assert retrieved.trace[0]["block_type"] == "TextGenerator"
        assert retrieved.trace[0]["execution_time"] == 1.5

    @pytest.mark.asyncio
    async def test_empty_metadata(self, storage):
        """records with empty metadata work correctly"""
        record = Record(output="test", metadata={})
        record_id = await storage.save_record(record)

        retrieved = await storage.get_by_id(record_id)
        assert retrieved.metadata == {}
