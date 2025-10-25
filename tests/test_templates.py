from unittest.mock import MagicMock, patch

import pytest

from lib.templates import template_registry
from lib.workflow import Pipeline as WorkflowPipeline


def test_template_registry_lists_all_templates():
    """test that all three templates are registered"""
    templates = template_registry.list_templates()
    template_ids = [t["id"] for t in templates]

    assert "json_generation" in template_ids
    assert "text_classification" in template_ids
    assert "qa_generation" in template_ids


def test_templates_have_required_fields():
    """test that all templates have required structure"""
    templates = template_registry.list_templates()

    for template in templates:
        assert "id" in template
        assert "name" in template
        assert "description" in template
        assert "example_seed" in template


def test_template_seeds_use_content_field():
    """test that all template seeds use simplified content structure"""
    templates = template_registry.list_templates()

    for template in templates:
        example_seed = template.get("example_seed")
        if example_seed:
            # seeds are arrays
            assert isinstance(example_seed, list)
            assert len(example_seed) > 0

            # check first seed item
            first_seed = example_seed[0]
            assert "metadata" in first_seed
            assert "content" in first_seed["metadata"]

            # ensure no old-style system/user fields
            assert "system" not in first_seed["metadata"]
            assert "user" not in first_seed["metadata"]


def test_json_generation_template_structure():
    """test json_generation template has correct blocks"""
    template = template_registry.get_template("json_generation")

    assert template is not None
    assert template["name"] == "JSON Generation"
    assert "blocks" in template
    assert len(template["blocks"]) == 2

    # first block should be StructuredGenerator
    assert template["blocks"][0]["type"] == "StructuredGenerator"
    assert "json_schema" in template["blocks"][0]["config"]

    # second block should be JSONValidatorBlock
    assert template["blocks"][1]["type"] == "JSONValidatorBlock"


def test_text_classification_template_structure():
    """test text_classification template has enum categories"""
    template = template_registry.get_template("text_classification")

    assert template is not None
    assert template["name"] == "Text Classification"

    # check schema has enum
    schema = template["blocks"][0]["config"]["json_schema"]
    assert "properties" in schema
    assert "category" in schema["properties"]
    assert "enum" in schema["properties"]["category"]

    # verify categories
    categories = schema["properties"]["category"]["enum"]
    assert "environment" in categories
    assert "technology" in categories


def test_qa_generation_template_structure():
    """test qa_generation template has two-step pipeline"""
    template = template_registry.get_template("qa_generation")

    assert template is not None
    assert template["name"] == "Q&A Generation"
    assert len(template["blocks"]) == 3

    # first block should be TextGenerator
    assert template["blocks"][0]["type"] == "TextGenerator"

    # second block should be StructuredGenerator
    assert template["blocks"][1]["type"] == "StructuredGenerator"

    # third block should be JSONValidatorBlock
    assert template["blocks"][2]["type"] == "JSONValidatorBlock"

    # check schema has qa_pairs array
    schema = template["blocks"][1]["config"]["json_schema"]
    assert "properties" in schema
    assert "qa_pairs" in schema["properties"]
    assert schema["properties"]["qa_pairs"]["type"] == "array"


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_json_generation_template_renders_content(mock_llm):
    """test that json_generation template properly renders {{ content }} in prompts"""
    template = template_registry.get_template("json_generation")
    assert template is not None
    pipeline_def = {"name": "Test JSON", "blocks": template["blocks"]}
    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    seed_data = {"content": "Electric cars reduce emissions but require charging infrastructure."}

    # capture what prompt is sent to LLM
    captured_prompt: str | None = None

    def capture_call(*args, **kwargs):
        nonlocal captured_prompt
        captured_prompt = kwargs["messages"][0]["content"]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"title": "Test", "description": "Test desc"}'
        return mock_response

    mock_llm.side_effect = capture_call

    result, trace, trace_id = await pipeline.execute(seed_data)

    # verify template was rendered - should NOT contain {{ content }}
    assert captured_prompt is not None
    assert "{{ content }}" not in captured_prompt, (
        "Template not rendered - still contains {{ content }}"
    )

    # verify actual content is in the prompt
    assert seed_data["content"] in captured_prompt, "Rendered prompt missing actual content"


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_text_classification_template_renders_content(mock_llm):
    """test that text_classification template properly renders {{ content }} in prompts"""
    template = template_registry.get_template("text_classification")
    assert template is not None
    pipeline_def = {"name": "Test Classification", "blocks": template["blocks"]}
    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    seed_data = {"content": "Solar panels convert sunlight into electricity."}

    captured_prompt: str | None = None

    def capture_call(*args, **kwargs):
        nonlocal captured_prompt
        captured_prompt = kwargs["messages"][0]["content"]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"category": "environment", "confidence": 0.9}'
        return mock_response

    mock_llm.side_effect = capture_call

    result, trace, trace_id = await pipeline.execute(seed_data)

    # verify template was rendered
    assert captured_prompt is not None
    assert "{{ content }}" not in captured_prompt, (
        "Template not rendered - still contains {{ content }}"
    )
    assert seed_data["content"] in captured_prompt, "Rendered prompt missing actual content"


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_qa_generation_template_renders_content(mock_llm):
    """test that qa_generation template properly renders {{ content }} and {{ assistant }}"""
    template = template_registry.get_template("qa_generation")
    assert template is not None
    pipeline_def = {"name": "Test Q&A", "blocks": template["blocks"]}
    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    seed_data = {"content": "Photosynthesis is how plants convert sunlight."}

    captured_prompts = []

    def capture_call(*args, **kwargs):
        captured_prompts.append(kwargs["messages"][0]["content"])
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]

        # first call: questions, second call: Q&A pairs
        if len(captured_prompts) == 1:
            mock_response.choices[0].message.content = "What is photosynthesis?"
        else:
            mock_response.choices[0].message.content = (
                '{"qa_pairs": [{"question": "What is photosynthesis?", '
                '"answer": "How plants convert sunlight."}]}'
            )

        return mock_response

    mock_llm.side_effect = capture_call

    result, trace, trace_id = await pipeline.execute(seed_data)

    # verify first prompt (TextGenerator) rendered {{ content }}
    assert len(captured_prompts) >= 2
    assert "{{ content }}" not in captured_prompts[0], "TextGenerator prompt not rendered"
    assert seed_data["content"] in captured_prompts[0], "TextGenerator prompt missing content"

    # verify second prompt (StructuredGenerator) rendered {{ assistant }} and {{ content }}
    assert "{{ assistant }}" not in captured_prompts[1], (
        "StructuredGenerator prompt not rendered - still has {{ assistant }}"
    )
    assert "{{ content }}" not in captured_prompts[1], (
        "StructuredGenerator prompt not rendered - still has {{ content }}"
    )
    assert seed_data["content"] in captured_prompts[1], "StructuredGenerator prompt missing content"
