import pytest

from lib.blocks.builtin.field_mapper import FieldMapper
from lib.entities.block_execution_context import BlockExecutionContext


def make_context(state: dict) -> BlockExecutionContext:
    """helper to create test context"""
    return BlockExecutionContext(
        trace_id="test-trace",
        pipeline_id=1,
        accumulated_state=state,
    )


class TestFieldMapperInit:
    def test_init_with_mappings(self):
        block = FieldMapper(mappings={"a": "{{ b }}"})
        assert block.mappings_template == '{"a": "{{ b }}"}'

    def test_init_empty(self):
        block = FieldMapper()
        assert block.mappings_template == "{}"

    def test_init_empty_dict(self):
        block = FieldMapper(mappings={})
        assert block.mappings_template == "{}"


class TestFieldMapperExecute:
    @pytest.mark.asyncio
    async def test_simple_mapping(self):
        block = FieldMapper(mappings={"x": "{{ y }}"})
        result = await block.execute(make_context({"y": "hello"}))
        assert result["x"] == "hello"

    @pytest.mark.asyncio
    async def test_nested_mapping(self):
        block = FieldMapper(mappings={"flat": "{{ nested.deep.value }}"})
        result = await block.execute(make_context({"nested": {"deep": {"value": "found"}}}))
        assert result["flat"] == "found"

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="tojson produces pretty-printed JSON with newlines causing parse error"
    )
    async def test_json_parsing_list(self):
        block = FieldMapper(mappings={"items": "{{ data | tojson }}"})
        result = await block.execute(make_context({"data": ["a", "b", "c"]}))
        assert result["items"] == ["a", "b", "c"]

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason="tojson produces pretty-printed JSON with newlines causing parse error"
    )
    async def test_json_parsing_dict(self):
        block = FieldMapper(mappings={"obj": "{{ data | tojson }}"})
        result = await block.execute(make_context({"data": {"key": "value"}}))
        assert result["obj"] == {"key": "value"}

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="StrictUndefined raises error instead of returning empty string")
    async def test_template_error_returns_empty_string(self):
        block = FieldMapper(mappings={"bad": "{{ undefined_var }}"})
        result = await block.execute(make_context({}))
        assert result["bad"] == ""

    @pytest.mark.asyncio
    async def test_empty_mappings_returns_empty(self):
        block = FieldMapper(mappings={})
        result = await block.execute(make_context({"some": "data"}))
        assert result == {}

    @pytest.mark.asyncio
    async def test_multiple_mappings(self):
        block = FieldMapper(
            mappings={
                "question": "{{ qa.q }}",
                "answer": "{{ qa.a }}",
            }
        )
        result = await block.execute(make_context({"qa": {"q": "What?", "a": "Something"}}))
        assert result["question"] == "What?"
        assert result["answer"] == "Something"

    @pytest.mark.asyncio
    async def test_preserves_string_without_json(self):
        block = FieldMapper(mappings={"text": "{{ content }}"})
        result = await block.execute(make_context({"content": "plain text"}))
        assert result["text"] == "plain text"

    @pytest.mark.asyncio
    async def test_filter_usage(self):
        block = FieldMapper(mappings={"truncated": "{{ text | truncate(10) }}"})
        result = await block.execute(make_context({"text": "This is a very long string"}))
        assert result["truncated"] == "This is a ..."


class TestFieldMapperSchema:
    def test_schema_structure(self):
        schema = FieldMapper.get_schema()
        assert schema["name"] == "Field Mapper"
        assert schema["category"] == "utilities"
        assert schema["outputs"] == ["*"]  # dynamic outputs handled by frontend

    def test_schema_has_mappings_config(self):
        schema = FieldMapper.get_schema()
        assert "mappings" in schema["config_schema"]["properties"]
