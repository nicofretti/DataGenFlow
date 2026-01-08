from unittest.mock import MagicMock

from lib.blocks.commons.usage_tracker import UsageTracker


class TestUsageTracker:
    def setup_method(self):
        """clear tracker state before each test"""
        UsageTracker.clear_all()

    def test_callback_accumulates_usage(self):
        # simulate LiteLLM response
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.cache_read_input_tokens = 10

        kwargs = {"metadata": {"trace_id": "test-trace-1"}}

        # call callback twice
        UsageTracker.callback(kwargs, response, 0.0, 1.0)
        UsageTracker.callback(kwargs, response, 1.0, 2.0)

        usage = UsageTracker.get_and_clear("test-trace-1")

        assert usage["input_tokens"] == 200
        assert usage["output_tokens"] == 100
        assert usage["cached_tokens"] == 20

    def test_callback_without_trace_id_ignored(self):
        response = MagicMock()
        response.usage.prompt_tokens = 100

        kwargs = {"metadata": {}}  # no trace_id

        UsageTracker.callback(kwargs, response, 0.0, 1.0)

        # should not have any tracked usage
        assert len(UsageTracker._usage) == 0

    def test_callback_without_usage_ignored(self):
        response = MagicMock(spec=[])  # no usage attribute

        kwargs = {"metadata": {"trace_id": "test-trace-2"}}

        UsageTracker.callback(kwargs, response, 0.0, 1.0)

        # should not have any tracked usage
        assert len(UsageTracker._usage) == 0

    def test_get_and_clear_removes_entry(self):
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.cache_read_input_tokens = 0

        kwargs = {"metadata": {"trace_id": "test-trace-3"}}
        UsageTracker.callback(kwargs, response, 0.0, 1.0)

        # first call returns usage
        usage1 = UsageTracker.get_and_clear("test-trace-3")
        assert usage1["input_tokens"] == 100

        # second call returns zeros (entry cleared)
        usage2 = UsageTracker.get_and_clear("test-trace-3")
        assert usage2["input_tokens"] == 0

    def test_to_pipeline_usage(self):
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.cache_read_input_tokens = 25

        kwargs = {"metadata": {"trace_id": "test-trace-4"}}
        UsageTracker.callback(kwargs, response, 0.0, 1.0)

        usage = UsageTracker.to_pipeline_usage("test-trace-4")

        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.cached_tokens == 25

    def test_separate_trace_ids(self):
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.cache_read_input_tokens = 0

        UsageTracker.callback({"metadata": {"trace_id": "trace-a"}}, response, 0.0, 1.0)
        UsageTracker.callback({"metadata": {"trace_id": "trace-b"}}, response, 0.0, 1.0)
        UsageTracker.callback({"metadata": {"trace_id": "trace-a"}}, response, 0.0, 1.0)

        usage_a = UsageTracker.get_and_clear("trace-a")
        usage_b = UsageTracker.get_and_clear("trace-b")

        assert usage_a["input_tokens"] == 200  # called twice
        assert usage_b["input_tokens"] == 100  # called once

    def test_clear_all(self):
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.cache_read_input_tokens = 0

        UsageTracker.callback({"metadata": {"trace_id": "trace-1"}}, response, 0.0, 1.0)
        UsageTracker.callback({"metadata": {"trace_id": "trace-2"}}, response, 0.0, 1.0)

        assert len(UsageTracker._usage) == 2

        UsageTracker.clear_all()

        assert len(UsageTracker._usage) == 0

    def test_handles_none_token_values(self):
        response = MagicMock()
        response.usage.prompt_tokens = None
        response.usage.completion_tokens = None
        response.usage.cache_read_input_tokens = None

        kwargs = {"metadata": {"trace_id": "test-trace-5"}}

        UsageTracker.callback(kwargs, response, 0.0, 1.0)

        usage = UsageTracker.get_and_clear("test-trace-5")

        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0
        assert usage["cached_tokens"] == 0
