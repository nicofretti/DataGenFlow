"""
Tests for BaseBlock.dependencies attribute and its inclusion in get_schema().
"""
from lib.blocks.base import BaseBlock


class NoDepsBlock(BaseBlock):
    name = "No Deps"
    description = "Block with no dependencies"
    inputs = ["text"]
    outputs = ["result"]

    async def execute(self, context):
        return {"result": "ok"}


class WithDepsBlock(BaseBlock):
    name = "With Deps"
    description = "Block with dependencies"
    inputs = ["text"]
    outputs = ["result"]
    dependencies = ["transformers>=4.30.0", "torch>=2.0.0"]

    async def execute(self, context):
        return {"result": "ok"}


def test_base_block_has_dependencies_default():
    assert hasattr(BaseBlock, "dependencies")
    assert BaseBlock.dependencies == []


def test_block_without_dependencies_defaults_to_empty():
    assert NoDepsBlock.dependencies == []


def test_block_with_dependencies_has_list():
    assert WithDepsBlock.dependencies == ["transformers>=4.30.0", "torch>=2.0.0"]


def test_get_schema_includes_dependencies():
    schema = WithDepsBlock.get_schema()
    assert "dependencies" in schema
    assert schema["dependencies"] == ["transformers>=4.30.0", "torch>=2.0.0"]


def test_get_schema_includes_empty_dependencies():
    schema = NoDepsBlock.get_schema()
    assert "dependencies" in schema
    assert schema["dependencies"] == []
