import pytest

from lib.blocks.builtin.markdown_multiplier import MarkdownMultiplierBlock


@pytest.mark.asyncio
async def test_markdown_multiplier_basic(make_context):
    block = MarkdownMultiplierBlock(parser_type="markdown")

    markdown_content = """# Heading 1
Some content here.

## Heading 2
More content.

### Heading 3
Even more content."""

    result = await block.execute(make_context({"file_content": markdown_content}))

    assert isinstance(result, list)
    assert len(result) > 0
    assert all("chunk_text" in item for item in result)
    assert all("chunk_index" in item for item in result)


@pytest.mark.asyncio
async def test_markdown_multiplier_sentence_parser(make_context):
    block = MarkdownMultiplierBlock(parser_type="sentence", chunk_size=50, chunk_overlap=10)

    text_content = "This is a test sentence. " * 20

    result = await block.execute(make_context({"file_content": text_content}))

    assert isinstance(result, list)
    assert len(result) > 1
    for idx, item in enumerate(result):
        assert item["chunk_index"] == idx
        assert len(item["chunk_text"]) > 0


@pytest.mark.asyncio
async def test_markdown_multiplier_empty_content(make_context):
    block = MarkdownMultiplierBlock()

    result = await block.execute(make_context({"file_content": ""}))

    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_markdown_multiplier_with_code_blocks(make_context):
    block = MarkdownMultiplierBlock(parser_type="markdown")

    markdown_with_code = """# Title

Some text before code.

```python
def hello():
    print("world")
```

Text after code."""

    result = await block.execute(make_context({"file_content": markdown_with_code}))

    assert isinstance(result, list)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_markdown_multiplier_missing_file_content(make_context):
    block = MarkdownMultiplierBlock()

    result = await block.execute(make_context())

    assert isinstance(result, list)


def test_markdown_multiplier_is_multiplier_flag():
    block = MarkdownMultiplierBlock()
    assert hasattr(block, "is_multiplier")
    assert block.is_multiplier is True


def test_markdown_multiplier_get_required_fields():
    required = MarkdownMultiplierBlock.get_required_fields({})
    assert required == ["file_content"]


@pytest.mark.asyncio
async def test_markdown_multiplier_with_chunk_size_disabled(make_context):
    block = MarkdownMultiplierBlock(parser_type="markdown", chunk_size=0)

    markdown_content = """# Heading 1
Some content here that is quite long and could potentially be split if chunking was enabled.

## Heading 2
More content that also could be split but shouldn't be."""

    result = await block.execute(make_context({"file_content": markdown_content}))

    assert isinstance(result, list)
    assert len(result) > 0
    assert all("chunk_text" in item for item in result)


@pytest.mark.asyncio
async def test_markdown_multiplier_two_pass_with_chunk_size(make_context):
    block = MarkdownMultiplierBlock(parser_type="markdown", chunk_size=100, chunk_overlap=10)

    markdown_content = (
        """# Introduction
This is a long introduction section with multiple sentences. It contains enough text to exceed the chunk size limit. """
        * 5
    )

    result = await block.execute(make_context({"file_content": markdown_content}))

    assert isinstance(result, list)
    assert len(result) > 1
    for idx, item in enumerate(result):
        assert item["chunk_index"] == idx
        assert len(item["chunk_text"]) > 0


@pytest.mark.asyncio
async def test_markdown_multiplier_two_pass_multiple_sections(make_context):
    block = MarkdownMultiplierBlock(parser_type="markdown", chunk_size=50, chunk_overlap=5)

    markdown_content = (
        """# Section One
Content for section one that will be split. """
        * 10
        + """

# Section Two
Content for section two that will also be split into smaller chunks. """
        * 10
    )

    result = await block.execute(make_context({"file_content": markdown_content}))

    assert isinstance(result, list)
    assert len(result) > 2
