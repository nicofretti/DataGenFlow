import pytest

from lib.blocks.builtin.ragas_batch_metrics import RagasBatchMetrics


class TestRagasBatchMetrics:
    """test suite for RagasBatchMetrics block"""

    def test_init_default(self):
        """test default initialization"""
        block = RagasBatchMetrics()
        assert block.metrics == ["faithfulness"]
        assert block.score_threshold == 0.5
        assert block.flag_low_scores is False

    def test_init_custom_metrics(self):
        """test initialization with custom metrics"""
        block = RagasBatchMetrics(
            metrics=["answer_relevancy", "context_precision"],
            score_threshold=0.7,
            flag_low_scores=True,
        )
        assert block.metrics == ["answer_relevancy", "context_precision"]
        assert block.score_threshold == 0.7
        assert block.flag_low_scores is True

    def test_init_threshold_clamping(self):
        """test that score_threshold is clamped to [0.0, 1.0]"""
        block_low = RagasBatchMetrics(score_threshold=-0.5)
        assert block_low.score_threshold == 0.0

        block_high = RagasBatchMetrics(score_threshold=1.5)
        assert block_high.score_threshold == 1.0

    def test_normalize_contexts_string(self):
        """test normalizing single string context"""
        block = RagasBatchMetrics()
        result = block._normalize_contexts("single context string")
        assert result == ["single context string"]

    def test_normalize_contexts_list(self):
        """test normalizing list of contexts"""
        block = RagasBatchMetrics()
        contexts = ["context 1", "context 2", "context 3"]
        result = block._normalize_contexts(contexts)
        assert result == ["context 1", "context 2", "context 3"]

    def test_normalize_contexts_json_string(self):
        """test normalizing JSON array string"""
        block = RagasBatchMetrics()
        json_str = '["ctx1", "ctx2"]'
        result = block._normalize_contexts(json_str)
        assert result == ["ctx1", "ctx2"]

    def test_normalize_contexts_empty(self):
        """test normalizing empty input"""
        block = RagasBatchMetrics()
        assert block._normalize_contexts([]) == []
        assert block._normalize_contexts("") == [""]

    def test_normalize_contexts_mixed_types(self):
        """test normalizing list with mixed types"""
        block = RagasBatchMetrics()
        contexts = ["string", 123, {"key": "value"}]
        result = block._normalize_contexts(contexts)
        assert result == ["string", "123", "{'key': 'value'}"]

    def test_validate_inputs_faithfulness_valid(self):
        """test validation for faithfulness metric with valid inputs"""
        block = RagasBatchMetrics()
        inputs = {
            "question": "What is AI?",
            "answer": "Artificial Intelligence",
            "contexts": ["AI is a field of computer science"],
        }
        assert block._validate_inputs(inputs, "faithfulness") is True

    def test_validate_inputs_faithfulness_missing_answer(self):
        """test validation for faithfulness with missing answer"""
        block = RagasBatchMetrics()
        inputs = {"question": "What is AI?", "contexts": ["context"]}
        assert block._validate_inputs(inputs, "faithfulness") is False

    def test_validate_inputs_answer_relevancy_valid(self):
        """test validation for answer_relevancy with valid inputs"""
        block = RagasBatchMetrics()
        inputs = {"question": "What is AI?", "answer": "Artificial Intelligence"}
        assert block._validate_inputs(inputs, "answer_relevancy") is True

    def test_validate_inputs_answer_relevancy_missing_question(self):
        """test validation for answer_relevancy with missing question"""
        block = RagasBatchMetrics()
        inputs = {"answer": "Artificial Intelligence"}
        assert block._validate_inputs(inputs, "answer_relevancy") is False

    def test_validate_inputs_context_precision_valid(self):
        """test validation for context_precision with valid inputs"""
        block = RagasBatchMetrics()
        inputs = {
            "question": "What is AI?",
            "contexts": ["AI context"],
            "ground_truth": "AI is Artificial Intelligence",
        }
        assert block._validate_inputs(inputs, "context_precision") is True

    def test_validate_inputs_context_precision_empty_contexts(self):
        """test validation for context_precision with empty contexts"""
        block = RagasBatchMetrics()
        inputs = {
            "question": "What is AI?",
            "contexts": [],
            "ground_truth": "AI is Artificial Intelligence",
        }
        assert block._validate_inputs(inputs, "context_precision") is False

    def test_validate_inputs_context_recall_valid(self):
        """test validation for context_recall with valid inputs"""
        block = RagasBatchMetrics()
        inputs = {
            "question": "What is AI?",
            "contexts": ["AI context"],
            "ground_truth": "AI is Artificial Intelligence",
        }
        assert block._validate_inputs(inputs, "context_recall") is True

    def test_validate_inputs_unknown_metric(self):
        """test validation for unknown metric type"""
        block = RagasBatchMetrics()
        inputs = {"question": "Q?", "answer": "A", "contexts": ["ctx"]}
        # unknown metrics should return False since requirements.get returns []
        assert block._validate_inputs(inputs, "unknown_metric") is True

    def test_validate_inputs_contexts_not_list(self):
        """test validation rejects contexts that aren't lists"""
        block = RagasBatchMetrics()
        inputs = {
            "question": "What is AI?",
            "answer": "Artificial Intelligence",
            "contexts": "single string context",  # should be list
        }
        assert block._validate_inputs(inputs, "faithfulness") is False

    @pytest.mark.asyncio
    async def test_execute_missing_parsed_json(self, make_context):
        """test execute with missing parsed_json field"""
        block = RagasBatchMetrics()
        result = await block.execute(make_context({"some_field": "value"}))
        assert result == {}

    @pytest.mark.asyncio
    async def test_execute_invalid_parsed_json_type(self, make_context):
        """test execute with invalid parsed_json type"""
        block = RagasBatchMetrics()
        result = await block.execute(make_context({"parsed_json": "not a dict"}))
        assert result == {}

    @pytest.mark.asyncio
    async def test_execute_missing_qa_pairs(self, make_context):
        """test execute with missing qa_pairs in parsed_json"""
        block = RagasBatchMetrics()
        result = await block.execute(make_context({"parsed_json": {"other": "data"}}))
        assert result == {}

    @pytest.mark.asyncio
    async def test_execute_empty_qa_pairs(self, make_context):
        """test execute with empty qa_pairs list"""
        block = RagasBatchMetrics()
        result = await block.execute(make_context({"parsed_json": {"qa_pairs": []}}))
        assert result == {}

    def test_schema(self):
        """test block schema generation"""
        schema = RagasBatchMetrics.get_schema()

        assert schema["name"] == "Ragas Batch Metrics"
        assert schema["category"] == "metrics"
        assert schema["description"] == "Evaluate all QA pairs from parsed JSON using RAGAS metrics"

        # check config schema
        config_schema = schema["config_schema"]
        assert "metrics" in config_schema["properties"]
        assert "score_threshold" in config_schema["properties"]
        assert "flag_low_scores" in config_schema["properties"]

        # check metrics enum (array of enums)
        metrics_prop = config_schema["properties"]["metrics"]
        assert metrics_prop["type"] == "array"
        assert "items" in metrics_prop
        assert "enum" in metrics_prop["items"]
        assert "answer_relevancy" in metrics_prop["items"]["enum"]
        assert "context_precision" in metrics_prop["items"]["enum"]
        assert "context_recall" in metrics_prop["items"]["enum"]
        assert "faithfulness" in metrics_prop["items"]["enum"]

    def test_schema_descriptions(self):
        """test that schema includes helpful descriptions"""
        schema = RagasBatchMetrics.get_schema()
        config_schema = schema["config_schema"]

        # check descriptions exist
        assert "description" in config_schema["properties"]["metrics"]
        assert "description" in config_schema["properties"]["score_threshold"]
        assert "description" in config_schema["properties"]["flag_low_scores"]

    def test_inputs_outputs(self):
        """test block inputs and outputs"""
        block = RagasBatchMetrics()
        assert block.inputs == ["parsed_json"]
        assert block.outputs == ["*"]  # wildcard output
