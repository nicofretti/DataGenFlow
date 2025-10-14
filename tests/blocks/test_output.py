"""
tests for OutputBlock (formerly FormatterBlock)
"""

import pytest

from lib.blocks.builtin.formatter import OutputBlock


class TestOutputBlock:
    """test output formatting functionality"""

    @pytest.mark.asyncio
    async def test_basic_template_rendering(self):
        """renders simple text template"""
        block = OutputBlock(format_template="Result: test output")

        result = await block.execute({})

        assert result["pipeline_output"] == "Result: test output"

    @pytest.mark.asyncio
    async def test_jinja2_variables(self):
        """renders template with jinja2 variables"""
        block = OutputBlock(format_template="Hello {{ name }}, you are {{ age }} years old")

        input_data = {"name": "Alice", "age": 30}
        result = await block.execute(input_data)

        assert result["pipeline_output"] == "Hello Alice, you are 30 years old"

    @pytest.mark.asyncio
    async def test_jinja2_conditionals(self):
        """renders template with jinja2 conditionals"""
        template = "{% if premium %}Premium User{% else %}Regular User{% endif %}"

        # premium user
        block = OutputBlock(format_template=template)
        result = await block.execute({"premium": True})
        assert "Premium User" in result["pipeline_output"]

        # regular user
        result = await block.execute({"premium": False})
        assert "Regular User" in result["pipeline_output"]

    @pytest.mark.asyncio
    async def test_jinja2_loops(self):
        """renders template with jinja2 loops"""
        template = "Items: {% for item in items %}{{ item }}, {% endfor %}"
        block = OutputBlock(format_template=template)

        input_data = {"items": ["apple", "banana", "cherry"]}
        result = await block.execute(input_data)

        output = result["pipeline_output"]
        assert "apple" in output
        assert "banana" in output
        assert "cherry" in output

    @pytest.mark.asyncio
    async def test_custom_filter_tojson(self):
        """uses tojson custom filter"""
        template = "Data: {{ data | tojson }}"
        block = OutputBlock(format_template=template)

        input_data = {"data": {"key": "value", "num": 42}}
        result = await block.execute(input_data)

        output = result["pipeline_output"]
        assert '"key": "value"' in output or '"key":"value"' in output

    @pytest.mark.asyncio
    async def test_custom_filter_truncate(self):
        """uses truncate custom filter"""
        template = "{{ text | truncate(10) }}"
        block = OutputBlock(format_template=template)

        input_data = {"text": "This is a very long text that should be truncated"}
        result = await block.execute(input_data)

        output = result["pipeline_output"]
        assert len(output) <= 15  # truncate adds "..."

    @pytest.mark.asyncio
    async def test_empty_template(self):
        """handles empty template"""
        block = OutputBlock(format_template="")

        result = await block.execute({"data": "test"})

        assert result["pipeline_output"] == ""

    @pytest.mark.asyncio
    async def test_nested_variable_access(self):
        """accesses nested variables"""
        template = "User: {{ user.name }} ({{ user.email }})"
        block = OutputBlock(format_template=template)

        input_data = {"user": {"name": "Alice", "email": "alice@example.com"}}
        result = await block.execute(input_data)

        output = result["pipeline_output"]
        assert "Alice" in output
        assert "alice@example.com" in output

    @pytest.mark.asyncio
    async def test_accepts_all_inputs(self):
        """OutputBlock accepts any input fields"""
        block = OutputBlock(format_template="test")

        # should accept any fields in input
        input_data = {"field1": "value1", "field2": "value2", "field3": "value3"}

        result = await block.execute(input_data)
        assert "pipeline_output" in result
