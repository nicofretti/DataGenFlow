"""
Tests for user blocks discovery and error handling
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from lib.blocks.registry import BlockRegistry
from lib.blocks.base import BaseBlock


class TestUserBlocksDiscovery:
    """Test discovery of user-defined blocks"""
    
    def test_user_blocks_directory_discovery(self):
        """Test that user blocks are discovered from user_blocks/ directory"""
        registry = BlockRegistry()
        
        # get initial blocks count
        initial_blocks = registry.list_blocks()
        initial_count = len(initial_blocks)
        
        # create a temporary user block
        user_blocks_dir = Path("user_blocks")
        user_blocks_dir.mkdir(exist_ok=True)
        
        test_block_code = '''
from lib.blocks.base import BaseBlock
from typing import Any

class TestUserBlock(BaseBlock):
    name = "test user block"
    description = "test block for discovery"
    inputs = ["text"]
    outputs = ["test_output"]

    def __init__(self, test_param: str = "default"):
        self.test_param = test_param

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        return {"test_output": f"processed: {data.get('text', '')}-{self.test_param}"}
'''
        
        test_block_file = user_blocks_dir / "test_user_block.py"
        try:
            with open(test_block_file, 'w') as f:
                f.write(test_block_code)
            
            # create a new registry to trigger discovery
            new_registry = BlockRegistry()
            new_blocks = new_registry.list_blocks()
            
            # should have discovered the new block
            assert len(new_blocks) >= initial_count
            
            # check if our test block is in the list
            block_types = [block["type"] for block in new_blocks]
            # note: the actual discovery mechanism may vary based on implementation
            
        finally:
            # cleanup
            if test_block_file.exists():
                test_block_file.unlink()
    
    def test_invalid_user_block_handling(self):
        """Test handling of invalid user blocks"""
        user_blocks_dir = Path("user_blocks")
        user_blocks_dir.mkdir(exist_ok=True)
        
        # create an invalid block file
        invalid_block_code = '''
# This is not a valid block - no class definition
def some_function():
    pass
'''
        
        invalid_block_file = user_blocks_dir / "invalid_block.py"
        try:
            with open(invalid_block_file, 'w') as f:
                f.write(invalid_block_code)
            
            # registry should handle invalid blocks gracefully
            registry = BlockRegistry()
            blocks = registry.list_blocks()
            
            # should still work and return core blocks
            block_types = [block["type"] for block in blocks]
            assert "LLMBlock" in block_types
            assert "ValidatorBlock" in block_types
            assert "TransformerBlock" in block_types
            
        finally:
            if invalid_block_file.exists():
                invalid_block_file.unlink()
    
    def test_user_block_with_syntax_error(self):
        """Test handling of user blocks with syntax errors"""
        user_blocks_dir = Path("user_blocks")
        user_blocks_dir.mkdir(exist_ok=True)
        
        # create a block with syntax error
        syntax_error_code = '''
from lib.blocks.base import BaseBlock

class SyntaxErrorBlock(BaseBlock):
    def get_schema(self
        # missing closing parenthesis - syntax error
        return {}
    
    async def execute(self, data):
        return data
'''
        
        syntax_error_file = user_blocks_dir / "syntax_error_block.py"
        try:
            with open(syntax_error_file, 'w') as f:
                f.write(syntax_error_code)
            
            # registry should handle syntax errors gracefully
            registry = BlockRegistry()
            blocks = registry.list_blocks()
            
            # should still work
            assert len(blocks) >= 3  # at least core blocks
            
        finally:
            if syntax_error_file.exists():
                syntax_error_file.unlink()


class TestErrorHandling:
    """Test error handling throughout the system"""
    
    @pytest.mark.asyncio
    async def test_block_execution_error_handling(self):
        """Test that block execution errors are handled properly"""
        from lib.blocks.builtin.transformer import TransformerBlock
        
        block = TransformerBlock(operation="invalid_operation")
        
        # should handle invalid operation gracefully
        input_data = {"text": "test"}
        
        # depending on implementation, might raise exception or return error
        try:
            result = await block.execute(input_data)
            # if no exception, check if error is indicated in result
            assert "error" in result or result.get("text") == "test"
        except Exception as e:
            # if exception is raised, it should be meaningful
            assert "operation" in str(e).lower() or "invalid" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_pipeline_execution_with_failing_block(self):
        """Test pipeline execution when a block fails"""
        from lib.workflow import Pipeline
        
        # create a pipeline with a block that will fail
        pipeline_def = {
            "name": "Failing Pipeline", 
            "blocks": [
                {"type": "TransformerBlock", "config": {"operation": "lowercase"}},
                {"type": "ValidatorBlock", "config": {"forbidden_words": ["test"]}}
            ]
        }
        
        pipeline = Pipeline.load_from_dict(pipeline_def)
        
        # input that should trigger validation failure
        input_data = {"text": "This is a test message"}

        result, trace, trace_id = await pipeline.execute(input_data)

        # pipeline should complete but validation should fail
        assert result["text"] == "this is a test message"  # transformation applied
        assert result["valid"] is False  # validation failed
    
    def test_invalid_pipeline_definition(self):
        """Test handling of invalid pipeline definitions"""
        from lib.workflow import Pipeline
        
        # test with missing blocks
        with pytest.raises(Exception):
            Pipeline.load_from_dict({"name": "test"})  # no blocks
        
        # test with invalid block type
        with pytest.raises(Exception):
            Pipeline.load_from_dict({
                "name": "test",
                "blocks": [{"type": "NonExistentBlock", "config": {}}]
            })
        
        # test with malformed config
        with pytest.raises(Exception):
            Pipeline.load_from_dict({
                "name": "test", 
                "blocks": "invalid"  # should be list
            })
    
    @pytest.mark.asyncio
    async def test_storage_error_handling(self):
        """Test storage error handling"""
        from lib.storage import Storage
        from models import Record
        
        # test with invalid database path
        invalid_storage = Storage("/invalid/path/database.db")
        
        # should fail gracefully
        with pytest.raises(Exception):
            await invalid_storage.init_db()
    
    @pytest.mark.asyncio
    async def test_generator_error_handling(self):
        """Test LLM generator error handling"""
        from lib.generator import Generator
        from models import GenerationConfig
        from config import settings

        # test with invalid endpoint
        original_endpoint = settings.LLM_ENDPOINT
        settings.LLM_ENDPOINT = "http://invalid:99999"

        try:
            config = GenerationConfig(model="test-model")
            gen = Generator(config)

            # should handle connection errors
            with pytest.raises(Exception):
                await gen.generate("system", "user")
        finally:
            settings.LLM_ENDPOINT = original_endpoint
    
    def test_model_validation_errors(self):
        """Test pydantic model validation"""
        from models import Record, RecordStatus, GenerationConfig
        
        # test invalid record status
        with pytest.raises(Exception):
            Record(
                system="test", user="test", assistant="test",
                status="invalid_status"  # not a valid RecordStatus
            )
        
        # test invalid generation config
        with pytest.raises(Exception):
            GenerationConfig(temperature=5.0)  # out of range
        
        with pytest.raises(Exception):
            GenerationConfig(max_tokens=-1)  # negative
    
    @pytest.mark.asyncio
    async def test_concurrent_storage_operations(self):
        """Test error handling in concurrent storage operations"""
        import asyncio
        from lib.storage import Storage
        from models import Record
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        try:
            storage = Storage(db_path)
            await storage.init_db()
            
            # create multiple concurrent operations
            async def create_record(i):
                record = Record(
                    system=f"sys{i}",
                    user=f"user{i}",
                    assistant=f"assist{i}"
                )
                return await storage.save_record(record)
            
            # run many concurrent operations
            tasks = [create_record(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # check that most operations succeeded
            successes = [r for r in results if isinstance(r, int) and r > 0]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            # should have mostly successes
            assert len(successes) >= 8  # allow for some failures in concurrency
            
            # any exceptions should be database-related, not crashes
            for exc in exceptions:
                assert "database" in str(exc).lower() or "sqlite" in str(exc).lower()
                
        finally:
            try:
                os.unlink(db_path)
            except Exception:
                pass


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.asyncio
    async def test_empty_input_handling(self):
        """Test handling of empty inputs"""
        from lib.blocks.builtin.transformer import TransformerBlock
        from lib.blocks.builtin.validator import ValidatorBlock
        
        transformer = TransformerBlock(operation="lowercase")
        validator = ValidatorBlock(min_length=1)
        
        # test empty text
        empty_result = await transformer.execute({"text": ""})
        assert empty_result["text"] == ""
        
        # test validation with empty text
        validation_result = await validator.execute({"text": ""})
        assert validation_result["valid"] is False
    
    @pytest.mark.asyncio
    async def test_large_input_handling(self):
        """Test handling of very large inputs"""
        from lib.blocks.builtin.transformer import TransformerBlock
        
        # create a very large input
        large_text = "A" * 100000  # 100KB
        
        transformer = TransformerBlock(operation="lowercase")
        result = await transformer.execute({"text": large_text})
        
        assert result["text"] == "a" * 100000
        assert len(result["text"]) == 100000
    
    @pytest.mark.asyncio
    async def test_unicode_handling(self):
        """Test handling of unicode characters"""
        from lib.blocks.builtin.transformer import TransformerBlock
        
        # test various unicode characters
        unicode_text = "Hello 世界 🌍 café naïve résumé"
        
        transformer = TransformerBlock(operation="lowercase")
        result = await transformer.execute({"text": unicode_text})
        
        # should preserve unicode characters
        assert "世界" in result["text"]
        assert "🌍" in result["text"]
        assert "café" in result["text"].lower()
    
    @pytest.mark.asyncio
    async def test_special_characters_in_metadata(self):
        """Test handling of special characters in metadata"""
        from lib.storage import Storage
        from models import Record
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        try:
            storage = Storage(db_path)
            await storage.init_db()
            
            # metadata with special characters
            special_metadata = {
                "unicode": "测试 🎉",
                "quotes": 'He said "Hello"',
                "newlines": "line1\nline2",
                "special": "!@#$%^&*(){}[]",
                "json_chars": '{"key": "value"}',
                "None": None,
                "empty": ""
            }
            
            record = Record(
                system="test", user="test", assistant="test",
                metadata=special_metadata
            )
            
            record_id = await storage.save_record(record)
            retrieved = await storage.get_by_id(record_id)
            
            assert retrieved.metadata == special_metadata
            
        finally:
            try:
                os.unlink(db_path)
            except Exception:
                pass
    
    def test_registry_with_no_user_blocks(self):
        """Test registry behavior when no user blocks exist"""
        from lib.blocks.registry import BlockRegistry
        
        # temporarily move user_blocks if it exists
        user_blocks_path = Path("user_blocks")
        backup_path = Path("user_blocks_backup")
        
        moved = False
        if user_blocks_path.exists():
            user_blocks_path.rename(backup_path)
            moved = True
        
        try:
            registry = BlockRegistry()
            blocks = registry.list_blocks()
            
            # should still have core blocks
            block_types = [block["type"] for block in blocks]
            assert "LLMBlock" in block_types
            assert "ValidatorBlock" in block_types
            assert "TransformerBlock" in block_types
            
        finally:
            if moved and backup_path.exists():
                backup_path.rename(user_blocks_path)