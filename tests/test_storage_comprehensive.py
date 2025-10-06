"""
Comprehensive tests for storage.py CRUD operations
"""
import pytest
import pytest_asyncio
import tempfile
import os
from datetime import datetime

from lib.storage import Storage
from models import Record, RecordStatus, RecordUpdate


@pytest_asyncio.fixture
async def storage():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    s = Storage(db_path)
    await s.init_db()
    yield s

    # cleanup
    try:
        os.unlink(db_path)
    except Exception:
        pass


class TestStorageRecords:
    """Test record CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_save_and_get_record(self, storage):
        """Test saving and retrieving a record"""
        record = Record(
            system="You are helpful",
            user="Hello",
            assistant="Hi there!",
            metadata={"test": "value"},
            status=RecordStatus.PENDING
        )
        
        record_id = await storage.save_record(record)
        assert record_id > 0
        
        retrieved = await storage.get_by_id(record_id)
        assert retrieved is not None
        assert retrieved.system == "You are helpful"
        assert retrieved.user == "Hello"
        assert retrieved.assistant == "Hi there!"
        assert retrieved.metadata == {"test": "value"}
        assert retrieved.status == RecordStatus.PENDING
        assert retrieved.id == record_id
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_record(self, storage):
        """Test getting a record that doesn't exist"""
        result = await storage.get_by_id(999999)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_records(self, storage):
        """Test getting all records with pagination"""
        # create some test records
        records = [
            Record(system="sys1", user="user1", assistant="assist1"),
            Record(system="sys2", user="user2", assistant="assist2"),
            Record(system="sys3", user="user3", assistant="assist3"),
        ]
        
        record_ids = []
        for record in records:
            record_id = await storage.save_record(record)
            record_ids.append(record_id)
        
        # test get all
        all_records = await storage.get_all()
        assert len(all_records) >= 3
        
        # test pagination
        page1 = await storage.get_all(limit=2, offset=0)
        assert len(page1) == 2
        
        page2 = await storage.get_all(limit=2, offset=2)
        assert len(page2) >= 1
    
    @pytest.mark.asyncio
    async def test_get_all_with_status_filter(self, storage):
        """Test getting records filtered by status"""
        # create records with different statuses
        pending_record = Record(
            system="sys", user="user", assistant="assist", 
            status=RecordStatus.PENDING
        )
        accepted_record = Record(
            system="sys", user="user", assistant="assist", 
            status=RecordStatus.ACCEPTED
        )
        
        await storage.save_record(pending_record)
        await storage.save_record(accepted_record)
        
        # test filtering
        pending_records = await storage.get_all(status=RecordStatus.PENDING)
        assert all(r.status == RecordStatus.PENDING for r in pending_records)
        
        accepted_records = await storage.get_all(status=RecordStatus.ACCEPTED)
        assert all(r.status == RecordStatus.ACCEPTED for r in accepted_records)
    
    @pytest.mark.asyncio
    async def test_update_record(self, storage):
        """Test updating a record"""
        # create initial record
        record = Record(
            system="original",
            user="original",
            assistant="original",
            status=RecordStatus.PENDING
        )
        record_id = await storage.save_record(record)
        
        # update the record
        update_data = RecordUpdate(
            system="updated system",
            assistant="updated assistant",
            status=RecordStatus.ACCEPTED
        )
        
        success = await storage.update_record(record_id, update_data)
        assert success is True
        
        # verify update
        updated = await storage.get_by_id(record_id)
        assert updated.system == "updated system"
        assert updated.user == "original"  # unchanged
        assert updated.assistant == "updated assistant"
        assert updated.status == RecordStatus.ACCEPTED
        assert updated.updated_at > updated.created_at
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_record(self, storage):
        """Test updating a record that doesn't exist"""
        update_data = RecordUpdate(system="test")
        success = await storage.update_record(999999, update_data)
        assert success is False
    
    @pytest.mark.asyncio
    async def test_delete_record(self, storage):
        """Test deleting a record"""
        record = Record(system="test", user="test", assistant="test")
        record_id = await storage.save_record(record)
        
        # verify record exists
        assert await storage.get_by_id(record_id) is not None
        
        # delete record
        success = await storage.delete_record(record_id)
        assert success is True
        
        # verify record is gone
        assert await storage.get_by_id(record_id) is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_record(self, storage):
        """Test deleting a record that doesn't exist"""
        success = await storage.delete_record(999999)
        assert success is False
    
    @pytest.mark.asyncio
    async def test_count_records(self, storage):
        """Test counting records"""
        initial_count = await storage.count_records()
        
        # add some records
        for i in range(3):
            record = Record(
                system=f"sys{i}",
                user=f"user{i}",
                assistant=f"assist{i}",
                status=RecordStatus.PENDING if i % 2 == 0 else RecordStatus.ACCEPTED
            )
            await storage.save_record(record)
        
        # test total count
        total_count = await storage.count_records()
        assert total_count == initial_count + 3
        
        # test count with status filter
        pending_count = await storage.count_records(status=RecordStatus.PENDING)
        accepted_count = await storage.count_records(status=RecordStatus.ACCEPTED)
        assert pending_count + accepted_count == 3
    
    @pytest.mark.asyncio
    async def test_export_jsonl(self, storage):
        """Test exporting records to JSONL format"""
        # create test records
        records = [
            Record(
                system="sys1", user="user1", assistant="assist1",
                metadata={"test": 1}, status=RecordStatus.PENDING
            ),
            Record(
                system="sys2", user="user2", assistant="assist2",
                metadata={"test": 2}, status=RecordStatus.ACCEPTED
            ),
        ]
        
        for record in records:
            await storage.save_record(record)
        
        # export all records
        jsonl_output = await storage.export_jsonl()
        lines = jsonl_output.strip().split('\n')
        assert len(lines) >= 2
        
        # check that each line is valid JSON
        import json
        for line in lines:
            data = json.loads(line)
            assert "id" in data
            assert "system" in data
            assert "user" in data
            assert "assistant" in data
            assert "metadata" in data
            assert "status" in data
        
        # export with status filter
        pending_jsonl = await storage.export_jsonl(status=RecordStatus.PENDING)
        pending_lines = pending_jsonl.strip().split('\n') if pending_jsonl.strip() else []
        
        # verify only pending records are exported
        for line in pending_lines:
            data = json.loads(line)
            assert data["status"] == "pending"


class TestStorageEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_record_with_empty_metadata(self, storage):
        """Test record with empty metadata"""
        record = Record(
            system="test", user="test", assistant="test",
            metadata={}
        )
        record_id = await storage.save_record(record)
        retrieved = await storage.get_by_id(record_id)
        assert retrieved.metadata == {}
    
    @pytest.mark.asyncio
    async def test_record_with_complex_metadata(self, storage):
        """Test record with complex metadata"""
        complex_metadata = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "boolean": True,
            "null": None,
            "unicode": "测试",
        }
        
        record = Record(
            system="test", user="test", assistant="test",
            metadata=complex_metadata
        )
        record_id = await storage.save_record(record)
        retrieved = await storage.get_by_id(record_id)
        assert retrieved.metadata == complex_metadata
    
    @pytest.mark.asyncio
    async def test_record_with_long_text(self, storage):
        """Test record with very long text fields"""
        long_text = "A" * 10000  # 10KB of text
        
        record = Record(
            system=long_text,
            user=long_text,
            assistant=long_text
        )
        record_id = await storage.save_record(record)
        retrieved = await storage.get_by_id(record_id)
        assert retrieved.system == long_text
        assert retrieved.user == long_text
        assert retrieved.assistant == long_text
    
    @pytest.mark.asyncio
    async def test_database_file_permissions(self):
        """Test handling of database file permissions"""
        # test with read-only directory (if possible)
        import tempfile
        import stat
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            # create and initialize database
            storage = Storage(db_path)
            await storage.init_db()
            
            # verify database file was created
            assert os.path.exists(db_path)
            
            # test basic operations work
            record = Record(system="test", user="test", assistant="test")
            record_id = await storage.save_record(record)
            assert record_id > 0


class TestStorageConcurrency:
    """Test concurrent operations (simplified)"""
    
    @pytest.mark.asyncio
    async def test_concurrent_record_creation(self, storage):
        """Test creating multiple records concurrently"""
        import asyncio
        
        async def create_record(i):
            record = Record(
                system=f"sys{i}",
                user=f"user{i}",
                assistant=f"assist{i}"
            )
            return await storage.save_record(record)
        
        # create 5 records concurrently
        tasks = [create_record(i) for i in range(5)]
        record_ids = await asyncio.gather(*tasks)
        
        # verify all records were created with unique IDs
        assert len(record_ids) == 5
        assert len(set(record_ids)) == 5  # all unique
        assert all(rid > 0 for rid in record_ids)
        
        # verify all records can be retrieved
        for record_id in record_ids:
            record = await storage.get_by_id(record_id)
            assert record is not None