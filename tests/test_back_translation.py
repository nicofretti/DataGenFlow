import pytest
from lib.blocks.research.back_translation import BackTranslationBlock


@pytest.mark.asyncio
async def test_back_translation_creates_variations():
    block = BackTranslationBlock(num_variations=2, temperature=0.7)
    data = {
        "conversation": "User: Hi. Agent: Hello, how can I help?",
        "topic": "greeting"
    }
    result = await block.execute(data)

    assert "diverse_conversations" in result
    assert len(result["diverse_conversations"]) == 2
    assert "diversity_score" in result
    assert 0 <= result["diversity_score"] <= 1


@pytest.mark.asyncio
async def test_back_translation_records_algorithm():
    block = BackTranslationBlock()
    data = {"conversation": "test"}
    result = await block.execute(data)

    assert result["algorithm"] == "back_translation_diversity"
    assert "paper" in result
    assert "Sennrich" in result["paper"]
