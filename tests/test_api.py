"""
Tests for FastAPI endpoints in app.py
"""

import json
import os
import tempfile

import pytest


# test configuration to ensure we don't interfere with real data
@pytest.fixture
def temp_db():
    """Create a temporary database for API testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
def sample_seed_file():
    """Create a sample seed file for testing"""
    seed_data = {
        "system": "You are a helpful assistant.",
        "user": "Explain {topic} in simple terms.",
        "metadata": {"topic": "machine learning", "num_samples": 2},
    }

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
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
        assert "TextGenerator" in block_types
        assert "ValidatorBlock" in block_types

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
                {"type": "ValidatorBlock", "config": {"min_length": 1}},
                {"type": "ValidatorBlock", "config": {"min_length": 5}},
            ],
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
            "blocks": [{"type": "TransformerBlock", "config": {"operation": "lowercase"}}],
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
            "blocks": [{"type": "TransformerBlock", "config": {"operation": "lowercase"}}],
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

    def test_update_pipeline(self, client):
        """Test PUT /api/pipelines/{id}"""
        # create a pipeline first
        pipeline_data = {
            "name": "Original Pipeline",
            "blocks": [{"type": "TransformerBlock", "config": {"operation": "lowercase"}}],
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]

        # update the pipeline
        updated_data = {
            "name": "Updated Pipeline",
            "blocks": [{"type": "ValidatorBlock", "config": {"min_length": 10}}],
        }
        response = client.put(f"/api/pipelines/{pipeline_id}", json=updated_data)
        assert response.status_code == 200

        result = response.json()
        assert result["id"] == pipeline_id
        assert result["name"] == "Updated Pipeline"

        # verify changes persisted
        get_response = client.get(f"/api/pipelines/{pipeline_id}")
        assert get_response.status_code == 200
        pipeline = get_response.json()
        assert pipeline["name"] == "Updated Pipeline"
        assert pipeline["definition"]["blocks"][0]["type"] == "ValidatorBlock"

    def test_update_nonexistent_pipeline(self, client):
        """Test PUT /api/pipelines/{id} with invalid ID"""
        updated_data = {
            "name": "Test",
            "blocks": [{"type": "ValidatorBlock", "config": {}}],
        }
        response = client.put("/api/pipelines/999999", json=updated_data)
        assert response.status_code == 404

    def test_update_pipeline_with_invalid_data(self, client):
        """Test PUT /api/pipelines/{id} with missing required fields"""
        # create a pipeline first
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [{"type": "TransformerBlock", "config": {"operation": "lowercase"}}],
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]

        # try to update with missing name
        invalid_data_no_name = {"blocks": []}
        response = client.put(f"/api/pipelines/{pipeline_id}", json=invalid_data_no_name)
        assert response.status_code == 400

        # try to update with missing blocks
        invalid_data_no_blocks = {"name": "Test"}
        response = client.put(f"/api/pipelines/{pipeline_id}", json=invalid_data_no_blocks)
        assert response.status_code == 400

    def test_delete_pipeline(self, client):
        """Test DELETE /api/pipelines/{id}"""
        # create a pipeline first
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [{"type": "TransformerBlock", "config": {"operation": "lowercase"}}],
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
            "name": "Validation Pipeline",
            "blocks": [{"type": "ValidatorBlock", "config": {"min_length": 1}}],
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
        assert result["result"]["text"] == "hello world"
        assert result["result"]["valid"] is True


class TestAPISeedValidation:
    """Test seed validation endpoint"""

    def test_validate_seeds_success(self, client):
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [{"type": "ValidatorBlock", "config": {"min_length": 1}}],
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]

        seeds = [
            {"repetitions": 2, "metadata": {"text": "hello world", "assistant": "response"}},
            {"repetitions": 1, "metadata": {"text": "another seed", "assistant": "response"}},
        ]

        response = client.post(
            "/api/seeds/validate", json={"pipeline_id": pipeline_id, "seeds": seeds}
        )
        assert response.status_code == 200

        result = response.json()
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["warnings"] == []

    def test_validate_seeds_missing_required_field(self, client):
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [{"type": "ValidatorBlock", "config": {"min_length": 1}}],
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]

        seeds = [{"repetitions": 1, "metadata": {"wrong_field": "value"}}]

        response = client.post(
            "/api/seeds/validate", json={"pipeline_id": pipeline_id, "seeds": seeds}
        )
        assert response.status_code == 200

        result = response.json()
        assert result["valid"] is False
        assert len(result["errors"]) >= 1
        assert any("missing required field" in error.lower() for error in result["errors"])
        assert any("text" in error for error in result["errors"])

    def test_validate_seeds_missing_metadata(self, client):
        """seeds missing metadata are rejected by pydantic validation (422)"""
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [{"type": "ValidatorBlock", "config": {"min_length": 1}}],
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]

        # missing required 'metadata' field - pydantic will reject this
        seeds = [{"repetitions": 1}]

        response = client.post(
            "/api/seeds/validate", json={"pipeline_id": pipeline_id, "seeds": seeds}
        )
        # pydantic validation rejects malformed seeds with 422
        assert response.status_code == 422

    def test_validate_seeds_zero_repetitions_warning(self, client):
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [{"type": "ValidatorBlock", "config": {"min_length": 1}}],
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]

        seeds = [{"repetitions": 0, "metadata": {"text": "hello", "assistant": "response"}}]

        response = client.post(
            "/api/seeds/validate", json={"pipeline_id": pipeline_id, "seeds": seeds}
        )
        assert response.status_code == 200

        result = response.json()
        assert result["valid"] is True
        assert result["errors"] == []
        assert len(result["warnings"]) == 1
        assert "repetitions=0" in result["warnings"][0]
        assert "1 seed(s)" in result["warnings"][0]

    def test_validate_seeds_invalid_repetitions(self, client):
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [{"type": "ValidatorBlock", "config": {"min_length": 1}}],
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]

        seeds = [{"repetitions": -5, "metadata": {"text": "hello", "assistant": "response"}}]

        response = client.post(
            "/api/seeds/validate", json={"pipeline_id": pipeline_id, "seeds": seeds}
        )
        assert response.status_code == 200

        result = response.json()
        assert result["valid"] is False
        assert len(result["errors"]) >= 1
        assert any("invalid repetitions" in error.lower() for error in result["errors"])

    def test_validate_seeds_nonexistent_pipeline(self, client):
        seeds = [{"repetitions": 1, "metadata": {"text": "hello", "assistant": "response"}}]

        response = client.post("/api/seeds/validate", json={"pipeline_id": 999999, "seeds": seeds})
        assert response.status_code == 404

    def test_validate_seeds_with_template_variables(self, client):
        pipeline_data = {
            "name": "Test Pipeline with Templates",
            "blocks": [
                {
                    "type": "TextGenerator",
                    "config": {
                        "system_prompt": "You are a {{ role }}",
                        "user_prompt": "Write about {{ topic }} for {{ audience }}",
                    },
                }
            ],
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]

        seeds_valid = [
            {"repetitions": 1, "metadata": {"role": "teacher", "topic": "math", "audience": "kids"}}
        ]
        response = client.post(
            "/api/seeds/validate", json={"pipeline_id": pipeline_id, "seeds": seeds_valid}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["valid"] is True

        seeds_missing = [{"repetitions": 1, "metadata": {"role": "teacher"}}]
        response = client.post(
            "/api/seeds/validate", json={"pipeline_id": pipeline_id, "seeds": seeds_missing}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        error_msg = result["errors"][0]
        assert "missing required field" in error_msg.lower()
        assert "topic" in error_msg
        assert "audience" in error_msg

    def test_validate_multiple_seeds_aggregated_errors(self, client):
        pipeline_data = {
            "name": "Test Pipeline",
            "blocks": [
                {
                    "type": "TextGenerator",
                    "config": {
                        "user_prompt": "Write about {{ topic }}",
                    },
                }
            ],
        }
        create_response = client.post("/api/pipelines", json=pipeline_data)
        pipeline_id = create_response.json()["id"]

        seeds = [
            {"repetitions": 1, "metadata": {}},
            {"repetitions": 1, "metadata": {}},
            {"repetitions": 1, "metadata": {}},
        ]

        response = client.post(
            "/api/seeds/validate", json={"pipeline_id": pipeline_id, "seeds": seeds}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "some seeds missing required field" in result["errors"][0].lower()
        assert "topic" in result["errors"][0]


class TestAPIGeneration:
    """Test generation-related API endpoints"""

    def test_generate_with_invalid_file(self, client):
        """Test POST /api/generate with invalid file"""
        # test with non-JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt") as f:
            f.write("not json")
            f.flush()

            with open(f.name, "rb") as test_file:
                response = client.post(
                    "/api/generate",
                    files={"file": ("test.txt", test_file, "text/plain")},
                    data={"pipeline_id": "1"},
                )
                assert response.status_code in [
                    400,
                    422,
                ]  # either bad request or validation error

    def test_generate_with_malformed_json(self, client):
        """Test POST /api/generate with malformed JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as f:
            f.write("{invalid json")
            f.flush()

            with open(f.name, "rb") as test_file:
                response = client.post(
                    "/api/generate",
                    files={"file": ("test.json", test_file, "application/json")},
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
        invalid_data = {"name": "", "blocks": []}  # empty name  # empty blocks

        response = client.post("/api/pipelines", json=invalid_data)
        assert response.status_code in [400, 422]

    def test_invalid_block_type(self, client):
        """Test creating and executing pipeline with invalid block type"""
        invalid_data = {
            "name": "Invalid Pipeline",
            "blocks": [{"type": "NonExistentBlock", "config": {}}],
        }

        # pipeline creation should succeed (validation deferred to execution)
        response = client.post("/api/pipelines", json=invalid_data)
        assert response.status_code == 200
        pipeline_id = response.json()["id"]

        # but execution should fail with block not found error
        exec_response = client.post(f"/api/pipelines/{pipeline_id}/execute", json={"data": "test"})
        assert exec_response.status_code in [400, 500]
        assert "NonExistentBlock" in exec_response.json()["error"]

    def test_execute_nonexistent_pipeline(self, client):
        """Test executing non-existent pipeline"""
        response = client.post("/api/pipelines/999999/execute", json={"text": "test"})
        assert response.status_code == 404
