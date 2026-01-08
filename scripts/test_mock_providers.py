#!/usr/bin/env python3
"""
mock provider testing script for RagasMetrics and FieldMapper blocks

this script simulates LLM responses from different providers (OpenAI, Anthropic,
Google Gemini, Ollama) to test the block implementations without making real API calls.

usage:
    python scripts/test_mock_providers.py

the script tests:
1. FieldMapper with various input transformations
2. RagasMetrics with mocked LLM/embedding responses
3. UsageTracker callback accumulation
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.blocks.builtin.field_mapper import FieldMapper
from lib.blocks.builtin.ragas_metrics import RagasMetrics
from lib.blocks.commons.usage_tracker import UsageTracker
from lib.entities.block_execution_context import BlockExecutionContext


def make_context(state: dict, trace_id: str = "test-trace") -> BlockExecutionContext:
    """helper to create test context"""
    return BlockExecutionContext(
        job_id=0,
        trace_id=trace_id,
        pipeline_id=1,
        accumulated_state=state,
    )


class MockLLMResponse:
    """mock LiteLLM response object"""

    def __init__(
        self,
        content: str = "mocked response",
        prompt_tokens: int = 100,
        completion_tokens: int = 50,
    ):
        self.choices = [MagicMock(message=MagicMock(content=content))]
        self.usage = MagicMock(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_input_tokens=0,
        )


class MockEmbeddingResponse:
    """mock embedding response"""

    def __init__(self, dimensions: int = 1536):
        self.data = [MagicMock(embedding=[0.1] * dimensions)]


def create_mock_llm_config(provider: str):
    """create mock LLM config for different providers"""
    configs = {
        "openai": MagicMock(
            provider=MagicMock(value="openai"),
            model_name="gpt-4o-mini",
            endpoint="https://api.openai.com/v1",
            api_key="sk-test-key",
        ),
        "anthropic": MagicMock(
            provider=MagicMock(value="anthropic"),
            model_name="claude-3-5-sonnet-20241022",
            endpoint=None,
            api_key="sk-ant-test-key",
        ),
        "gemini": MagicMock(
            provider=MagicMock(value="gemini"),
            model_name="gemini-2.0-flash",
            endpoint=None,
            api_key="test-gemini-key",
        ),
        "ollama": MagicMock(
            provider=MagicMock(value="ollama"),
            model_name="llama3.2",
            endpoint="http://localhost:11434/v1/chat/completions",
            api_key=None,
        ),
    }
    return configs.get(provider, configs["openai"])


async def test_field_mapper():
    """test FieldMapper block with various inputs"""
    print("\n" + "=" * 60)
    print("Testing FieldMapper Block")
    print("=" * 60)

    # test 1: simple mapping
    print("\n1. Simple string mapping:")
    block = FieldMapper(mappings={"question": "{{ qa.q }}", "answer": "{{ qa.a }}"})
    result = await block.execute(
        make_context({"qa": {"q": "What is Python?", "a": "A programming language"}})
    )
    print("   Input: qa.q='What is Python?', qa.a='A programming language'")
    print(f"   Output: {result}")
    assert result["question"] == "What is Python?"
    assert result["answer"] == "A programming language"
    print("   ✓ PASSED")

    # test 2: JSON list mapping
    print("\n2. JSON list mapping with tojson filter:")
    block = FieldMapper(mappings={"contexts": "{{ sources | tojson }}"})
    result = await block.execute(make_context({"sources": ["doc1", "doc2", "doc3"]}))
    print("   Input: sources=['doc1', 'doc2', 'doc3']")
    print(f"   Output: {result}")
    assert isinstance(result["contexts"], list)
    assert len(result["contexts"]) == 3
    print("   ✓ PASSED")

    # test 3: nested object access
    print("\n3. Nested object access:")
    block = FieldMapper(mappings={"value": "{{ deep.nested.field }}"})
    result = await block.execute(make_context({"deep": {"nested": {"field": "found it!"}}}))
    print("   Input: deep.nested.field='found it!'")
    print(f"   Output: {result}")
    assert result["value"] == "found it!"
    print("   ✓ PASSED")

    # test 4: missing field handling
    print("\n4. Missing field handling (should return empty string):")
    block = FieldMapper(mappings={"missing": "{{ undefined_variable }}"})
    result = await block.execute(make_context({}))
    print("   Input: (empty)")
    print(f"   Output: {result}")
    assert result["missing"] == ""
    print("   ✓ PASSED")

    print("\n✓ All FieldMapper tests passed!")


async def test_usage_tracker():
    """test UsageTracker accumulation"""
    print("\n" + "=" * 60)
    print("Testing UsageTracker")
    print("=" * 60)

    UsageTracker.clear_all()

    # simulate multiple LLM calls
    trace_id = "test-usage-trace"

    print("\n1. Simulating 3 LLM calls for the same trace:")
    for i in range(3):
        response = MockLLMResponse(
            content=f"Response {i}",
            prompt_tokens=100 + i * 10,
            completion_tokens=50 + i * 5,
        )
        UsageTracker.callback(
            {"metadata": {"trace_id": trace_id}},
            response,
            start_time=0.0,
            end_time=1.0,
        )
        print(f"   Call {i + 1}: prompt={100 + i * 10}, completion={50 + i * 5}")

    usage = UsageTracker.get_and_clear(trace_id)
    expected_input = 100 + 110 + 120  # 330
    expected_output = 50 + 55 + 60  # 165

    print(f"\n   Accumulated: input={usage['input_tokens']}, output={usage['output_tokens']}")
    print(f"   Expected: input={expected_input}, output={expected_output}")

    assert usage["input_tokens"] == expected_input
    assert usage["output_tokens"] == expected_output
    print("   ✓ PASSED")

    # test 2: verify clearing
    print("\n2. Verify usage was cleared:")
    usage2 = UsageTracker.get_and_clear(trace_id)
    print(f"   After clear: input={usage2['input_tokens']}, output={usage2['output_tokens']}")
    assert usage2["input_tokens"] == 0
    assert usage2["output_tokens"] == 0
    print("   ✓ PASSED")

    print("\n✓ All UsageTracker tests passed!")


async def test_ragas_metrics_validation():
    """test RagasMetrics input validation"""
    print("\n" + "=" * 60)
    print("Testing RagasMetrics Input Validation")
    print("=" * 60)

    block = RagasMetrics(metrics=["faithfulness", "answer_relevancy"])

    # test 1: missing question
    print("\n1. Missing question returns empty scores:")
    result = await block.execute(make_context({"answer": "test"}))
    print("   Input: answer='test' (no question)")
    print(f"   Output: {result['ragas_scores']}")
    assert result["ragas_scores"]["passed"] is False
    assert result["ragas_scores"]["faithfulness"] == 0.0
    print("   ✓ PASSED")

    # test 2: missing answer
    print("\n2. Missing answer returns empty scores:")
    result = await block.execute(make_context({"question": "test"}))
    print("   Input: question='test' (no answer)")
    print(f"   Output: {result['ragas_scores']}")
    assert result["ragas_scores"]["passed"] is False
    print("   ✓ PASSED")

    # test 3: validate contexts normalization
    print("\n3. Contexts normalization:")
    test_cases = [
        (["a", "b"], ["a", "b"], "list input"),
        ('["a", "b"]', ["a", "b"], "JSON string input"),
        ("single", ["single"], "plain string input"),
        ([], [], "empty list"),
    ]

    for input_val, expected, desc in test_cases:
        result = block._normalize_contexts(input_val)
        print(f"   {desc}: {input_val} -> {result}")
        assert result == expected, f"Expected {expected}, got {result}"
    print("   ✓ All context normalization tests PASSED")

    print("\n✓ All RagasMetrics validation tests passed!")


async def test_ragas_metrics_with_provider(provider: str):
    """test RagasMetrics with mocked provider"""
    print(f"\n{'=' * 60}")
    print(f"Testing RagasMetrics with {provider.upper()} provider")
    print("=" * 60)

    config = create_mock_llm_config(provider)
    UsageTracker.clear_all()

    # create mock metric result
    mock_result = MagicMock()
    mock_result.value = 0.85

    # create mock metric with ascore method (ragas 0.4.x API)
    mock_metric = MagicMock()
    mock_metric.ascore = AsyncMock(return_value=mock_result)

    mock_embeddings = MagicMock()

    with (
        patch("lib.blocks.builtin.ragas_metrics.RagasMetrics._create_ragas_llm") as mock_create_llm,
        patch(
            "lib.blocks.builtin.ragas_metrics.RagasMetrics._create_ragas_embeddings"
        ) as mock_create_embeddings,
        patch("lib.blocks.builtin.ragas_metrics.RagasMetrics._build_metrics") as mock_build_metrics,
    ):
        mock_create_llm.return_value = MagicMock()
        mock_create_embeddings.return_value = mock_embeddings
        mock_build_metrics.return_value = {
            "faithfulness": mock_metric,
            "answer_relevancy": mock_metric,
        }

        # simulate usage tracking
        response = MockLLMResponse(prompt_tokens=200, completion_tokens=100)
        trace_id = f"test-{provider}"
        UsageTracker.callback({"metadata": {"trace_id": trace_id}}, response, 0.0, 1.0)

        block = RagasMetrics(
            metrics=["faithfulness", "answer_relevancy"],
            score_threshold=0.7,
        )

        context = make_context(
            {
                "question": "What is machine learning?",
                "answer": "Machine learning is a subset of AI that learns from data.",
                "contexts": ["ML is part of artificial intelligence"],
                "ground_truth": "Machine learning allows systems to learn from experience.",
            },
            trace_id=trace_id,
        )

        result = await block.execute(context)

        print(f"\n   Provider: {provider}")
        print(f"   Model: {config.model_name}")
        print(f"   Scores: {result['ragas_scores']}")
        print(f"   Usage: {result.get('_usage', {})}")

        # verify scores
        assert result["ragas_scores"]["faithfulness"] == 0.85
        assert result["ragas_scores"]["answer_relevancy"] == 0.85
        assert result["ragas_scores"]["passed"] is True
        print(f"   ✓ {provider.upper()} test PASSED")


async def run_all_tests():
    """run all mock provider tests"""
    print("\n" + "#" * 60)
    print("# Mock Provider Testing Script")
    print("# Testing FieldMapper, RagasMetrics, and UsageTracker")
    print("#" * 60)

    try:
        await test_field_mapper()
        await test_usage_tracker()
        await test_ragas_metrics_validation()

        # test with different providers
        for provider in ["openai", "anthropic", "gemini", "ollama"]:
            await test_ragas_metrics_with_provider(provider)

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
