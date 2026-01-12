import pytest

from lib.blocks.commons.template_utils import (
    clean_internal_fields,
    clean_metadata_fields,
    normalize_template_param,
    parse_llm_json_response,
    render_and_parse_json,
    render_template_or_return_default,
    validate_string_list,
)
from lib.errors import BlockExecutionError


class TestRenderAndParseJson:
    def test_render_and_parse_list(self):
        template = '["field1", "field2"]'
        context = {}
        result = render_and_parse_json(template, context, "test_field", list)
        assert result == ["field1", "field2"]

    def test_render_and_parse_dict(self):
        template = '{"key": "value"}'
        context = {}
        result = render_and_parse_json(template, context, "test_field", dict)
        assert result == {"key": "value"}

    def test_render_with_template_vars(self):
        template = '["{{ var1 }}", "{{ var2 }}"]'
        context = {"var1": "field1", "var2": "field2"}
        result = render_and_parse_json(template, context, "test_field", list)
        assert result == ["field1", "field2"]

    def test_invalid_json_raises_error(self):
        template = '["field1", "field2"'  # missing closing bracket
        context = {}
        with pytest.raises(BlockExecutionError) as exc_info:
            render_and_parse_json(template, context, "test_field", list)
        assert "must be valid JSON" in str(exc_info.value)

    def test_wrong_type_raises_error(self):
        template = '["field1"]'
        context = {}
        with pytest.raises(BlockExecutionError) as exc_info:
            render_and_parse_json(template, context, "test_field", dict)
        assert "must be a JSON dict" in str(exc_info.value)


class TestValidateStringList:
    def test_valid_string_list(self):
        value = ["field1", "field2", "field3"]
        validate_string_list(value, "test_field")  # should not raise

    def test_empty_list(self):
        value = []
        validate_string_list(value, "test_field")  # should not raise

    def test_list_with_non_strings_raises_error(self):
        value = ["field1", 123, "field3"]
        with pytest.raises(BlockExecutionError) as exc_info:
            validate_string_list(value, "test_field")
        assert "must be strings" in str(exc_info.value)

    def test_list_with_mixed_types_raises_error(self):
        value = ["field1", None, "field3"]
        with pytest.raises(BlockExecutionError) as exc_info:
            validate_string_list(value, "test_field")
        assert "must be strings" in str(exc_info.value)


class TestNormalizeTemplateParam:
    def test_normalize_list(self):
        value = ["field1", "field2"]
        result = normalize_template_param(value, list)
        assert result == '["field1", "field2"]'

    def test_normalize_dict(self):
        value = {"key": "value"}
        result = normalize_template_param(value, dict)
        assert result == '{"key": "value"}'

    def test_normalize_string_unchanged(self):
        value = "{{ some_template }}"
        result = normalize_template_param(value, list)
        assert result == "{{ some_template }}"

    def test_normalize_json_string_unchanged(self):
        value = '["field1", "field2"]'
        result = normalize_template_param(value, list)
        assert result == '["field1", "field2"]'


class TestParseLlmJsonResponse:
    def test_parse_direct_json(self):
        content = '{"field": "value"}'
        result = parse_llm_json_response(content, "test_field")
        assert result == {"field": "value"}

    def test_parse_from_markdown_code_block(self):
        content = """Here is the result:
```json
{"field": "value"}
```
"""
        result = parse_llm_json_response(content, "test_field")
        assert result == {"field": "value"}

    def test_parse_from_markdown_without_language(self):
        content = """Here is the result:
```
{"field": "value"}
```
"""
        result = parse_llm_json_response(content, "test_field")
        assert result == {"field": "value"}

    def test_parse_from_text_with_json_embedded(self):
        content = 'Here is the result: {"field": "value"} and some more text'
        result = parse_llm_json_response(content, "test_field")
        assert result == {"field": "value"}

    def test_parse_multiline_json(self):
        content = """{
    "field1": "value1",
    "field2": "value2"
}"""
        result = parse_llm_json_response(content, "test_field")
        assert result == {"field1": "value1", "field2": "value2"}

    def test_unparseable_content_raises_error(self):
        content = "This is not JSON at all"
        with pytest.raises(BlockExecutionError) as exc_info:
            parse_llm_json_response(content, "test_field")
        assert "Failed to parse" in str(exc_info.value)


class TestCleanInternalFields:
    def test_clean_internal_fields(self):
        state = {
            "field1": "value1",
            "field2": "value2",
            "_usage": {"tokens": 100},
            "_hints": {"hint": "value"},
            "_internal": "data",
        }
        result = clean_internal_fields(state)
        assert result == {"field1": "value1", "field2": "value2"}

    def test_clean_no_internal_fields(self):
        state = {"field1": "value1", "field2": "value2"}
        result = clean_internal_fields(state)
        assert result == {"field1": "value1", "field2": "value2"}

    def test_clean_only_internal_fields(self):
        state = {"_usage": {"tokens": 100}, "_hints": {"hint": "value"}}
        result = clean_internal_fields(state)
        assert result == {}

    def test_original_state_not_mutated(self):
        state = {"field1": "value1", "_usage": {"tokens": 100}}
        result = clean_internal_fields(state)
        assert "_usage" in state  # original unchanged
        assert "_usage" not in result


class TestCleanMetadataFields:
    def test_clean_metadata_fields(self):
        state = {
            "field1": "value1",
            "samples": [{"a": 1}],
            "target_count": 10,
            "categorical_fields": ["cat"],
            "numeric_fields": ["num"],
            "dependencies": {"dep": ["field"]},
            "comparison_fields": ["comp"],
            "similarity_threshold": 0.85,
        }
        result = clean_metadata_fields(state)
        assert result == {"field1": "value1"}

    def test_clean_no_metadata_fields(self):
        state = {"field1": "value1", "field2": "value2"}
        result = clean_metadata_fields(state)
        assert result == {"field1": "value1", "field2": "value2"}

    def test_clean_only_metadata_fields(self):
        state = {"samples": [{"a": 1}], "target_count": 10}
        result = clean_metadata_fields(state)
        assert result == {}

    def test_original_state_not_mutated(self):
        state = {"field1": "value1", "samples": [{"a": 1}]}
        result = clean_metadata_fields(state)
        assert "samples" in state  # original unchanged
        assert "samples" not in result


class TestRenderTemplateOrReturnDefault:
    def test_render_template(self):
        template = "Hello {{ name }}"
        context = {"name": "World"}
        result = render_template_or_return_default(template, context, "default")
        assert result == "Hello World"

    def test_return_default_when_none(self):
        result = render_template_or_return_default(None, {}, "default")
        assert result == "default"

    def test_return_default_when_empty_string(self):
        result = render_template_or_return_default("", {}, "default")
        assert result == "default"

    def test_render_empty_template_as_empty(self):
        result = render_template_or_return_default("   ", {"data": "value"}, "default")
        # jinja2 renders whitespace as whitespace
        assert result == "   "
