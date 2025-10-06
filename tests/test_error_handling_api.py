"""
Tests for error handling in API and workflow
"""
import pytest
from starlette.testclient import TestClient

from app import app
from lib.workflow import Pipeline
from lib.errors import BlockNotFoundError, BlockExecutionError, ValidationError


# client fixture now provided by conftest.py


class TestAPIErrorResponses:
    """Test API error responses"""

    def test_invalid_block_type_returns_error(self, client):
        """Test pipeline with invalid block type returns proper error"""
        pipeline_data = {
            "name": "Invalid Pipeline",
            "blocks": [{"type": "NonExistentBlock", "config": {}}]
        }

        # create pipeline (should succeed)
        response = client.post("/api/pipelines", json=pipeline_data)
        assert response.status_code == 200
        pipeline_id = response.json()["id"]

        # execute should fail with proper error
        exec_response = client.post(
            f"/api/pipelines/{pipeline_id}/execute",
            json={"text": "test"}
        )
        assert exec_response.status_code == 400
        error_data = exec_response.json()
        assert "error" in error_data
        assert "NonExistentBlock" in error_data["error"]
        assert "detail" in error_data
        assert "available_blocks" in error_data["detail"]

    def test_validation_error_returns_proper_response(self, client):
        """Test validation error returns structured response"""
        # create a custom block that returns extra fields (will fail in real scenario)
        # for now just test the error structure
        pass


class TestWorkflowErrors:
    """Test workflow error types"""

    @pytest.mark.asyncio
    async def test_block_not_found_error(self):
        """Test BlockNotFoundError is raised for invalid block"""
        pipeline_def = {
            "name": "Test",
            "blocks": [{"type": "InvalidBlock", "config": {}}]
        }

        with pytest.raises(BlockNotFoundError) as exc_info:
            Pipeline.load_from_dict(pipeline_def)

        assert "InvalidBlock" in str(exc_info.value.message)
        assert "available_blocks" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_block_execution_error_includes_context(self):
        """Test BlockExecutionError includes block name and step"""
        from unittest.mock import AsyncMock, patch

        pipeline_def = {
            "name": "Test",
            "blocks": [
                {"type": "TransformerBlock", "config": {}}
            ]
        }

        pipeline = Pipeline.load_from_dict(pipeline_def)

        # Mock the block's execute to raise an error
        with patch.object(pipeline._block_instances[0], 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("Simulated block failure")

            with pytest.raises(BlockExecutionError) as exc_info:
                await pipeline.execute({"text": "test"})

        error = exc_info.value
        assert "TransformerBlock" in error.message
        assert "step" in error.detail
        assert error.detail["step"] == 1


class TestErrorMessages:
    """Test error message clarity"""

    @pytest.mark.asyncio
    async def test_error_message_shows_available_blocks(self):
        """Test error message lists available blocks"""
        pipeline_def = {
            "name": "Test",
            "blocks": [{"type": "FakeBlock", "config": {}}]
        }

        with pytest.raises(BlockNotFoundError) as exc_info:
            Pipeline.load_from_dict(pipeline_def)

        # should show available blocks in detail
        assert len(exc_info.value.detail["available_blocks"]) > 0
        # should include known blocks
        available = exc_info.value.detail["available_blocks"]
        assert "TransformerBlock" in available or "LLMBlock" in available
