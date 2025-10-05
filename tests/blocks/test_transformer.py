import pytest

from lib.blocks.builtin.transformer import TransformerBlock


@pytest.mark.asyncio
async def test_transformer_lowercase():
    block = TransformerBlock(operation="lowercase")
    result = await block.execute({"text": "HELLO World"})
    assert result["text"] == "hello world"


@pytest.mark.asyncio
async def test_transformer_uppercase():
    block = TransformerBlock(operation="uppercase")
    result = await block.execute({"text": "hello world"})
    assert result["text"] == "HELLO WORLD"


@pytest.mark.asyncio
async def test_transformer_strip():
    block = TransformerBlock(operation="strip")
    result = await block.execute({"text": "  hello  "})
    assert result["text"] == "hello"


@pytest.mark.asyncio
async def test_transformer_trim():
    block = TransformerBlock(operation="trim")
    result = await block.execute({"text": "hello    world   test"})
    assert result["text"] == "hello world test"
