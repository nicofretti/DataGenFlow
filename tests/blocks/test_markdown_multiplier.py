import pytest

from lib.blocks.builtin.markdown_multiplier import MarkdownMultiplierBlock


@pytest.mark.asyncio
async def test_markdown_multiplier_basic():
    block = MarkdownMultiplierBlock(parser_type="markdown")

    markdown_content = """# Heading 1
Some content here.

## Heading 2
More content.

### Heading 3
Even more content."""

    result = await block.execute({"file_content": markdown_content})

    assert isinstance(result, list)
    assert len(result) > 0
    assert all("chunk_text" in item for item in result)
    assert all("chunk_index" in item for item in result)


@pytest.mark.asyncio
async def test_markdown_multiplier_sentence_parser():
    block = MarkdownMultiplierBlock(parser_type="sentence", chunk_size=50, chunk_overlap=10)

    text_content = "This is a test sentence. " * 20

    result = await block.execute({"file_content": text_content})

    assert isinstance(result, list)
    assert len(result) > 1
    for idx, item in enumerate(result):
        assert item["chunk_index"] == idx
        assert len(item["chunk_text"]) > 0


@pytest.mark.asyncio
async def test_markdown_multiplier_empty_content():
    block = MarkdownMultiplierBlock()

    result = await block.execute({"file_content": ""})

    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_markdown_multiplier_with_code_blocks():
    block = MarkdownMultiplierBlock(parser_type="markdown")

    markdown_with_code = """# Title

Some text before code.

```python
def hello():
    print("world")
```

Text after code."""

    result = await block.execute({"file_content": markdown_with_code})

    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_markdown_multiplier_missing_file_content():
    block = MarkdownMultiplierBlock()

    result = await block.execute({})

    assert isinstance(result, list)


def test_markdown_multiplier_is_multiplier_flag():
    block = MarkdownMultiplierBlock()
    assert hasattr(block, "is_multiplier")
    assert block.is_multiplier is True


def test_markdown_multiplier_get_required_fields():
    required = MarkdownMultiplierBlock.get_required_fields({})
    assert required == ["file_content"]
