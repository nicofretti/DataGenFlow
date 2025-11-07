import pytest

from lib.blocks.builtin.structured_generator import StructuredGenerator


@pytest.mark.integration
@pytest.mark.asyncio
async def test_structured_generator_ollama():
    """integration test for StructuredGenerator with actual Ollama instance"""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
    }

    block = StructuredGenerator(
        json_schema=schema,
        model="gemma3:1b",
        temperature=0.7,
        max_tokens=200,
        user_prompt="Generate a person with name and age",
    )

    result = await block.execute({})

    assert "generated" in result
    assert isinstance(result["generated"], dict)
    print(f"Generated JSON: {result['generated']}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_structured_generator_with_data():
    """integration test using prompt from data"""
    schema = {
        "type": "object",
        "properties": {"city": {"type": "string"}, "population": {"type": "number"}},
    }

    block = StructuredGenerator(json_schema=schema)

    result = await block.execute({"prompt": "Generate a city with name and population"})

    assert "generated" in result
    assert isinstance(result["generated"], dict)
    print(f"Generated JSON: {result['generated']}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_structured_generator_complex_schema():
    """integration test with nested schema"""
    schema = {
        "type": "object",
        "properties": {
            "product": {"type": "string"},
            "price": {"type": "number"},
            "features": {"type": "array", "items": {"type": "string"}},
        },
    }

    block = StructuredGenerator(
        json_schema=schema, user_prompt="Generate a product with name, price and 3 features"
    )

    result = await block.execute({})

    assert "generated" in result
    assert isinstance(result["generated"], dict)
    print(f"Generated JSON: {result['generated']}")
