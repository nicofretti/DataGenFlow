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
    """test complete data augmentation pipeline with all 3 blocks"""

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
        pipeline_id = await storage.save_pipeline("test_augmentation", json.dumps(pipeline_def))
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
        results = await pipeline.execute(initial_data)

        # verify results
        assert isinstance(results, list), "Multiplier pipeline should return list"
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"

        # verify each result
        for exec_result in results:
            result = exec_result.result
            trace = exec_result.trace
            trace_id = exec_result.trace_id
            # check required fields
            assert "plan" in result, "Missing plan field"
            assert "role" in result, "Missing role field"
            assert "storage" in result, "Missing storage field"
            assert "bio" in result, "Missing bio field"

            # check duplicate check fields
            assert "is_duplicate" in result, "Missing is_duplicate field"
            assert "similarity_score" in result, "Missing similarity_score field"
            assert isinstance(result["is_duplicate"], bool)
            assert isinstance(result["similarity_score"], float)

            # check plan values are valid
            assert result["plan"] in ["Free", "Pro"], f"Invalid plan: {result['plan']}"

            # check role values are valid
            assert result["role"] in ["Viewer", "Editor", "Admin"], (
                f"Invalid role: {result['role']}"
            )

            # check dependencies: Free -> Viewer
            if result["plan"] == "Free":
                assert result["role"] == "Viewer", "Free plan should have Viewer role"

            # check trace has 2 steps (StructureSampler is multiplier, doesn't appear in per-item trace)
            assert len(trace) == 2, f"Expected 2 trace steps, got {len(trace)}"

            step_types = [step.block_type for step in trace]
            assert step_types == [
                "SemanticInfiller",
                "DuplicateRemover",
            ], f"Unexpected trace steps: {step_types}"

            # verify trace_id is valid
            assert isinstance(trace_id, str)
            assert len(trace_id) > 0

        print("\n✅ All integration tests passed!")
        print(f"Generated {len(results)} records successfully")

        # print sample result for inspection
        sample = results[0].result
        print("\nSample result:")
        print(f"  plan: {sample['plan']}")
        print(f"  role: {sample['role']}")
        print(f"  storage: {sample['storage']}")
        print(f"  bio: {sample['bio']}")
        print(f"  is_duplicate: {sample['is_duplicate']}")
        print(f"  similarity_score: {sample['similarity_score']}")

    finally:
        await storage.close()


@pytest.mark.asyncio
async def test_structure_sampler_alone(tmp_path):
    """test StructureSampler block in isolation"""

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

        results = await pipeline.execute(initial_data)

        assert isinstance(results, list)
        assert len(results) == 10

        # check distribution approximately matches input (2 Free, 1 Pro = 67% Free, 33% Pro)
        plan_counts = {"Free": 0, "Pro": 0}
        for exec_result in results:
            plan_counts[exec_result.result["plan"]] += 1

        # expect approximately 6-7 Free, 3-4 Pro (with seed=42, should be deterministic)
        assert 5 <= plan_counts["Free"] <= 8, f"Free count out of range: {plan_counts['Free']}"
        assert 2 <= plan_counts["Pro"] <= 5, f"Pro count out of range: {plan_counts['Pro']}"

        print(f"\n✅ StructureSampler test passed! Distribution: {plan_counts}")

    finally:
        await storage.close()


@pytest.mark.asyncio
async def test_data_augmentation_with_no_embedding_model(tmp_path):
    """test that DuplicateRemover gracefully handles missing embedding model"""

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
                    "type": "DuplicateRemover",
                    "config": {
                        "similarity_threshold": 0.85,
                        "comparison_fields": ["plan"],
                        "embedding_model": "non_existent_model",
                    },
                },
            ]
        }

        pipeline_id = await storage.save_pipeline("test_no_embedding", json.dumps(pipeline_def))
        assert pipeline_id > 0
        pipeline = Pipeline("test_no_embedding", pipeline_def["blocks"])

        initial_data = {"samples": [{"plan": "Free"}]}

        # should not raise error, just skip similarity check
        results = await pipeline.execute(initial_data)

        assert isinstance(results, list)
        assert len(results) == 3

        for exec_result in results:
            # should have is_duplicate = False when embedding check fails
            assert exec_result.result["is_duplicate"] is False
            assert exec_result.result["similarity_score"] == 0.0

        print("\n✅ No embedding model test passed!")

    finally:
        await storage.close()
