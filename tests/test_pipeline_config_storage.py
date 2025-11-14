import pytest

from lib.storage import Storage
from lib.workflow import Pipeline


@pytest.mark.asyncio
async def test_pipeline_definition_with_block_configs():
    """test that pipeline definitions can store and retrieve block configurations"""
    pipeline_def = {
        "name": "My Pipeline",
        "blocks": [
            {
                "type": "TextGenerator",
                "config": {"model": "llama2", "temperature": 0.8, "max_tokens": 1000},
            },
            {"type": "ValidatorBlock", "config": {"min_length": 10, "max_length": 5000}},
        ],
    }

    # should be storable and retrievable
    storage = Storage(":memory:")
    await storage.init_db()

    try:
        pipeline_id = await storage.save_pipeline("test", pipeline_def)
        retrieved = await storage.get_pipeline(pipeline_id)

        assert retrieved is not None
        assert retrieved["definition"]["blocks"][0]["config"]["temperature"] == 0.8
        assert retrieved["definition"]["blocks"][1]["config"]["min_length"] == 10
    finally:
        # close the storage connection
        await storage.close()


@pytest.mark.asyncio
async def test_workflow_uses_block_configs():
    """test that workflow initializes blocks with their configurations"""
    pipeline_def = {
        "name": "Test Pipeline",
        "blocks": [
            {
                "type": "TextGenerator",
                "config": {"model": "llama2", "temperature": 0.9, "max_tokens": 500},
            }
        ],
    }

    # create pipeline from definition
    pipeline = Pipeline(name=str(pipeline_def["name"]), blocks=list(pipeline_def["blocks"]))  # type: ignore[arg-type]

    # verify block was initialized with config
    assert len(pipeline._block_instances) == 1
    block = pipeline._block_instances[0]
    assert block.model_name == "llama2"
    assert block.temperature == 0.9
    assert block.max_tokens == 500
