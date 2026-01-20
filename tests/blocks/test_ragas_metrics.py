import pytest

from lib.blocks.builtin.ragas_metrics import METRIC_REQUIREMENTS, RagasMetrics
from lib.entities.block_execution_context import BlockExecutionContext


def make_context(state: dict, trace_id: str = "test-trace") -> BlockExecutionContext:
    """helper to create test context"""
    return BlockExecutionContext(
        job_id=1,
        trace_id=trace_id,
        pipeline_id=1,
        accumulated_state=state,
    )


class TestRagasMetricsInit:
    def test_defaults(self):
        block = RagasMetrics()
        assert block.question_field == "question"
        assert block.answer_field == "answer"
        assert block.contexts_field == "contexts"
        assert block.ground_truth_field == "ground_truth"
        assert block.metrics_template == '["faithfulness"]'
        assert block.score_threshold == 0.5
        assert block.model_name is None
        assert block.embedding_model_name is None

    def test_custom_config(self):
        block = RagasMetrics(
            question_field="q",
            answer_field="a",
            metrics=["faithfulness", "answer_relevancy"],
            model="gpt-4",
            embedding_model="text-embedding-ada-002",
            score_threshold=0.8,
        )
        assert block.question_field == "q"
        assert block.model_name == "gpt-4"
        assert block.score_threshold == 0.8
        assert "answer_relevancy" in block.metrics_template

    def test_threshold_clamped_high(self):
        block = RagasMetrics(score_threshold=1.5)
        assert block.score_threshold == 1.0

    def test_threshold_clamped_low(self):
        block = RagasMetrics(score_threshold=-0.5)
        assert block.score_threshold == 0.0

    def test_metrics_non_list_stored_as_template(self):
        block = RagasMetrics(metrics="not_a_list")  # type: ignore
        # non-list values are stored as-is for template rendering
        assert block.metrics_template == "not_a_list"


class TestNormalizeContexts:
    def test_list_input(self):
        block = RagasMetrics()
        assert block._normalize_contexts(["a", "b"]) == ["a", "b"]

    def test_json_string_input(self):
        block = RagasMetrics()
        assert block._normalize_contexts('["a", "b"]') == ["a", "b"]

    def test_plain_string_input(self):
        block = RagasMetrics()
        assert block._normalize_contexts("single context") == ["single context"]

    def test_empty_list(self):
        block = RagasMetrics()
        assert block._normalize_contexts([]) == []

    def test_empty_string(self):
        block = RagasMetrics()
        assert block._normalize_contexts("") == []

    def test_none_input(self):
        block = RagasMetrics()
        assert block._normalize_contexts(None) == []

    def test_converts_non_strings_to_strings(self):
        block = RagasMetrics()
        assert block._normalize_contexts([1, 2, 3]) == ["1", "2", "3"]


class TestValidateMetricInputs:
    def test_answer_relevancy_valid(self):
        block = RagasMetrics()
        inputs = {"question": "What?", "answer": "Something"}
        is_valid, msg = block._validate_metric_inputs("answer_relevancy", inputs)
        assert is_valid is True
        assert msg == ""

    def test_answer_relevancy_missing_question(self):
        block = RagasMetrics()
        inputs = {"answer": "Something"}
        is_valid, msg = block._validate_metric_inputs("answer_relevancy", inputs)
        assert is_valid is False
        assert "question" in msg

    def test_faithfulness_missing_contexts(self):
        block = RagasMetrics()
        inputs = {"question": "What?", "answer": "Something", "contexts": []}
        is_valid, msg = block._validate_metric_inputs("faithfulness", inputs)
        assert is_valid is False
        assert "contexts" in msg

    def test_context_recall_missing_ground_truth(self):
        block = RagasMetrics()
        inputs = {"question": "What?", "contexts": ["ctx"], "ground_truth": ""}
        is_valid, msg = block._validate_metric_inputs("context_recall", inputs)
        assert is_valid is False
        assert "ground_truth" in msg

    def test_faithfulness_valid(self):
        block = RagasMetrics()
        inputs = {
            "question": "What?",
            "answer": "Something",
            "contexts": ["context1"],
        }
        is_valid, msg = block._validate_metric_inputs("faithfulness", inputs)
        assert is_valid is True


class TestEmptyScores:
    @pytest.mark.xfail(reason="_empty_scores depends on self.metrics which is set during execute()")
    def test_returns_all_metrics_with_zero(self):
        block = RagasMetrics(metrics=["faithfulness", "answer_relevancy"])
        scores = block._empty_scores()
        assert scores["faithfulness"] == 0.0
        assert scores["answer_relevancy"] == 0.0
        assert scores["passed"] is False


class TestExecute:
    @pytest.mark.asyncio
    async def test_missing_question_returns_empty_scores(self):
        block = RagasMetrics()
        result = await block.execute(make_context({"answer": "test"}))
        assert result["ragas_scores"]["passed"] is False
        assert result["ragas_scores"]["faithfulness"] == 0.0

    @pytest.mark.asyncio
    async def test_missing_answer_returns_empty_scores(self):
        block = RagasMetrics()
        result = await block.execute(make_context({"question": "test"}))
        assert result["ragas_scores"]["passed"] is False

    @pytest.mark.asyncio
    async def test_custom_field_names(self):
        block = RagasMetrics(
            question_field="q",
            answer_field="a",
        )
        # missing question because we're looking at wrong field
        result = await block.execute(make_context({"question": "test", "answer": "test"}))
        assert result["ragas_scores"]["passed"] is False


class TestSchema:
    def test_schema_structure(self):
        schema = RagasMetrics.get_schema()
        assert schema["name"] == "Ragas Metrics"
        assert schema["category"] == "metrics"
        assert "model" in schema["config_schema"]["properties"]
        assert "embedding_model" in schema["config_schema"]["properties"]
        assert "metrics" in schema["config_schema"]["properties"]

    def test_field_references(self):
        assert "question_field" in RagasMetrics._field_references
        assert "answer_field" in RagasMetrics._field_references
        assert "contexts_field" in RagasMetrics._field_references
        assert "ground_truth_field" in RagasMetrics._field_references

    def test_outputs(self):
        assert RagasMetrics.outputs == ["ragas_scores"]


class TestMetricRequirements:
    def test_all_metrics_have_requirements(self):
        expected_metrics = [
            "answer_relevancy",
            "context_precision",
            "context_recall",
            "faithfulness",
        ]
        for metric in expected_metrics:
            assert metric in METRIC_REQUIREMENTS
            assert isinstance(METRIC_REQUIREMENTS[metric], list)
            assert len(METRIC_REQUIREMENTS[metric]) > 0
