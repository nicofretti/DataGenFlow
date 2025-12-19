import json
import logging
import re
from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext

logger = logging.getLogger(__name__)


class CleanJSONLLM:
    """wrapper around langchain LLM that strips markdown code fences from JSON responses"""

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    def _strip_markdown_fences(self, text: str) -> str:
        """remove markdown code fences from JSON responses"""
        # remove ```json and ``` wrappers
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
        return text.strip()

    async def agenerate_prompt(self, prompts: Any, **kwargs: Any) -> Any:
        """async generate with markdown fence stripping"""
        response = await self.llm.agenerate_prompt(prompts, **kwargs)
        # strip markdown fences from all generations
        for generations in response.generations:
            for gen in generations:
                if hasattr(gen, "text"):
                    gen.text = self._strip_markdown_fences(gen.text)
        return response

    def __getattr__(self, name: str) -> Any:
        """delegate all other methods to underlying LLM"""
        return getattr(self.llm, name)


class RagasBatchMetrics(BaseBlock):
    name = "Ragas Batch Metrics"
    description = "Evaluate all QA pairs from parsed JSON using RAGAS metrics"
    category = "metrics"
    inputs = ["parsed_json"]
    outputs = ["*"]  # dynamic outputs based on number of QA pairs and selected metrics

    _config_enums = {
        "metrics": [
            "answer_relevancy",
            "context_precision",
            "context_recall",
            "faithfulness",
        ]
    }

    _config_descriptions = {
        "metrics": "Select one or more ragas metrics to calculate for each QA pair",
        "score_threshold": (
            "Minimum score threshold (0.0-1.0). "
            "QA pairs with any score below this will be flagged as low quality"
        ),
        "flag_low_scores": "Enable flagging of QA pairs with scores below threshold",
    }

    def __init__(
        self,
        metrics: list[str] | None = None,
        score_threshold: float = 0.5,
        flag_low_scores: bool = False,
    ):
        """
        Args:
            metrics: List of ragas metrics to calculate for each QA pair
            score_threshold: Minimum acceptable score (0.0-1.0)
            flag_low_scores: Whether to flag low-scoring QA pairs
        """
        # set metrics list
        if isinstance(metrics, list):
            self.metrics = metrics
        else:
            self.metrics = ["faithfulness"]

        # set threshold and flagging
        self.score_threshold = max(0.0, min(1.0, score_threshold))
        self.flag_low_scores = flag_low_scores

    def _normalize_contexts(self, contexts: Any) -> list[str]:
        """convert contexts to list of strings"""
        if isinstance(contexts, str):
            # try to parse as json array first
            try:
                parsed = json.loads(contexts)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                # if json parsing fails, treat input as single context string below
                pass
            # treat as single context
            return [contexts]
        elif isinstance(contexts, list):
            return [str(item) for item in contexts]
        return []

    def _validate_inputs(self, inputs: dict[str, Any], metric_name: str) -> bool:
        """check if required fields are present for the selected metric"""
        # define required fields per metric
        requirements = {
            "answer_relevancy": ["question", "answer"],
            "context_precision": ["question", "contexts", "ground_truth"],
            "context_recall": ["question", "contexts", "ground_truth"],
            "faithfulness": ["question", "answer", "contexts"],
        }

        required = requirements.get(metric_name, [])

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

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        try:
            from ragas import SingleTurnSample
            from ragas.metrics import (
                AnswerRelevancy,
                ContextPrecision,
                ContextRecall,
                Faithfulness,
            )
        except ImportError as e:
            logger.error(f"ragas not installed: {e}")
            return {}

        # get QA data from context (supports both "parsed_json" and "generated" fields)
        data = context.accumulated_state
        logger.info(f"ragas_batch_metrics: accumulated_state keys: {list(data.keys())}")

        # try "parsed_json" first, then "generated" for flexibility
        qa_data = data.get("parsed_json") or data.get("generated")
        if not qa_data or not isinstance(qa_data, dict):
            logger.error(
                f"No valid QA data found. Expected 'parsed_json' or 'generated' field. "
                f"Available fields: {list(data.keys())}"
            )
            return {}

        qa_pairs = qa_data.get("qa_pairs", [])
        if not isinstance(qa_pairs, list) or len(qa_pairs) == 0:
            logger.error(
                f"qa_pairs not found or empty. Type: {type(qa_pairs)}, "
                f"Length: {len(qa_pairs) if isinstance(qa_pairs, list) else 'N/A'}"
            )
            return {}

        # configure LLM and embeddings for ragas
        try:
            from langchain_community.chat_models import ChatLiteLLM

            from app import llm_config_manager

            llm_config = await llm_config_manager.get_llm_model(None)
            logger.info(f"ragas using provider: {llm_config.provider.value}")

            # prepare litellm params using existing config manager
            llm_params = llm_config_manager.prepare_llm_call(
                llm_config,
                temperature=0.0,
            )

            # create langchain-compatible litellm LLM (works for all providers)
            base_llm = ChatLiteLLM(
                model=llm_params["model"],
                api_key=llm_params.get("api_key"),
                api_base=llm_params.get("api_base"),
                temperature=0.0,
            )

            # wrap with markdown fence stripper for JSON responses
            llm = CleanJSONLLM(base_llm)

            # configure embeddings based on provider
            embeddings: Any
            if llm_config.provider.value == "ollama":
                from langchain_community.embeddings import OllamaEmbeddings

                base_url = (
                    llm_config.endpoint.replace("/v1/chat/completions", "")
                    if llm_config.endpoint
                    else "http://localhost:11434"
                )
                embeddings = OllamaEmbeddings(
                    model="nomic-embed-text",
                    base_url=base_url,
                )
            elif llm_config.provider.value == "gemini":
                from langchain_google_genai import (
                    GoogleGenerativeAIEmbeddings,
                )

                embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=llm_config.api_key,
                )
            elif llm_config.provider.value == "openai":
                from langchain_openai import OpenAIEmbeddings

                embeddings = OpenAIEmbeddings(  # type: ignore[call-arg]
                    api_key=llm_config.api_key,
                    base_url=llm_config.endpoint,
                )
            else:
                # for anthropic and others, use openai embeddings if available
                # or fall back to a simple default
                try:
                    import os

                    from langchain_openai import OpenAIEmbeddings

                    # try to use openai embeddings if OPENAI_API_KEY is set
                    if os.getenv("OPENAI_API_KEY"):
                        embeddings = OpenAIEmbeddings()
                    else:
                        # use text-embedding-ada-002 endpoint with anthropic key
                        logger.warning(
                            f"provider {llm_config.provider.value} doesn't provide embeddings, "
                            "some metrics (answer_relevancy) may not work. "
                            "consider configuring an embedding model in settings."
                        )
                        embeddings = None
                except Exception:
                    embeddings = None

        except Exception as e:
            logger.error(f"failed to configure LLM for ragas: {e}")
            return {}

        # map of available metrics
        metric_map = {
            "context_precision": ContextPrecision(llm=llm),
            "context_recall": ContextRecall(llm=llm),
            "faithfulness": Faithfulness(llm=llm),
        }

        # add answer_relevancy only if embeddings are available
        if embeddings:
            metric_map["answer_relevancy"] = AnswerRelevancy(
                llm=llm,
                embeddings=embeddings,
            )

        # process each QA pair and build enhanced structure
        qa_pairs_with_scores = []

        for qa_index, qa_pair in enumerate(qa_pairs):
            if not isinstance(qa_pair, dict):
                continue

            # copy original QA pair data
            enhanced_qa = {
                "question": qa_pair.get("question", ""),
                "answer": qa_pair.get("answer", ""),
                "ground_truth": qa_pair.get("ground_truth", ""),
                "contexts": self._normalize_contexts(qa_pair.get("contexts", [])),
                "scores": {},
            }

            # extract fields from QA pair
            inputs = {
                "question": qa_pair.get("question", ""),
                "answer": qa_pair.get("answer", ""),
                "ground_truth": qa_pair.get("ground_truth", ""),
                "contexts": self._normalize_contexts(qa_pair.get("contexts", [])),
            }

            # calculate all selected metrics for this QA pair
            for metric_name in self.metrics:
                metric = metric_map.get(metric_name)

                if not metric:
                    # provide helpful error message based on why metric is unavailable
                    if metric_name == "answer_relevancy":
                        logger.error(
                            f"metric '{metric_name}' requires embeddings which are unavailable. "
                            f"provider {llm_config.provider.value} may not support embeddings, "
                            "or OPENAI_API_KEY is not set for fallback embeddings"
                        )
                    else:
                        logger.error(f"unknown metric type: {metric_name}")
                    enhanced_qa["scores"][f"{metric_name}_score"] = 0.0
                    continue

                # validate required fields for this metric
                if not self._validate_inputs(inputs, metric_name):
                    logger.warning(
                        f"missing required fields for {metric_name} in qa_pair {qa_index}"
                    )
                    enhanced_qa["scores"][f"{metric_name}_score"] = 0.0
                    continue

                try:
                    # create sample with only required fields for this metric
                    sample_kwargs = {}

                    if inputs.get("question"):
                        sample_kwargs["user_input"] = inputs["question"]
                    if inputs.get("answer"):
                        sample_kwargs["response"] = inputs["answer"]
                    if inputs.get("contexts"):
                        sample_kwargs["retrieved_contexts"] = inputs["contexts"]
                    if inputs.get("ground_truth"):
                        sample_kwargs["reference"] = inputs["ground_truth"]

                    sample = SingleTurnSample(**sample_kwargs)

                    # calculate metric
                    score = await metric.single_turn_ascore(sample)
                    enhanced_qa["scores"][f"{metric_name}_score"] = float(score)

                except Exception as e:
                    logger.error(
                        f"ragas metric calculation failed for {metric_name} "
                        f"in qa_pair {qa_index}: {e}"
                    )
                    enhanced_qa["scores"][f"{metric_name}_score"] = 0.0

            # flag low-scoring QA pairs if enabled
            if self.flag_low_scores:
                low_quality = any(
                    score < self.score_threshold for score in enhanced_qa["scores"].values()
                )
                enhanced_qa["low_quality"] = low_quality

                # also track which specific scores are below threshold
                enhanced_qa["below_threshold"] = {
                    metric: score < self.score_threshold
                    for metric, score in enhanced_qa["scores"].items()
                }

            qa_pairs_with_scores.append(enhanced_qa)

        # optionally filter out low-quality pairs
        if self.flag_low_scores:
            total_pairs = len(qa_pairs_with_scores)
            low_quality_count = sum(
                1 for qa in qa_pairs_with_scores if qa.get("low_quality", False)
            )
            logger.info(
                f"ragas evaluation: {low_quality_count}/{total_pairs} "
                f"QA pairs flagged as low quality (threshold: {self.score_threshold})"
            )

        result = {"qa_pairs_with_scores": qa_pairs_with_scores}
        logger.info(
            f"ragas_batch_metrics: returning {len(qa_pairs_with_scores)} QA pairs with scores"
        )
        return result
