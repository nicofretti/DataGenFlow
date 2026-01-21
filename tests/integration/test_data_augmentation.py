"""integration test for data augmentation pipeline"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lib.entities import LLMModelConfig, LLMProvider
from lib.storage import Storage
from lib.workflow import Pipeline


@pytest.mark.asyncio
@patch("litellm.acompletion")
@patch("app.llm_config_manager")
async def test_data_augmentation_pipeline(mock_config_manager, mock_completion, tmp_path):
    """test complete data augmentation pipeline with all 3 blocks (batch mode)"""

    # setup mocks for LLM calls
    mock_config_manager.get_llm_model = AsyncMock(
        return_value=LLMModelConfig(
            name="test",
            provider=LLMProvider.OPENAI,
            endpoint="http://test",
            model_name="gpt-4",
        )
    )
    mock_config_manager.prepare_llm_call = MagicMock(
        return_value={"model": "gpt-4", "messages": []}
    )
    # mock embedding model to skip (will fall back to default similarity)
    mock_config_manager.get_embedding_model = AsyncMock(side_effect=Exception("No embedding"))

    # mock LLM response with realistic generated fields
    mock_completion.return_value = MagicMock(
        choices=[
            MagicMock(message=MagicMock(content='{"bio": "Generated bio text", "storage": 10}'))
        ],
        usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
    )

    # setup test database
    db_path = tmp_path / "test.db"
    storage = Storage(str(db_path))
    await storage.init_db()

    try:
        # define pipeline
        pipeline_def = {
            "blocks": [
                {
                    "type": "StructureSampler",
                    "config": {
                        "target_count": 5,
                        "categorical_fields": ["plan", "role"],
                        "numeric_fields": ["storage"],
                        "dependencies": {"role": ["plan"]},
                        "seed": 42,
                    },
                },
                {
                    "type": "SemanticInfiller",
                    "config": {
                        "fields_to_generate": '["bio", "storage"]',
                        "temperature": 0.8,
                        "max_tokens": 200,
                        "model": None,
                    },
                },
                {
                    "type": "DuplicateRemover",
                    "config": {
                        "similarity_threshold": 0.85,
                        "comparison_fields": ["bio"],
                        "embedding_model": None,
                    },
                },
            ]
        }

        # save pipeline to database
        pipeline_id = await storage.save_pipeline("test_augmentation", pipeline_def)
        assert pipeline_id > 0

        # create pipeline instance
        pipeline = Pipeline("test_augmentation", pipeline_def["blocks"])

        # prepare seed data
        initial_data = {
            "samples": [
                {
                    "plan": "Free",
                    "role": "Viewer",
                    "storage": 1,
                    "bio": "Student learning",
                },
                {
                    "plan": "Free",
                    "role": "Viewer",
                    "storage": 2,
                    "bio": "Just exploring",
                },
                {
                    "plan": "Pro",
                    "role": "Editor",
                    "storage": 50,
                    "bio": "Freelancer",
                },
                {
                    "plan": "Pro",
                    "role": "Admin",
                    "storage": 100,
                    "bio": "Team lead",
                },
            ]
        }

        # execute pipeline
        result = await pipeline.execute(initial_data)

        # verify batch mode return (single ExecutionResult)
        assert hasattr(result, "result"), "Batch pipeline should return ExecutionResult"

        # get samples from result
        samples = result.result.get("generated_samples", [])
        assert len(samples) == 5, f"Expected 5 samples, got {len(samples)}"

        # verify each sample
        for sample in samples:
            assert "plan" in sample, "Missing plan field"
            assert "role" in sample, "Missing role field"
            assert "storage" in sample, "Missing storage field"
            assert "bio" in sample, "Missing bio field"

            # check duplicate fields
            assert "is_duplicate" in sample, "Missing is_duplicate"
            assert "similarity_to_seeds" in sample, "Missing similarity_to_seeds"
            assert "similarity_to_generated" in sample, "Missing similarity_to_generated"

            # check valid values
            assert sample["plan"] in ["Free", "Pro"]
            if sample["plan"] == "Free":
                assert sample["role"] == "Viewer"

        # verify trace has 3 blocks (batch mode)
        trace = result.trace
        assert len(trace) == 3, f"Expected 3 blocks in trace, got {len(trace)}"
        assert trace[0].block_type == "StructureSampler"
        assert trace[1].block_type == "SemanticInfiller"
        assert trace[2].block_type == "DuplicateRemover"

        print("\n✅ All integration tests passed!")
        print(f"Generated {len(samples)} records successfully")

        # print sample result for inspection
        sample = samples[0]
        print("\nSample result:")
        print(f"  plan: {sample['plan']}")
        print(f"  role: {sample['role']}")
        print(f"  storage: {sample['storage']}")
        print(f"  bio: {sample['bio']}")
        print(f"  is_duplicate: {sample['is_duplicate']}")

    finally:
        await storage.close()


@pytest.mark.asyncio
async def test_structure_sampler_alone(tmp_path):
    """test StructureSampler block in isolation (batch mode)"""

    db_path = tmp_path / "test.db"
    storage = Storage(str(db_path))
    await storage.init_db()

    try:
        pipeline_def = {
            "blocks": [
                {
                    "type": "StructureSampler",
                    "config": {
                        "target_count": 10,
                        "categorical_fields": ["plan"],
                        "numeric_fields": [],
                        "dependencies": {},
                        "seed": 42,
                    },
                }
            ]
        }

        pipeline_id = await storage.save_pipeline("test_sampler", json.dumps(pipeline_def))
        assert pipeline_id > 0
        pipeline = Pipeline("test_sampler", pipeline_def["blocks"])

        initial_data = {
            "samples": [
                {"plan": "Free"},
                {"plan": "Free"},
                {"plan": "Pro"},
            ]
        }

        result = await pipeline.execute(initial_data)

        # verify batch mode (single ExecutionResult)
        assert hasattr(result, "result"), "Should return ExecutionResult"

        skeletons = result.result.get("skeletons", [])
        assert len(skeletons) == 10, f"Expected 10 skeletons, got {len(skeletons)}"

        # check distribution approximately matches input (2 Free, 1 Pro = 67% Free, 33% Pro)
        plan_counts = {"Free": 0, "Pro": 0}
        for skeleton in skeletons:
            plan_counts[skeleton["plan"]] += 1

        # expect approximately 6-7 Free, 3-4 Pro (with seed=42, should be deterministic)
        assert 5 <= plan_counts["Free"] <= 8, f"Free count out of range: {plan_counts['Free']}"
        assert 2 <= plan_counts["Pro"] <= 5, f"Pro count out of range: {plan_counts['Pro']}"

        print(f"\n✅ StructureSampler test passed! Distribution: {plan_counts}")

    finally:
        await storage.close()


@pytest.mark.asyncio
@patch("litellm.acompletion")
@patch("app.llm_config_manager")
async def test_data_augmentation_with_no_embedding_model(
    mock_config_manager, mock_completion, tmp_path
):
    """test that DuplicateRemover gracefully handles missing embedding model"""

    # setup mocks for LLM calls
    mock_config_manager.get_llm_model = AsyncMock(
        return_value=LLMModelConfig(
            name="test",
            provider=LLMProvider.OPENAI,
            endpoint="http://test",
            model_name="gpt-4",
        )
    )
    mock_config_manager.prepare_llm_call = MagicMock(
        return_value={"model": "gpt-4", "messages": []}
    )
    # mock embedding model to fail (simulates no embedding model configured)
    mock_config_manager.get_embedding_model = AsyncMock(
        side_effect=Exception("Embedding model not configured")
    )

    # mock LLM response
    mock_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"bio": "Test bio"}'))],
        usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
    )

    db_path = tmp_path / "test.db"
    storage = Storage(str(db_path))
    await storage.init_db()

    try:
        pipeline_def = {
            "blocks": [
                {
                    "type": "StructureSampler",
                    "config": {
                        "target_count": 3,
                        "categorical_fields": ["plan"],
                        "numeric_fields": [],
                        "dependencies": {},
                        "seed": 42,
                    },
                },
                {
                    "type": "SemanticInfiller",
                    "config": {
                        "fields_to_generate": '["bio"]',
                        "temperature": 0.8,
                        "max_tokens": 200,
                        "model": None,
                    },
                },
                {
                    "type": "DuplicateRemover",
                    "config": {
                        "similarity_threshold": 0.85,
                        "comparison_fields": ["bio"],
                        "embedding_model": "non_existent_model",
                    },
                },
            ]
        }

        pipeline_id = await storage.save_pipeline("test_no_embedding", json.dumps(pipeline_def))
        assert pipeline_id > 0
        pipeline = Pipeline("test_no_embedding", pipeline_def["blocks"])

        initial_data = {"samples": [{"plan": "Free", "bio": "Original"}]}

        # should not raise error, just skip similarity check
        result = await pipeline.execute(initial_data)

        # verify batch mode (single ExecutionResult)
        assert hasattr(result, "result"), "Should return ExecutionResult"

        samples = result.result.get("generated_samples", [])
        assert len(samples) == 3

        for sample in samples:
            # should have is_duplicate = False when embedding check fails
            assert sample["is_duplicate"] is False
            assert sample["similarity_to_seeds"] == 0.0
            assert sample["similarity_to_generated"] == 0.0

        print("\n✅ No embedding model test passed!")

    finally:
        await storage.close()
