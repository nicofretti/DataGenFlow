import pytest

from lib.blocks.validator import ValidatorBlock


@pytest.mark.asyncio
async def test_validator_min_length():
    block = ValidatorBlock(min_length=10)

    result = await block.execute({"text": "short"})
    assert result["valid"] is False

    result = await block.execute({"text": "this is long enough"})
    assert result["valid"] is True


@pytest.mark.asyncio
async def test_validator_max_length():
    block = ValidatorBlock(max_length=10)

    result = await block.execute({"text": "this is too long"})
    assert result["valid"] is False

    result = await block.execute({"text": "short"})
    assert result["valid"] is True


@pytest.mark.asyncio
async def test_validator_forbidden_words():
    block = ValidatorBlock(forbidden_words=["bad", "forbidden"])

    result = await block.execute({"text": "this is a bad example"})
    assert result["valid"] is False

    result = await block.execute({"text": "this is good"})
    assert result["valid"] is True
