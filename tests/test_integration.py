"""
Integration tests for the QA Data Generation pipeline
"""
import pytest
import pytest_asyncio
import tempfile
import json
import os
from unittest.mock import AsyncMock, patch

from lib.workflow import Pipeline
from lib.storage import Storage
from lib.pipeline import Pipeline as LegacyPipeline
from models import Record, RecordStatus, SeedInput, GenerationConfig


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


class TestWorkflowIntegration:
    """Test complete workflow pipeline execution"""
    
    @pytest.mark.asyncio
    async def test_simple_transformation_pipeline(self):
        """Test a pipeline with just transformation blocks"""
        pipeline_def = {
            "name": "Text Processing Pipeline",
            "blocks": [
                {"type": "TransformerBlock", "config": {"operation": "strip"}},
                {"type": "TransformerBlock", "config": {"operation": "lowercase"}},
                {"type": "ValidatorBlock", "config": {"min_length": 3}}
            ]
        }
        
        pipeline = Pipeline.load_from_dict(pipeline_def)

        input_data = {"text": "  HELLO WORLD  "}
        result, trace = await pipeline.execute(input_data)

        assert result["text"] == "hello world"
        assert result["valid"] is True
        assert len(trace) == 3
    
    @pytest.mark.asyncio
    async def test_validation_failure_pipeline(self):
        """Test pipeline where validation fails"""
        pipeline_def = {
            "name": "Strict Validation Pipeline",
            "blocks": [
                {"type": "TransformerBlock", "config": {"operation": "strip"}},
                {"type": "ValidatorBlock", "config": {"min_length": 100}}  # very strict
            ]
        }
        
        pipeline = Pipeline.load_from_dict(pipeline_def)

        input_data = {"text": "short"}
        result, trace = await pipeline.execute(input_data)

        assert result["text"] == "short"
        assert result["valid"] is False
    
    @pytest.mark.asyncio
    async def test_pipeline_with_mocked_llm(self):
        """Test pipeline that includes LLM block with mocked response"""
        pipeline_def = {
            "name": "LLM Pipeline",
            "blocks": [
                {"type": "LLMBlock", "config": {"model": "test-model"}},
                {"type": "ValidatorBlock", "config": {"min_length": 5}}
            ]
        }

        pipeline = Pipeline.load_from_dict(pipeline_def)

        # mock generator class
        with patch('lib.blocks.builtin.llm.Generator') as MockGenerator:
            mock_instance = MockGenerator.return_value
            mock_instance.generate = AsyncMock(return_value="This is a test response from LLM")

            input_data = {
                "system": "You are helpful",
                "user": "Say hello"
            }

            result, trace = await pipeline.execute(input_data)

            assert result["assistant"] == "This is a test response from LLM"
            assert result["valid"] is True
            assert len(trace) == 2
            mock_instance.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pipeline_data_flow(self):
        """Test that data flows correctly between blocks"""
        pipeline_def = {
            "name": "Data Flow Pipeline",
            "blocks": [
                {"type": "TransformerBlock", "config": {"operation": "uppercase"}},
                {"type": "TransformerBlock", "config": {"operation": "trim"}},
            ]
        }
        
        pipeline = Pipeline.load_from_dict(pipeline_def)
        
        input_data = {
            "text": "  hello   world  ",
            "metadata": {"test": "preserved"}
        }
        
        result, trace = await pipeline.execute(input_data)

        # text should be uppercase and trimmed
        assert result["text"] == "HELLO WORLD"
        # metadata should be preserved in accumulated state
        assert result["metadata"] == {"test": "preserved"}


class TestStoragePipelineIntegration:
    """Test integration between storage and pipeline systems"""
    
    @pytest.mark.asyncio
    async def test_save_and_execute_pipeline(self, storage):
        """Test saving a pipeline and executing it"""
        pipeline_def = {
            "name": "Stored Pipeline",
            "blocks": [
                {"type": "TransformerBlock", "config": {"operation": "lowercase"}},
                {"type": "ValidatorBlock", "config": {"min_length": 3}}
            ]
        }
        
        # save pipeline
        pipeline_id = await storage.save_pipeline("Test Pipeline", pipeline_def)
        assert pipeline_id > 0
        
        # retrieve and execute
        stored_pipeline_data = await storage.get_pipeline(pipeline_id)
        assert stored_pipeline_data is not None
        
        pipeline = Pipeline.load_from_dict(stored_pipeline_data["definition"])
        
        input_data = {"text": "HELLO"}
        result, trace = await pipeline.execute(input_data)

        assert result["text"] == "hello"
        assert result["valid"] is True
    
    @pytest.mark.asyncio
    async def test_record_creation_with_pipeline_id(self, storage):
        """Test creating records linked to pipelines"""
        # create a pipeline
        pipeline_def = {"name": "Test", "blocks": []}
        pipeline_id = await storage.save_pipeline("Test Pipeline", pipeline_def)
        
        # create records linked to this pipeline
        records = [
            Record(
                system="sys1", user="user1", assistant="assist1",
                status=RecordStatus.PENDING
            ),
            Record(
                system="sys2", user="user2", assistant="assist2", 
                status=RecordStatus.ACCEPTED
            )
        ]
        
        record_ids = []
        for record in records:
            record_id = await storage.save_record(record, pipeline_id=pipeline_id)
            record_ids.append(record_id)
        
        # verify records can be retrieved
        for record_id in record_ids:
            retrieved = await storage.get_by_id(record_id)
            assert retrieved is not None
        
        # verify pipeline still exists
        pipeline = await storage.get_pipeline(pipeline_id)
        assert pipeline is not None


class TestLegacyPipelineIntegration:
    """Test integration with legacy pipeline system"""
    
    @pytest.mark.asyncio
    async def test_legacy_pipeline_with_mocked_generation(self, storage):
        """Test the legacy pipeline system with mocked LLM"""
        pipeline = LegacyPipeline(storage)
        
        # create a temporary seed file
        seed_data = {
            "system": "You are a {role}",
            "user": "Explain {topic}",
            "metadata": {
                "role": "teacher",
                "topic": "photosynthesis", 
                "num_samples": 2
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(seed_data, f)
            seed_file = f.name
        
        try:
            # mock the generator in the pipeline
            with patch.object(pipeline.generator, 'generate', new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = "Photosynthesis is the process by which plants make food using sunlight."
                
                config = GenerationConfig(model="test-model")
                result = await pipeline.process_seed_file(seed_file, config)
                
                assert "success" in result
                assert result["success"] is True
                assert "generated" in result
                assert result["generated"] == 2  # num_samples
                
                # verify records were created
                records = await storage.get_all()
                assert len(records) >= 2
                
                # check that system/user prompts were filled
                for record in records[-2:]:  # last 2 records
                    assert "teacher" in record.system
                    assert "photosynthesis" in record.user
                    assert record.assistant == "Photosynthesis is the process by which plants make food using sunlight."
        finally:
            os.unlink(seed_file)
    
    @pytest.mark.asyncio
    async def test_legacy_pipeline_validation_integration(self, storage):
        """Test legacy pipeline with validation"""
        pipeline = LegacyPipeline(storage)
        
        # create seed with validation metadata
        seed_data = {
            "system": "Be concise",
            "user": "Say hi",
            "metadata": {
                "num_samples": 1,
                "min_length": 20  # require longer responses
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(seed_data, f)
            seed_file = f.name
        
        try:
            with patch.object(pipeline.generator, 'generate', new_callable=AsyncMock) as mock_generate:
                # mock short response that should fail validation
                mock_generate.return_value = "Hi"
                
                result = await pipeline.process_seed_file(seed_file)
                
                # check that generation succeeded but validation might have failed
                assert "success" in result
                records = await storage.get_all()
                
                # find the record we just created
                latest_record = records[-1] if records else None
                assert latest_record is not None
                assert latest_record.assistant == "Hi"
        finally:
            os.unlink(seed_file)


class TestEndToEndWorkflow:
    """Test complete end-to-end scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_qa_generation_workflow(self, storage):
        """Test a complete QA generation workflow"""
        # 1. Create a processing pipeline
        pipeline_def = {
            "name": "QA Processing Pipeline",
            "blocks": [
                {"type": "LLMBlock", "config": {"model": "test-model"}},
                {"type": "TransformerBlock", "config": {"operation": "trim"}},
                {"type": "ValidatorBlock", "config": {"min_length": 10}}
            ]
        }
        
        pipeline_id = await storage.save_pipeline("QA Pipeline", pipeline_def)
        
        # 2. Create seed input
        seed = SeedInput(
            system="You are an expert in {subject}",
            user="Explain {concept} to a {level} student",
            metadata={
                "subject": "biology",
                "concept": "mitosis",
                "level": "high school",
                "num_samples": 1
            }
        )
        
        # 3. Execute pipeline (with mocked LLM)
        pipeline = Pipeline.load_from_dict(pipeline_def)
        llm_block = None
        for block in pipeline.blocks:
            if hasattr(block, 'generator'):
                llm_block = block
                break
        
        with patch.object(llm_block.generator, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "  Mitosis is the process of cell division that results in two identical daughter cells.  "
            
            # fill templates
            filled_system = seed.system.format(**seed.metadata)
            filled_user = seed.user.format(**seed.metadata)
            
            input_data = {
                "system": filled_system,
                "user": filled_user
            }
            
            result, trace = await pipeline.execute(input_data)

            # 4. Create and save record with results
            record = Record(
                system=input_data["system"],
                user=input_data["user"],
                assistant=result["assistant"],
                metadata=seed.metadata,
                status=RecordStatus.ACCEPTED if result.get("valid", True) else RecordStatus.REJECTED
            )
            
            record_id = await storage.save_record(record, pipeline_id=pipeline_id)
            
            # 5. Verify the complete workflow
            saved_record = await storage.get_by_id(record_id)
            assert saved_record is not None
            assert "biology" in saved_record.system
            assert "mitosis" in saved_record.user
            assert "cell division" in saved_record.assistant
            assert saved_record.assistant == "Mitosis is the process of cell division that results in two identical daughter cells."  # trimmed
            assert saved_record.status == RecordStatus.ACCEPTED
            
            # 6. Verify pipeline association
            pipeline_data = await storage.get_pipeline(pipeline_id)
            assert pipeline_data is not None
            assert pipeline_data["name"] == "QA Pipeline"
    
    @pytest.mark.asyncio 
    async def test_batch_processing_workflow(self, storage):
        """Test processing multiple records in batch"""
        # create a simple pipeline
        pipeline_def = {
            "name": "Batch Pipeline",
            "blocks": [
                {"type": "TransformerBlock", "config": {"operation": "uppercase"}},
                {"type": "ValidatorBlock", "config": {"min_length": 3}}
            ]
        }
        
        pipeline = Pipeline.load_from_dict(pipeline_def)
        
        # process multiple inputs
        inputs = [
            {"text": "hello"},
            {"text": "world"}, 
            {"text": "test"},
            {"text": "hi"}  # might fail validation depending on validator
        ]
        
        results = []
        for input_data in inputs:
            result, trace = await pipeline.execute(input_data)
            results.append(result)
        
        # verify all were processed
        assert len(results) == 4
        
        # verify transformations applied
        for result in results:
            assert result["text"].isupper()
            assert "valid" in result
        
        # create records from results
        record_ids = []
        for i, result in enumerate(results):
            record = Record(
                system="test",
                user=f"input {i}",
                assistant=result["text"],
                status=RecordStatus.ACCEPTED if result["valid"] else RecordStatus.REJECTED
            )
            record_id = await storage.save_record(record)
            record_ids.append(record_id)
        
        # verify all records saved
        assert len(record_ids) == 4
        
        # verify records can be retrieved
        for record_id in record_ids:
            record = await storage.get_by_id(record_id)
            assert record is not None