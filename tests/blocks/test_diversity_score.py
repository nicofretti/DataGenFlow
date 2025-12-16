import pytest

from lib.blocks.builtin.diversity_score import DiversityScore


@pytest.mark.asyncio
async def test_diversity_score_list(make_context):
    block = DiversityScore(field_name="texts")
    result = await block.execute(
        make_context({"texts": ["hello world", "goodbye world", "hello there"]})
    )

    assert "diversity_score" in result
    assert 0 <= result["diversity_score"] <= 1
    # should have some diversity since texts differ
    assert result["diversity_score"] > 0


@pytest.mark.asyncio
async def test_diversity_score_identical(make_context):
    block = DiversityScore(field_name="texts")
    result = await block.execute(make_context({"texts": ["same text", "same text", "same text"]}))

    assert "diversity_score" in result
    # identical texts should have 0 diversity
    assert result["diversity_score"] == 0


@pytest.mark.asyncio
async def test_diversity_score_single_text(make_context):
    block = DiversityScore(field_name="assistant")
    result = await block.execute(make_context({"assistant": "single text"}))

    assert "diversity_score" in result
    # single text has no diversity
    assert result["diversity_score"] == 0.0


@pytest.mark.asyncio
async def test_diversity_score_schema():
    schema = DiversityScore.get_schema()
    assert schema["name"] == "Diversity Score"
    assert "field_name" in schema["config_schema"]["properties"]
    assert schema["config_schema"]["properties"]["field_name"]["default"] == "assistant"
