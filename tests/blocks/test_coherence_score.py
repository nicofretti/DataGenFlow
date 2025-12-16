import pytest

from lib.blocks.builtin.coherence_score import CoherenceScore


@pytest.mark.asyncio
async def test_coherence_score(make_context):
    block = CoherenceScore(field_name="assistant")
    result = await block.execute(
        make_context(
            {"assistant": "This is a sentence. This is another sentence. Final sentence here."}
        )
    )

    assert "coherence_score" in result
    assert 0 <= result["coherence_score"] <= 1


@pytest.mark.asyncio
async def test_coherence_score_empty(make_context):
    block = CoherenceScore(field_name="assistant")
    result = await block.execute(make_context({"assistant": ""}))

    assert result["coherence_score"] == 0.0


@pytest.mark.asyncio
async def test_coherence_score_schema():
    schema = CoherenceScore.get_schema()
    assert schema["name"] == "Coherence Score"
    assert "field_name" in schema["config_schema"]["properties"]
