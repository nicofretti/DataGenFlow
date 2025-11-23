import json
import logging
from typing import Any

from lib.blocks.base import BaseBlock

logger = logging.getLogger(__name__)


class RagasMetrics(BaseBlock):
    name = "Ragas Metrics"
    description = (
        "Evaluate RAG systems using ragas metrics: Context Precision, Context Recall, "
        "Context Entities Recall, Noise Sensitivity, Response Relevancy, Faithfulness"
    )
    category = "metrics"
    inputs = []
    outputs = ["ragas_score"]

    _config_enums = {
        "metric_type": [
            "context_precision",
            "context_recall",
            "context_entities_recall",
            "noise_sensitivity",
            "answer_relevancy",
            "faithfulness",
        ]
    }

    _field_references = [
        "question_field",
        "answer_field",
        "contexts_field",
        "ground_truth_field",
    ]

    _config_descriptions = {
        "metric_type": "Type of ragas metric to calculate",
        "question_field": "Field containing the question text",
        "answer_field": "Field containing the generated answer",
        "contexts_field": "Field containing retrieved contexts (list or string)",
        "ground_truth_field": "Field containing the reference/ground truth answer",
    }

    def __init__(
        self,
        metric_type: str = "faithfulness",
        question_field: str = "question",
        answer_field: str = "answer",
        contexts_field: str = "contexts",
        ground_truth_field: str = "ground_truth",
    ):
        """
        Args:
            metric_type: Type of ragas metric to calculate
            question_field: Name of field containing the question
            answer_field: Name of field containing the generated answer
            contexts_field: Name of field containing retrieved contexts
            ground_truth_field: Name of field containing ground truth answer
        """
        self.metric_type = metric_type
        self.question_field = question_field
        self.answer_field = answer_field
        self.contexts_field = contexts_field
        self.ground_truth_field = ground_truth_field

    def _normalize_contexts(self, contexts: Any) -> list[str]:
        """convert contexts to list of strings"""
        if isinstance(contexts, str):
            # try to parse as json array first
            try:
                parsed = json.loads(contexts)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
            # treat as single context
            return [contexts]
        elif isinstance(contexts, list):
            return [str(item) for item in contexts]
        return []

    def _get_metric_inputs(self, data: dict[str, Any]) -> dict[str, Any]:
        """extract and validate required inputs for the metric"""
        inputs = {}

        # get raw values from data
        question = data.get(self.question_field, "")
        answer = data.get(self.answer_field, "")
        contexts_raw = data.get(self.contexts_field, [])
        ground_truth = data.get(self.ground_truth_field, "")

        # normalize contexts
        contexts = self._normalize_contexts(contexts_raw)

        # map to ragas expected field names
        inputs["question"] = question
        inputs["answer"] = answer
        inputs["contexts"] = contexts
        inputs["ground_truth"] = ground_truth

        return inputs

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            from ragas import SingleTurnSample
            from ragas.metrics import (
                AnswerRelevancy,
                ContextEntityRecall,
                ContextPrecision,
                ContextRecall,
                Faithfulness,
                NoiseSensitivity,
            )
        except ImportError as e:
            logger.error(f"ragas not installed: {e}")
            return {"ragas_score": 0.0}

        # get inputs
        inputs = self._get_metric_inputs(data)

        # select metric
        metric_map = {
            "context_precision": ContextPrecision(),
            "context_recall": ContextRecall(),
            "context_entities_recall": ContextEntityRecall(),
            "noise_sensitivity": NoiseSensitivity(),
            "answer_relevancy": AnswerRelevancy(),
            "faithfulness": Faithfulness(),
        }

        metric = metric_map.get(self.metric_type)
        if not metric:
            logger.error(f"unknown metric type: {self.metric_type}")
            return {"ragas_score": 0.0}

        # validate required fields for metric
        if not self._validate_inputs(inputs):
            logger.warning(f"missing required fields for {self.metric_type}")
            return {"ragas_score": 0.0}

        try:
            # create sample
            sample = SingleTurnSample(
                user_input=inputs["question"],
                response=inputs["answer"],
                retrieved_contexts=inputs["contexts"],
                reference=inputs["ground_truth"],
            )

            # calculate metric
            score = await metric.single_turn_ascore(sample)

            return {"ragas_score": float(score)}

        except Exception as e:
            logger.error(f"ragas metric calculation failed: {e}")
            return {"ragas_score": 0.0}

    def _validate_inputs(self, inputs: dict[str, Any]) -> bool:
        """check if required fields are present for the selected metric"""
        # define required fields per metric
        requirements = {
            "context_precision": ["question", "contexts", "ground_truth"],
            "context_recall": ["question", "contexts", "ground_truth"],
            "context_entities_recall": ["question", "contexts", "ground_truth"],
            "noise_sensitivity": ["question", "contexts", "answer"],
            "answer_relevancy": ["question", "answer"],
            "faithfulness": ["answer", "contexts"],
        }

        required = requirements.get(self.metric_type, [])

        for field in required:
            value = inputs.get(field)
            if not value:
                return False
            # contexts must be non-empty list
            if field == "contexts" and not isinstance(value, list):
                return False
            if field == "contexts" and len(value) == 0:
                return False

        return True
