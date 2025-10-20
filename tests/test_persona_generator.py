import pytest
from lib.blocks.research.persona_generator import PersonaGeneratorBlock


@pytest.mark.asyncio
async def test_persona_generator_creates_persona_without_seed():
    block = PersonaGeneratorBlock(personality_traits=["helpful", "friendly"], num_personas=1)
    data = {}  # no seed input
    result = await block.execute(data)

    assert "personas" in result
    assert len(result["personas"]) == 1
    persona = result["personas"][0]
    assert "name" in persona
    assert "personality" in persona
    assert "background" in persona


@pytest.mark.asyncio
async def test_persona_generator_with_metadata():
    block = PersonaGeneratorBlock(personality_traits=["frustrated"], num_personas=1)
    data = {"topic": "billing", "context": "customer service"}
    result = await block.execute(data)

    assert result["personas"][0]["context"] == "billing"
