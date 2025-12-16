import pytest

from lib.blocks.builtin.rouge_score import RougeScore


@pytest.mark.asyncio
async def test_rouge_score_perfect_match(make_context):
    block = RougeScore(
        generated_field="assistant", reference_field="reference", rouge_type="rouge1"
    )
    result = await block.execute(
        make_context({"assistant": "The quick brown fox", "reference": "The quick brown fox"})
    )

    assert "rouge_score" in result
    assert result["rouge_score"] == 1.0


@pytest.mark.asyncio
async def test_rouge_score_partial_match(make_context):
    block = RougeScore(
        generated_field="assistant", reference_field="reference", rouge_type="rouge1"
    )
    result = await block.execute(
        make_context({"assistant": "The quick brown dog", "reference": "The quick brown fox"})
    )

    assert "rouge_score" in result
    assert 0 < result["rouge_score"] < 1.0


@pytest.mark.asyncio
async def test_rouge_score_empty(make_context):
    block = RougeScore()
    result = await block.execute(make_context())

    assert result["rouge_score"] == 0.0


@pytest.mark.asyncio
async def test_rouge_score_schema():
    schema = RougeScore.get_schema()
    assert schema["name"] == "ROUGE Score"
    assert "generated_field" in schema["config_schema"]["properties"]
    assert "reference_field" in schema["config_schema"]["properties"]
    assert "rouge_type" in schema["config_schema"]["properties"]
