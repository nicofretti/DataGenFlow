"""
tests for JSONValidatorBlock
"""

import pytest

from lib.blocks.builtin.json_validator import JSONValidatorBlock


class TestJSONValidatorBlock:
    """test json validation functionality"""

    @pytest.mark.asyncio
    async def test_valid_json_returns_parsed_object(self, make_context):
        """valid json is parsed and returned"""
        block = JSONValidatorBlock(field_name="data")

        input_data = {"data": '{"key": "value", "number": 42}'}
        result = await block.execute(make_context(input_data))

        assert result["valid"] is True
        assert result["parsed_json"] == {"key": "value", "number": 42}

    @pytest.mark.asyncio
    async def test_invalid_json_returns_valid_false(self, make_context):
        """invalid json returns valid=false"""
        block = JSONValidatorBlock(field_name="data")

        input_data = {"data": "not valid json {"}
        result = await block.execute(make_context(input_data))

        assert result["valid"] is False
        assert result["parsed_json"] is None

    @pytest.mark.asyncio
    async def test_required_fields_validation(self, make_context):
        """validates required fields in json"""
        block = JSONValidatorBlock(field_name="data", required_fields=["name", "email"])

        # valid - has required fields
        valid_data = {"data": '{"name": "John", "email": "john@example.com"}'}
        result = await block.execute(make_context(valid_data))
        assert result["valid"] is True

        # invalid - missing email
        invalid_data = {"data": '{"name": "John"}'}
        result = await block.execute(make_context(invalid_data))
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_strict_mode_raises_error(self, make_context):
        """strict mode raises exception on invalid json"""
        block = JSONValidatorBlock(field_name="data", strict=True)

        input_data = {"data": "invalid json"}

        with pytest.raises(ValueError):
            await block.execute(make_context(input_data))

    @pytest.mark.asyncio
    async def test_custom_field_name(self, make_context):
        """can validate json from any field"""
        block = JSONValidatorBlock(field_name="response")

        input_data = {"response": '{"status": "ok"}'}
        result = await block.execute(make_context(input_data))

        assert result["valid"] is True
        assert result["parsed_json"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_nested_json_structures(self, make_context):
        """handles nested json objects"""
        block = JSONValidatorBlock(field_name="data")

        nested_json = '{"user": {"name": "Alice", "age": 30}, "items": [1, 2, 3]}'
        input_data = {"data": nested_json}
        result = await block.execute(make_context(input_data))

        assert result["valid"] is True
        assert result["parsed_json"]["user"]["name"] == "Alice"
        assert result["parsed_json"]["items"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_missing_field_returns_invalid(self, make_context):
        """missing source field returns valid=false"""
        block = JSONValidatorBlock(field_name="data")

        input_data = {"other_field": "value"}
        result = await block.execute(make_context(input_data))

        assert result["valid"] is False
        assert result["parsed_json"] is None
