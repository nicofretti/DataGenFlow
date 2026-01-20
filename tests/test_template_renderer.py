"""tests for template_renderer module"""

import pytest

from lib.template_renderer import render_template


def test_render_simple_template():
    """test basic template rendering with variables"""
    template = "Hello {{ name }}"
    context = {"name": "World"}
    result = render_template(template, context)
    assert result == "Hello World"


def test_render_template_with_conditionals():
    """test template rendering with if/else"""
    template = "{% if active %}Active{% else %}Inactive{% endif %}"

    result_true = render_template(template, {"active": True})
    assert result_true == "Active"

    result_false = render_template(template, {"active": False})
    assert result_false == "Inactive"


def test_render_template_with_loops():
    """test template rendering with for loops"""
    template = "{% for item in items %}{{ item }},{% endfor %}"
    context = {"items": ["a", "b", "c"]}
    result = render_template(template, context)
    assert result == "a,b,c,"


def test_tojson_filter_with_dict():
    """test tojson filter serializes dict correctly"""
    template = "{{ data | tojson }}"
    context = {"data": {"key": "value", "number": 42}}
    result = render_template(template, context)
    # check it contains the data (exact formatting may vary)
    assert '"key": "value"' in result
    assert '"number": 42' in result


def test_tojson_filter_with_list():
    """test tojson filter serializes list correctly"""
    template = "{{ items | tojson }}"
    context = {"items": ["apple", "banana", "cherry"]}
    result = render_template(template, context)
    assert '"apple"' in result
    assert '"banana"' in result
    assert '"cherry"' in result


def test_tojson_filter_with_undefined_variable():
    """test tojson filter raises clear error for undefined variables"""
    template = "{{ missing_var | tojson }}"
    context = {}

    with pytest.raises(ValueError) as exc_info:
        render_template(template, context)

    error_msg = str(exc_info.value)
    # verify error message is clear
    assert "undefined variable" in error_msg.lower()
    assert "missing_var" in error_msg
    assert "JSON" in error_msg


def test_tojson_filter_error_includes_variable_name():
    """test that tojson filter error message includes the specific variable name"""
    template = "{{ categorical_fields | tojson }}"
    context = {"other_field": "value"}

    with pytest.raises(ValueError) as exc_info:
        render_template(template, context)

    error_msg = str(exc_info.value)
    assert "categorical_fields" in error_msg


def test_tojson_filter_nested_in_complex_template():
    """test tojson filter in a realistic template like StructureSampler uses"""
    template = "{{ fields | tojson }}"

    # with defined variable - should work
    context = {"fields": ["field1", "field2"]}
    result = render_template(template, context)
    assert '"field1"' in result
    assert '"field2"' in result

    # without defined variable - should fail clearly
    with pytest.raises(ValueError) as exc_info:
        render_template(template, {})

    assert "fields" in str(exc_info.value)


def test_truncate_filter():
    """test truncate filter works correctly"""
    template = "{{ text | truncate(10) }}"

    # short text - no truncation
    result = render_template(template, {"text": "short"})
    assert result == "short"

    # long text - gets truncated
    result = render_template(template, {"text": "this is a very long text"})
    assert result == "this is a ..."


def test_undefined_variable_without_filter():
    """test that undefined variables without filters also raise clear errors"""
    template = "{{ missing }}"
    context = {}

    with pytest.raises(ValueError) as exc_info:
        render_template(template, context)

    error_msg = str(exc_info.value)
    assert "undefined" in error_msg.lower()


def test_template_syntax_error():
    """test that template syntax errors are caught and reported"""
    template = "{% if missing %} unclosed"
    context = {}

    with pytest.raises(ValueError) as exc_info:
        render_template(template, context)

    error_msg = str(exc_info.value)
    assert "syntax error" in error_msg.lower()
