"""
Tests for FastAPI endpoints in app.py
"""
import pytest
import tempfile
import json
import os
from pathlib import Path
from fastapi.testclient import TestClient

from app import app
from lib.storage import Storage


# test configuration to ensure we don't interfere with real data
@pytest.fixture
def temp_db():
    """Create a temporary database for API testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except Exception:
        pass


# client fixture now provided by conftest.py


@pytest.fixture
def sample_seed_file():
    """Create a sample seed file for testing"""
    seed_data = {
        "system": "You are a helpful assistant.",
        "user": "Explain {topic} in simple terms.",
        "metadata": {
            "topic": "machine learning",
            "num_samples": 2
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(seed_data, f)
        return f.name


class TestAPIBlocks:
    """Test block-related API endpoints"""
    
    def test_list_blocks(self, client):
        """Test GET /api/blocks"""
        response = client.get("/api/blocks")
        assert response.status_code == 200
        
        blocks = response.json()
        assert isinstance(blocks, list)
        assert len(blocks) >= 3  # at least the core blocks
        
        # check for expected core blocks
        block_types = [block["type"] for block in blocks]
        assert "LLMBlock" in block_types
        assert "ValidatorBlock" in block_types
        assert "TransformerBlock" in block_types
        
        # check block structure
        for block in blocks:
            assert "type" in block
            assert "name" in block
            assert "description" in block
            assert "inputs" in block
            assert "outputs" in block


class TestAPIPipelines:
    """Test pipeline-related API endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_pipeline(self, client):
        """Test POST /api/pipelines"""
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [
                {"type": "TransformerBlock", "config": {"operation": "lowercase"}},
                {"type": "ValidatorBlock", "config": {"min_length": 5}}
            ]
        }
        
        response = client.post("/api/pipelines", json=pipeline_data)
        assert response.status_code == 200
        
        result = response.json()
        assert "id" in result
        assert result["id"] > 0
    
    def test_list_pipelines(self, client):
        """Test GET /api/pipelines"""
        # first create a pipeline
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [{"type": "TransformerBlock", "config": {"operation": "lowercase"}}]
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        assert create_response.status_code == 200
        
        # then list pipelines
        response = client.get("/api/pipelines")
        assert response.status_code == 200
        
        pipelines = response.json()
        assert isinstance(pipelines, list)
        assert len(pipelines) >= 1
        
        # check pipeline structure
        for pipeline in pipelines:
            assert "id" in pipeline
            assert "name" in pipeline
            assert "definition" in pipeline
            assert "created_at" in pipeline
    
    def test_get_pipeline(self, client):
        """Test GET /api/pipelines/{id}"""
        # create a pipeline first
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [{"type": "TransformerBlock", "config": {"operation": "lowercase"}}]
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]
        
        # get the pipeline
        response = client.get(f"/api/pipelines/{pipeline_id}")
        assert response.status_code == 200
        
        pipeline = response.json()
        assert pipeline["id"] == pipeline_id
        assert pipeline["name"] == "Test Pipeline"
        assert "definition" in pipeline
    
    def test_get_nonexistent_pipeline(self, client):
        """Test GET /api/pipelines/{id} with invalid ID"""
        response = client.get("/api/pipelines/999999")
        assert response.status_code == 404
    
    def test_delete_pipeline(self, client):
        """Test DELETE /api/pipelines/{id}"""
        # create a pipeline first
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [{"type": "TransformerBlock", "config": {"operation": "lowercase"}}]
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]
        
        # delete the pipeline
        response = client.delete(f"/api/pipelines/{pipeline_id}")
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        
        # verify it's gone
        get_response = client.get(f"/api/pipelines/{pipeline_id}")
        assert get_response.status_code == 404
    
    def test_execute_pipeline(self, client):
        """Test POST /api/pipelines/{id}/execute"""
        # create a simple pipeline
        pipeline_data = {
            "name": "Transform Pipeline",
            "blocks": [{"type": "TransformerBlock", "config": {"operation": "uppercase"}}]
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]
        
        # execute the pipeline
        input_data = {"text": "hello world"}
        response = client.post(f"/api/pipelines/{pipeline_id}/execute", json=input_data)
        assert response.status_code == 200

        result = response.json()
        # api returns {result, trace}
        assert "result" in result
        assert "trace" in result
        assert result["result"]["text"] == "HELLO WORLD"


class TestAPIGeneration:
    """Test generation-related API endpoints"""
    
    def test_generate_with_invalid_file(self, client):
        """Test POST /api/generate with invalid file"""
        # test with non-JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as f:
            f.write("not json")
            f.flush()
            
            with open(f.name, 'rb') as test_file:
                response = client.post(
                    "/api/generate",
                    files={"file": ("test.txt", test_file, "text/plain")},
                    data={"pipeline_id": "1"}
                )
                assert response.status_code in [400, 422]  # either bad request or validation error
    
    def test_generate_with_malformed_json(self, client):
        """Test POST /api/generate with malformed JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
            f.write("{invalid json")
            f.flush()
            
            with open(f.name, 'rb') as test_file:
                response = client.post(
                    "/api/generate",
                    files={"file": ("test.json", test_file, "application/json")}
                )
                # should return error for malformed JSON
                assert response.status_code in [400, 422, 500]


class TestAPIRecords:
    """Test record-related API endpoints"""
    
    def test_list_records(self, client):
        """Test GET /api/records"""
        response = client.get("/api/records")
        assert response.status_code == 200

        result = response.json()
        # api returns list directly, not wrapped in object
        assert isinstance(result, list)
    
    def test_list_records_with_filters(self, client):
        """Test GET /api/records with query parameters"""
        response = client.get("/api/records?status=pending&limit=5&offset=0")
        assert response.status_code == 200

        result = response.json()
        assert isinstance(result, list)
        assert len(result) <= 5
    
    def test_export_records(self, client):
        """Test GET /api/export"""
        response = client.get("/api/export")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"


class TestAPIStaticFiles:
    """Test static file serving"""
    
    def test_frontend_static_files(self, client):
        """Test that frontend files are served"""
        response = client.get("/")
        # should either serve the frontend or return 404 if not built
        assert response.status_code in [200, 404]


class TestAPIErrors:
    """Test error handling in API endpoints"""
    
    def test_invalid_pipeline_data(self, client):
        """Test creating pipeline with invalid data"""
        invalid_data = {
            "name": "",  # empty name
            "blocks": []  # empty blocks
        }
        
        response = client.post("/api/pipelines", json=invalid_data)
        assert response.status_code in [400, 422]
    
    def test_invalid_block_type(self, client):
        """Test creating pipeline with invalid block type"""
        invalid_data = {
            "name": "Invalid Pipeline",
            "blocks": [{"type": "NonExistentBlock", "config": {}}]
        }

        # pipeline creation accepts any JSON (validation happens on execution)
        response = client.post("/api/pipelines", json=invalid_data)
        assert response.status_code == 200

        pipeline_id = response.json()["id"]

        # execution should fail with error
        try:
            exec_response = client.post(
                f"/api/pipelines/{pipeline_id}/execute",
                json={"text": "test"}
            )
            # if we get a response, it should be an error code
            assert exec_response.status_code in [400, 500]
        except Exception as e:
            # or it might raise an exception directly in test mode
            assert "unknown block type" in str(e) or "NonExistentBlock" in str(e)
    
    def test_execute_nonexistent_pipeline(self, client):
        """Test executing non-existent pipeline"""
        response = client.post("/api/pipelines/999999/execute", json={"text": "test"})
        assert response.status_code == 404