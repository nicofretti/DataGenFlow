import pytest

from lib.templates import TemplateRegistry
from lib.workflow import Pipeline
from models import Record, RecordStatus


@pytest.mark.asyncio
async def test_full_customer_service_pipeline(storage):
    """end-to-end test: load template, execute with seed, verify metrics"""
    from unittest.mock import AsyncMock, patch

    # 1. load template
    registry = TemplateRegistry()
    template = registry.get_template("customer_service_conversations")
    assert template is not None

    # 2. create pipeline from template
    pipeline = Pipeline(name="Customer Service Test", blocks=template["blocks"])

    # 3. prepare seed data (metadata only, no algorithm config)
    seed_data = {
        "repetitions": 1,
        "metadata": {
            "topic": "billing_issue",
            "persona_style": "frustrated_customer",
            "num_turns": 3,
            "difficulty": "intermediate",
        },
    }

    # 4. execute pipeline with mocked llm calls
    with patch("lib.generator.Generator.generate", new_callable=AsyncMock) as mock_gen:
        # mock persona generation
        mock_gen.return_value = '{"name": "John", "personality": "frustrated", "background": "Customer with billing issue"}'

        job_id = 1
        accumulated_state, trace, trace_id = await pipeline.execute(
            seed_data["metadata"], job_id, None, storage
        )

        # 5. verify accumulated state contains metrics
        assert "metrics" in accumulated_state
        assert "diversity" in accumulated_state["metrics"]
        assert "coherence" in accumulated_state["metrics"]
        assert "engagement" in accumulated_state["metrics"]

        # 6. verify trace shows all algorithm blocks executed
        block_types = [t["block_type"] for t in trace]
        assert "PersonaGeneratorBlock" in block_types
        assert "DialogueGeneratorBlock" in block_types
        assert "BackTranslationBlock" in block_types
        assert "MetricsCalculatorBlock" in block_types
        assert "ValidatorBlock" in block_types

        # 7. verify dialogue was generated
        assert "dialogue" in accumulated_state
        assert len(accumulated_state["dialogue"]) > 0

        # 8. verify metrics are computed and numeric
        assert isinstance(accumulated_state["metrics"]["diversity"], (int, float))
        assert isinstance(accumulated_state["metrics"]["coherence"], (int, float))
        assert isinstance(accumulated_state["metrics"]["engagement"], (int, float))
        assert 0 <= accumulated_state["metrics"]["diversity"] <= 1
        assert 0 <= accumulated_state["metrics"]["coherence"] <= 1
        assert 0 <= accumulated_state["metrics"]["engagement"] <= 1

        # 9. save record and verify
        # use dialogue as output (pipeline_output might be metrics dict from last block)
        import json

        output = accumulated_state.get("dialogue", "")
        if isinstance(output, dict):
            output = json.dumps(output)

        # ensure output is a string
        if not isinstance(output, str):
            output = str(output)

        record = Record(
            output=output,
            metadata=seed_data["metadata"],
            status=RecordStatus.PENDING,
            trace=trace,
        )

        record_id = await storage.save_record(record)
        assert record_id > 0

        # 10. retrieve and verify saved record
        saved_record = await storage.get_by_id(record_id)
        assert saved_record is not None
        assert saved_record.trace is not None
        assert len(saved_record.trace) == 5  # all 5 blocks
        assert saved_record.metadata["topic"] == "billing_issue"
