import pytest
from lib.blocks.research.dialogue_generator import DialogueGeneratorBlock


@pytest.mark.asyncio
async def test_dialogue_generator_with_personas():
    block = DialogueGeneratorBlock(turns=3, algo="persona_driven")
    data = {
        "personas": [
            {"name": "John", "personality": "frustrated"},
            {"name": "Agent", "personality": "helpful"}
        ],
        "topic": "billing_issue"
    }
    result = await block.execute(data)

    assert "dialogue" in result
    assert "turn_count" in result
    assert result["turn_count"] == 3


@pytest.mark.asyncio
async def test_dialogue_generator_without_seed():
    block = DialogueGeneratorBlock(turns=2, algo="persona_driven")
    data = {"topic": "greeting"}
    result = await block.execute(data)

    assert "dialogue" in result
    assert len(result["dialogue"]) > 0
