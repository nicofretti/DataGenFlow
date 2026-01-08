from unittest.mock import MagicMock, patch

import pytest

from lib.entities import pipeline as pipeline_entities
from lib.templates import template_registry
from lib.workflow import Pipeline as WorkflowPipeline


def test_template_registry_lists_all_templates():
    """test that all three templates are registered"""
    templates = template_registry.list_templates()
    template_ids = [t["id"] for t in templates]

    assert "json_generation" in template_ids
    assert "text_classification" in template_ids
    assert "qa_generation" in template_ids
    assert "ragas_evaluation" in template_ids


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
            # allow either "content" or "file_content" (for markdown templates)
            assert "content" in first_seed["metadata"] or "file_content" in first_seed["metadata"]

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
    """test qa_generation template has markdown chunking and two-step generation pipeline"""
    template = template_registry.get_template("qa_generation")

    assert template is not None
    assert template["name"] == "Q&A Generation"
    assert len(template["blocks"]) == 4

    # first block should be MarkdownMultiplierBlock
    assert template["blocks"][0]["type"] == "MarkdownMultiplierBlock"

    # second block should be TextGenerator
    assert template["blocks"][1]["type"] == "TextGenerator"

    # third block should be StructuredGenerator
    assert template["blocks"][2]["type"] == "StructuredGenerator"

    # fourth block should be JSONValidatorBlock
    assert template["blocks"][3]["type"] == "JSONValidatorBlock"

    # check schema has qa_pairs array
    schema = template["blocks"][2]["config"]["json_schema"]
    assert "properties" in schema
    assert "qa_pairs" in schema["properties"]
    assert schema["properties"]["qa_pairs"]["type"] == "array"


def test_ragas_evaluation_template_structure():
    """test ragas_evaluation template has correct blocks"""
    template = template_registry.get_template("ragas_evaluation")

    assert template is not None
    assert template["name"] == "QA Generation with RAGAS Evaluation"
    assert len(template["blocks"]) == 3

    # first block should be StructuredGenerator
    assert template["blocks"][0]["type"] == "StructuredGenerator"
    # verify schema has required fields
    schema = template["blocks"][0]["config"]["json_schema"]
    assert "question" in schema["properties"]
    assert "answer" in schema["properties"]
    assert "contexts" in schema["properties"]
    assert "ground_truth" in schema["properties"]

    # second block should be FieldMapper
    assert template["blocks"][1]["type"] == "FieldMapper"
    mappings = template["blocks"][1]["config"]["mappings"]
    assert "question" in mappings
    assert "answer" in mappings
    assert "contexts" in mappings
    assert "ground_truth" in mappings

    # third block should be RagasMetrics
    assert template["blocks"][2]["type"] == "RagasMetrics"
    ragas_config = template["blocks"][2]["config"]
    assert ragas_config["question_field"] == "question"
    assert ragas_config["answer_field"] == "answer"
    assert "faithfulness" in ragas_config["metrics"]
    assert "answer_relevancy" in ragas_config["metrics"]


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

    exec_result = await pipeline.execute(seed_data)
    assert isinstance(exec_result, pipeline_entities.ExecutionResult)

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

    exec_result = await pipeline.execute(seed_data)
    assert isinstance(exec_result, pipeline_entities.ExecutionResult)

    # verify template was rendered
    assert captured_prompt is not None
    assert "{{ content }}" not in captured_prompt, (
        "Template not rendered - still contains {{ content }}"
    )
    assert seed_data["content"] in captured_prompt, "Rendered prompt missing actual content"


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_qa_generation_template_renders_content(mock_llm):
    """test that qa_generation template properly renders {{ chunk_text }} and {{ assistant }}"""
    template = template_registry.get_template("qa_generation")
    assert template is not None
    pipeline_def = {"name": "Test Q&A", "blocks": template["blocks"]}
    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    # use file_content for markdown multiplier
    seed_data = {
        "file_content": "# Photosynthesis\n\nPhotosynthesis is how plants convert sunlight."
    }

    captured_prompts = []

    def capture_call(*args, **kwargs):
        captured_prompts.append(kwargs["messages"][0]["content"])
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]

        # first call: questions (from TextGenerator), second call: Q&A pairs (from StructuredGenerator)
        if len(captured_prompts) == 1:
            mock_response.choices[0].message.content = "What is photosynthesis?"
        else:
            mock_response.choices[0].message.content = (
                '{"qa_pairs": [{"question": "What is photosynthesis?", '
                '"answer": "How plants convert sunlight."}]}'
            )

        return mock_response

    mock_llm.side_effect = capture_call

    # multiplier returns list of results
    results = await pipeline.execute(seed_data)
    assert isinstance(results, list)
    assert len(results) > 0, "Expected at least one result from multiplier"

    # verify prompts were rendered
    assert len(captured_prompts) >= 2
    # verify first prompt (TextGenerator) rendered {{ chunk_text }}
    assert "{{ chunk_text }}" not in captured_prompts[0], "TextGenerator prompt not rendered"

    # verify second prompt (StructuredGenerator) rendered {{ assistant }} and {{ chunk_text }}
    assert "{{ assistant }}" not in captured_prompts[1], (
        "StructuredGenerator prompt not rendered - still has {{ assistant }}"
    )
    assert "{{ chunk_text }}" not in captured_prompts[1], (
        "StructuredGenerator prompt not rendered - still has {{ chunk_text }}"
    )
