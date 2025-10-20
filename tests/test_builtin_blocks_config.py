import pytest

from lib.blocks.builtin.llm import LLMBlock
from lib.blocks.builtin.validator import ValidatorBlock
from lib.blocks.builtin.json_validator import JSONValidatorBlock
from lib.blocks.builtin.formatter import OutputBlock


def test_llm_block_config_schema():
    schema = LLMBlock.get_config_schema()
    assert "model" in schema["properties"]
    assert "temperature" in schema["properties"]
    assert "max_tokens" in schema["properties"]
    assert schema["properties"]["temperature"]["type"] == "number"
    assert schema["properties"]["max_tokens"]["type"] == "integer"
    assert schema["properties"]["temperature"]["default"] == 0.7
    assert schema["properties"]["max_tokens"]["default"] == 2048


def test_validator_block_config_schema():
    schema = ValidatorBlock.get_config_schema()
    assert "min_length" in schema["properties"]
    assert "max_length" in schema["properties"]
    assert "forbidden_words" in schema["properties"]
    assert schema["properties"]["min_length"]["type"] == "integer"
    assert schema["properties"]["max_length"]["type"] == "integer"
    assert schema["properties"]["min_length"]["default"] == 0
    assert schema["properties"]["max_length"]["default"] == 100000


def test_json_validator_block_config_schema():
    schema = JSONValidatorBlock.get_config_schema()
    assert "field_name" in schema["properties"]
    assert "required_fields" in schema["properties"]
    assert "strict" in schema["properties"]
    assert schema["properties"]["field_name"]["type"] == "string"
    assert schema["properties"]["strict"]["type"] == "boolean"
    assert schema["properties"]["field_name"]["default"] == "assistant"
    assert schema["properties"]["strict"]["default"] is False


def test_output_block_config_schema():
    schema = OutputBlock.get_config_schema()
    assert "format_template" in schema["properties"]
    assert schema["properties"]["format_template"]["type"] == "string"
    assert schema["properties"]["format_template"]["default"] == "Result: {{ assistant }}"


def test_block_config_separate_from_runtime():
    # config is set at pipeline build time
    block = LLMBlock(model="gpt-4", temperature=0.9, max_tokens=1000)
    assert block.model == "gpt-4"
    assert block.temperature == 0.9
    assert block.max_tokens == 1000


def test_block_default_values():
    # blocks can use default values
    block = ValidatorBlock()
    assert block.min_length == 0
    assert block.max_length == 100000
    assert block.forbidden_words == []


def test_validator_block_handles_list_types():
    # verify that list types are properly represented in schema
    schema = ValidatorBlock.get_config_schema()
    assert schema["properties"]["forbidden_words"]["type"] == "array"
    assert "items" in schema["properties"]["forbidden_words"]


def test_json_validator_block_handles_list_types():
    # verify that list types are properly represented in schema
    schema = JSONValidatorBlock.get_config_schema()
    assert schema["properties"]["required_fields"]["type"] == "array"
    assert "items" in schema["properties"]["required_fields"]
