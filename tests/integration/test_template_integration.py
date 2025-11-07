"""
Integration tests for pipeline templates

These tests verify that all templates work end-to-end with real execution flow.
Tests are marked with @pytest.mark.integration and use actual LLM calls (mocked).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from lib.templates import template_registry
from lib.workflow import Pipeline as WorkflowPipeline


@pytest.mark.integration
@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_json_generation_template_end_to_end(mock_llm):
    """
    test json_generation template executes successfully with realistic data

    flow:
    1. load template
    2. execute with seed containing 'content' field
    3. verify StructuredGenerator generates valid JSON
    4. verify JSONValidator validates correctly
    5. verify final output is proper JSON
    """
    # setup mock LLM response with valid JSON
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(
        {
            "title": "Electric Vehicles",
            "description": "Electric cars reduce emissions but require charging infrastructure.",
        }
    )
    mock_llm.return_value = mock_response

    # load template and create pipeline
    template = template_registry.get_template("json_generation")
    assert template is not None, "json_generation template not found"

    pipeline_def = {"name": "Test JSON Generation", "blocks": template["blocks"]}
    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    # execute with realistic seed data
    seed_data = {
        "content": "Electric cars reduce emissions but require charging infrastructure. "
        "They are becoming more popular as battery technology improves."
    }

    result, trace, trace_id = await pipeline.execute(seed_data)

    # verify execution completed
    assert result is not None
    assert trace is not None
    assert len(trace) == 2  # StructuredGenerator + JSONValidator

    # verify StructuredGenerator output
    structured_output = trace[0]["output"]
    assert "generated" in structured_output
    assert isinstance(structured_output["generated"], dict)
    assert "title" in structured_output["generated"]
    assert "description" in structured_output["generated"]

    # verify JSONValidator output
    validator_output = trace[1]["output"]
    assert validator_output["valid"] is True
    assert validator_output["parsed_json"] is not None

    # verify final accumulated state
    final_state = trace[-1]["accumulated_state"]
    assert "generated" in final_state
    assert "valid" in final_state
    assert "parsed_json" in final_state

    # verify LLM was called with rendered template (no {{ content }})
    call_args = mock_llm.call_args
    messages = call_args.kwargs["messages"]
    prompt = messages[0]["content"]
    assert "{{ content }}" not in prompt, "Template not rendered"
    assert seed_data["content"] in prompt, "Content not injected into prompt"


@pytest.mark.integration
@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_text_classification_template_end_to_end(mock_llm):
    """
    test text_classification template with multiple categories

    flow:
    1. load template
    2. test with technology content
    3. verify category classification
    4. verify confidence score
    5. test with different category content
    """
    # test case 1: technology content
    mock_response_tech = MagicMock()
    mock_response_tech.choices = [MagicMock()]
    mock_response_tech.choices[0].message.content = json.dumps(
        {"category": "technology", "confidence": 0.95}
    )
    mock_llm.return_value = mock_response_tech

    template = template_registry.get_template("text_classification")
    assert template is not None, "text_classification template not found"

    pipeline_def = {"name": "Test Classification", "blocks": template["blocks"]}
    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    # test with technology content
    tech_seed = {
        "content": "Artificial intelligence and machine learning are transforming software development. "
        "Neural networks can now write code and detect bugs automatically."
    }

    result, trace, trace_id = await pipeline.execute(tech_seed)

    # verify execution
    assert len(trace) == 2  # StructuredGenerator + JSONValidator

    # verify classification result
    classification = trace[0]["output"]["generated"]
    assert classification["category"] == "technology"
    assert 0.0 <= classification["confidence"] <= 1.0

    # verify validation passed
    assert trace[1]["output"]["valid"] is True

    # test case 2: environment content
    mock_response_env = MagicMock()
    mock_response_env.choices = [MagicMock()]
    mock_response_env.choices[0].message.content = json.dumps(
        {"category": "environment", "confidence": 0.88}
    )
    mock_llm.return_value = mock_response_env

    # create new pipeline instance
    pipeline2 = WorkflowPipeline.load_from_dict(pipeline_def)

    env_seed = {
        "content": "Climate change is causing rising sea levels and extreme weather events. "
        "Renewable energy sources like solar and wind are crucial for reducing emissions."
    }

    exec_result2 = await pipeline2.execute(env_seed)
    assert isinstance(exec_result2, tuple)
    result2, trace2, trace_id2 = exec_result2

    # verify different category
    classification2 = trace2[0]["output"]["generated"]
    assert classification2["category"] == "environment"
    assert trace2[1]["output"]["valid"] is True


@pytest.mark.integration
@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_qa_generation_template_end_to_end(mock_llm):
    """
    test qa_generation template with markdown chunker

    flow:
    1. MarkdownMultiplierBlock chunks markdown
    2. TextGenerator generates questions per chunk
    3. StructuredGenerator generates Q&A pairs
    4. JSONValidator validates structure
    5. verify accumulated state flows correctly
    """
    call_count = [0]

    def mock_llm_responses(*args, **kwargs):
        call_count[0] += 1
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]

        # first call: TextGenerator generates questions
        if call_count[0] == 1:
            mock_response.choices[0].message.content = (
                "What is photosynthesis?\n"
                "What role does chlorophyll play?\n"
                "What is the end product of photosynthesis?"
            )
        # second call: StructuredGenerator generates Q&A pairs
        else:
            mock_response.choices[0].message.content = json.dumps(
                {
                    "qa_pairs": [
                        {
                            "question": "What is photosynthesis?",
                            "answer": "Photosynthesis is the process by which plants convert sunlight into energy.",
                        },
                        {
                            "question": "What role does chlorophyll play?",
                            "answer": "Chlorophyll in leaves absorbs light, triggering chemical reactions.",
                        },
                        {
                            "question": "What is the end product of photosynthesis?",
                            "answer": "The end product is glucose, which plants use for energy.",
                        },
                    ]
                }
            )

        return mock_response

    mock_llm.side_effect = mock_llm_responses

    # load template
    template = template_registry.get_template("qa_generation")
    assert template is not None, "qa_generation template not found"

    pipeline_def = {"name": "Test Q&A", "blocks": template["blocks"]}
    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    # execute with markdown content
    seed_data = {
        "file_content": "# Photosynthesis\n\nPhotosynthesis is the process by which plants convert sunlight into energy. "
        "Chlorophyll in leaves absorbs light, which triggers chemical reactions that produce glucose."
    }

    # multiplier pipeline returns list of results
    results = await pipeline.execute(seed_data)

    assert isinstance(results, list)
    assert len(results) > 0

    # verify first result (test one chunk)
    result, trace, trace_id = results[0]

    # verify all 3 blocks executed (after chunker)
    assert len(trace) == 3  # TextGenerator + StructuredGenerator + JSONValidator

    # verify TextGenerator output (questions)
    text_gen_output = trace[0]["output"]
    assert "assistant" in text_gen_output
    questions = text_gen_output["assistant"]
    assert "photosynthesis" in questions.lower()

    # verify StructuredGenerator output (Q&A pairs)
    structured_output = trace[1]["output"]
    assert "generated" in structured_output
    qa_data = structured_output["generated"]
    assert "qa_pairs" in qa_data
    assert isinstance(qa_data["qa_pairs"], list)
    assert len(qa_data["qa_pairs"]) >= 3

    # verify Q&A pair structure
    for pair in qa_data["qa_pairs"]:
        assert "question" in pair
        assert "answer" in pair
        assert isinstance(pair["question"], str)
        assert isinstance(pair["answer"], str)
        assert len(pair["question"]) > 0
        assert len(pair["answer"]) > 0

    # verify JSONValidator output
    validator_output = trace[2]["output"]
    assert validator_output["valid"] is True
    assert validator_output["parsed_json"] is not None

    # verify accumulated state contains all outputs
    final_state = trace[-1]["accumulated_state"]
    assert "chunk_text" in final_state  # from MarkdownMultiplierBlock
    assert "assistant" in final_state  # from TextGenerator
    assert "generated" in final_state  # from StructuredGenerator
    assert "valid" in final_state  # from JSONValidator
    assert "parsed_json" in final_state  # from JSONValidator

    # verify both LLM calls had rendered templates (per chunk)
    assert mock_llm.call_count >= 2

    # first call should have {{ chunk_text }} rendered
    first_call_messages = mock_llm.call_args_list[0].kwargs["messages"]
    first_prompt = first_call_messages[0]["content"]
    assert "{{ chunk_text }}" not in first_prompt

    # second call should have {{ assistant }} and {{ chunk_text }} rendered
    second_call_messages = mock_llm.call_args_list[1].kwargs["messages"]
    second_prompt = second_call_messages[0]["content"]
    assert "{{ assistant }}" not in second_prompt
    assert "{{ chunk_text }}" not in second_prompt


@pytest.mark.integration
@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_template_handles_invalid_json_gracefully(mock_llm):
    """test that templates handle malformed JSON from LLM"""
    # mock LLM returns invalid JSON
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is not valid JSON!"
    mock_llm.return_value = mock_response

    template = template_registry.get_template("json_generation")
    assert template is not None
    pipeline_def = {"name": "Test Invalid JSON", "blocks": template["blocks"]}
    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    seed_data = {"content": "Test content"}

    result, trace, trace_id = await pipeline.execute(seed_data)

    # execution should complete (not crash)
    assert trace is not None
    assert len(trace) == 2

    # JSONValidator should mark as invalid
    validator_output = trace[1]["output"]
    assert validator_output["valid"] is False
    assert validator_output["parsed_json"] is None


@pytest.mark.integration
@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_template_with_empty_content(mock_llm):
    """test templates handle empty content field"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(
        {"title": "Empty", "description": "Empty content provided"}
    )
    mock_llm.return_value = mock_response

    template = template_registry.get_template("json_generation")
    assert template is not None
    pipeline_def = {"name": "Test Empty", "blocks": template["blocks"]}
    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    # empty content
    seed_data = {"content": ""}

    result, trace, trace_id = await pipeline.execute(seed_data)

    # should complete without error
    assert trace is not None
    assert len(trace) == 2

    # verify prompt was sent (even with empty content)
    assert mock_llm.called


@pytest.mark.integration
@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_all_templates_load_and_execute(mock_llm):
    """smoke test: verify all templates can load and execute without crashing"""
    # generic mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(
        {
            "title": "Test",
            "description": "Test",
            "category": "technology",
            "confidence": 0.5,
            "qa_pairs": [{"question": "Test?", "answer": "Test."}],
        }
    )
    mock_llm.return_value = mock_response

    templates = template_registry.list_templates()

    for template_info in templates:
        template_id = template_info["id"]
        template = template_registry.get_template(template_id)

        assert template is not None, f"Template {template_id} not found"
        assert "blocks" in template, f"Template {template_id} has no blocks"

        # create and execute pipeline
        pipeline_def = {"name": f"Test {template_id}", "blocks": template["blocks"]}
        pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

        # qa_generation uses file_content, others use content
        if template_id == "qa_generation":
            seed_data = {"file_content": "# Test\n\nTest content for smoke test"}
        else:
            seed_data = {"content": "Test content for smoke test"}

        # should not crash
        execution_result = await pipeline.execute(seed_data)

        # qa_generation (multiplier pipeline) returns list, others return tuple
        if template_id == "qa_generation":
            assert isinstance(execution_result, list)
            assert len(execution_result) > 0
            first_result = execution_result[0]
            assert isinstance(first_result, tuple)
            result, trace, trace_id = first_result
        else:
            assert isinstance(execution_result, tuple)
            result, trace, trace_id = execution_result

        assert trace is not None
        assert len(trace) > 0
        assert trace_id is not None
