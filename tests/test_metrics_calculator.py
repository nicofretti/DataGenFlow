import pytest
from lib.blocks.research.metrics_calculator import MetricsCalculatorBlock


@pytest.mark.asyncio
async def test_metrics_calculator_computes_all_metrics():
    block = MetricsCalculatorBlock(compute=["diversity", "coherence", "difficulty"])
    data = {
        "conversation": "User: Hi. Agent: Hello!",
        "diverse_conversations": ["User: Hi. Agent: Hello!", "User: Greetings. Agent: Welcome!"],
        "diversity_score": 0.6,
        "difficulty_score": 0.3,
        "algorithm": "back_translation"
    }
    result = await block.execute(data)

    assert "metrics" in result
    assert result["metrics"]["diversity"] == 0.6
    assert result["metrics"]["coherence"] > 0
    assert result["metrics"]["difficulty"] == 0.3


@pytest.mark.asyncio
async def test_metrics_calculator_with_engagement():
    block = MetricsCalculatorBlock(compute=["engagement"])
    data = {
        "conversation": "User: How are you? Agent: I'm great! Thanks for asking!"
    }
    result = await block.execute(data)

    assert "metrics" in result
    assert "engagement" in result["metrics"]
    assert result["metrics"]["engagement"] > 0


@pytest.mark.asyncio
async def test_metrics_calculator_creates_summary():
    block = MetricsCalculatorBlock(compute=["diversity", "coherence"])
    data = {
        "conversation": "User: Hello. Agent: Hi there!",
        "diversity_score": 0.5
    }
    result = await block.execute(data)

    assert "metrics_summary" in result
    assert "diversity" in result["metrics_summary"]
    assert "coherence" in result["metrics_summary"]


@pytest.mark.asyncio
async def test_metrics_calculator_default_metrics():
    block = MetricsCalculatorBlock()
    data = {
        "conversation": "User: Hi. Agent: Hello!",
        "diversity_score": 0.4
    }
    result = await block.execute(data)

    assert "metrics" in result
    # should compute all default metrics
    assert len(result["metrics"]) > 0
