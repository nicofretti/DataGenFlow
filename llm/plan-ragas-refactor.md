# Plan: RagasMetrics Block Refactoring

## Overview

Refactor `RagasBatchMetrics` into a simpler, pipeline-compatible `RagasMetrics` block and create a new `FieldMapper` utility block for data transformation (replacing `JSONFieldExtractorBlock`).

---

## Problems with Current Implementation

| Issue | Current | Expected |
|-------|---------|----------|
| LLM integration | LangChain (`ChatLiteLLM`, `OllamaEmbeddings`) | Ragas 0.4.x native LiteLLM adapter |
| Input fields | Hardcoded `parsed_json.qa_pairs` structure | Configurable field references |
| Outputs | Wildcard `["*"]` | Specific `["ragas_scores"]` |
| Embeddings | Hardcoded provider logic (50+ lines) | `LiteLLMEmbeddings` via `llm_config_manager` |
| Model selection | Implicit from config | Explicit `model` param like TextGenerator |
| Observability | None | Langfuse via global `litellm.success_callback` |
| Field extraction | `JSONFieldExtractorBlock` with path syntax | `FieldMapper` with Jinja2 templates |

---

## Solution Architecture

### New Block: FieldMapper

**Purpose**: Extract/transform nested fields into top-level fields using Jinja2. Replaces `JSONFieldExtractorBlock`.

**File**: `lib/blocks/builtin/field_mapper.py`

```python
import json
import logging
from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext
from lib.template_renderer import render_template

logger = logging.getLogger(__name__)


class FieldMapper(BaseBlock):
    name = "Field Mapper"
    description = "Create new fields by rendering Jinja2 expressions"
    category = "utilities"
    inputs = ["*"]
    outputs = ["*"]  # dynamic - frontend extracts keys from mappings config

    _config_descriptions = {
        "mappings": "Dict mapping new field names to Jinja2 expressions. Example: {\"question\": \"{{ parsed_json.qa.q }}\"}"
    }

    def __init__(self, mappings: dict[str, str] | None = None):
        """
        Args:
            mappings: {"field_name": "{{ jinja2.expression }}"}
        """
        self.mappings = mappings or {}

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        if not self.mappings:
            logger.warning("no mappings configured, returning empty result")
            return {}

        result = {}
        for field_name, template in self.mappings.items():
            try:
                rendered = render_template(template, context.accumulated_state)
                result[field_name] = self._maybe_parse_json(rendered)
            except Exception as e:
                logger.error(f"failed to render template for '{field_name}': {e}")
                result[field_name] = ""

        return result

    def _maybe_parse_json(self, value: str) -> Any:
        """parse JSON if possible, otherwise return string"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
```

**Usage Example**:
```yaml
- type: FieldMapper
  config:
    mappings:
      question: "{{ parsed_json.qa.q }}"
      answer: "{{ parsed_json.qa.a }}"
      contexts: "{{ parsed_json.qa.sources | tojson }}"
```

---

### Rewritten Block: RagasMetrics

**Purpose**: Evaluate a single QA pair using RAGAS metrics.

**File**: `lib/blocks/builtin/ragas_metrics.py` (new file, delete `ragas_batch_metrics.py`)

```python
import json
import logging
from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext

logger = logging.getLogger(__name__)

# metric requirements - which fields each metric needs
METRIC_REQUIREMENTS: dict[str, list[str]] = {
    "answer_relevancy": ["question", "answer"],
    "context_precision": ["question", "contexts", "ground_truth"],
    "context_recall": ["question", "contexts", "ground_truth"],
    "faithfulness": ["question", "answer", "contexts"],
}


class RagasMetrics(BaseBlock):
    name = "Ragas Metrics"
    description = "Evaluate a QA pair using RAGAS metrics"
    category = "metrics"
    inputs = ["*"]
    outputs = ["ragas_scores"]

    _field_references = [
        "question_field",
        "answer_field",
        "contexts_field",
        "ground_truth_field",
    ]

    _config_enums = {
        "metrics": [
            "answer_relevancy",
            "context_precision",
            "context_recall",
            "faithfulness",
        ]
    }

    _config_descriptions = {
        "model": "LLM model for evaluation (leave empty for default)",
        "embedding_model": "Embedding model for answer_relevancy (leave empty for default)",
        "question_field": "Field containing the question",
        "answer_field": "Field containing the answer",
        "contexts_field": "Field containing contexts (list of strings)",
        "ground_truth_field": "Field containing expected answer",
        "metrics": "RAGAS metrics to calculate",
        "score_threshold": "Minimum score (0.0-1.0) to pass",
    }

    def __init__(
        self,
        question_field: str = "question",
        answer_field: str = "answer",
        contexts_field: str = "contexts",
        ground_truth_field: str = "ground_truth",
        metrics: list[str] | None = None,
        score_threshold: float = 0.5,
        model: str | None = None,
        embedding_model: str | None = None,
    ):
        self.question_field = question_field
        self.answer_field = answer_field
        self.contexts_field = contexts_field
        self.ground_truth_field = ground_truth_field
        self.metrics = metrics if isinstance(metrics, list) else ["faithfulness"]
        self.score_threshold = max(0.0, min(1.0, score_threshold))
        self.model_name = model
        self.embedding_model_name = embedding_model
```

---

## Implementation Steps

### Step 1: Create FieldMapper Block

**File**: `lib/blocks/builtin/field_mapper.py`

1. Create new file with FieldMapper class
2. Use `render_template` from `lib/template_renderer.py`
3. Handle JSON parsing for complex types (lists, dicts)
4. Dynamic outputs based on mappings keys

**Tests**: `tests/blocks/test_field_mapper.py`
- Test simple string mapping
- Test nested field access
- Test JSON parsing (lists, dicts)
- Test invalid template handling

---

### Step 2: Create RagasMetrics Block

**File**: `lib/blocks/builtin/ragas_metrics.py`

1. Rename file from `ragas_batch_metrics.py`
2. Implement new simplified interface
3. Use direct field references (no nested paths)
4. Single evaluation per execution (no loops)

---

### Step 3: Create Usage Tracker Utility

**Purpose**: Accumulate LLM token usage per trace_id for blocks that don't have direct access to LLM responses (like ragas).

**File**: `lib/blocks/commons/usage_tracker.py`

```python
"""
usage tracker for accumulating LLM token usage across multiple calls

useful for blocks that call external libraries (like ragas) which make
LLM calls internally without exposing usage information.
"""
import threading
from collections import defaultdict
from typing import Any

from lib.entities import pipeline


class UsageTracker:
    """thread-safe usage accumulator per trace_id

    usage:
        # register callback in app.py
        litellm.success_callback = ["langfuse", UsageTracker.callback]

        # in block execute method, after LLM calls complete
        usage = UsageTracker.get_and_clear(context.trace_id)
        return {"_usage": usage}
    """

    _usage: dict[str, dict[str, int]] = defaultdict(lambda: {
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
    })
    _lock = threading.Lock()

    @classmethod
    def callback(
        cls,
        kwargs: dict[str, Any],
        completion_response: Any,
        start_time: float,
        end_time: float,
    ) -> None:
        """LiteLLM success callback to accumulate usage"""
        trace_id = kwargs.get("metadata", {}).get("trace_id")
        if not trace_id:
            return

        usage = getattr(completion_response, "usage", None)
        if not usage:
            return

        with cls._lock:
            cls._usage[trace_id]["input_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
            cls._usage[trace_id]["output_tokens"] += getattr(usage, "completion_tokens", 0) or 0
            cls._usage[trace_id]["cached_tokens"] += getattr(usage, "cache_read_input_tokens", 0) or 0

    @classmethod
    def get_and_clear(cls, trace_id: str) -> dict[str, int]:
        """get accumulated usage for trace_id and clear it"""
        with cls._lock:
            usage = dict(cls._usage.pop(trace_id, {
                "input_tokens": 0,
                "output_tokens": 0,
                "cached_tokens": 0,
            }))
        return usage

    @classmethod
    def to_pipeline_usage(cls, trace_id: str) -> pipeline.Usage:
        """get accumulated usage as pipeline.Usage object"""
        usage = cls.get_and_clear(trace_id)
        return pipeline.Usage(
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cached_tokens=usage["cached_tokens"],
        )
```

**File**: `lib/blocks/commons/__init__.py`

```python
from lib.blocks.commons.usage_tracker import UsageTracker

__all__ = ["UsageTracker"]
```

**Update app.py** (around line 67):

```python
from lib.blocks.commons import UsageTracker

# configure langfuse integration if credentials are set
if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
    litellm.success_callback = ["langfuse", UsageTracker.callback]
else:
    # still track usage even without langfuse
    litellm.success_callback = [UsageTracker.callback]
```

---

### Step 4: Replace LangChain with Ragas 0.4.x Native LiteLLM

Remove:
```python
from langchain_community.chat_models import ChatLiteLLM
from langchain_community.embeddings import OllamaEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
```

Add:
```python
from litellm import AsyncOpenAI as LiteLLMAsyncClient
from ragas.llms import llm_factory
from ragas.embeddings import LiteLLMEmbeddings
from ragas.metrics.collections import (  # new path for ragas 0.4.x
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)
```

**LLM Creation** (use `adapter="litellm"` for all providers including OpenAI):
```python
async def _create_ragas_llm(self, context: BlockExecutionContext):
    from app import llm_config_manager

    config = await llm_config_manager.get_llm_model(self.model_name)
    params = llm_config_manager.prepare_llm_call(config, temperature=0.0)

    # use LiteLLM's OpenAI-compatible async client
    client = LiteLLMAsyncClient(
        api_key=params.get("api_key", ""),
        base_url=params.get("api_base"),
    )

    return llm_factory(
        model=params["model"],
        client=client,
        adapter="litellm",  # consistent for all providers
        metadata={"trace_id": context.trace_id, "tags": ["datagenflow", "ragas"]},
    )
```

**Embeddings Creation** (use `LiteLLMEmbeddings` directly, not deprecated `embedding_factory`):
```python
async def _create_ragas_embeddings(self):
    from app import llm_config_manager

    config = await llm_config_manager.get_embedding_model(self.embedding_model_name)
    params = llm_config_manager._prepare_embedding_call(config, input_text="")

    return LiteLLMEmbeddings(
        model=params["model"],
        api_key=params.get("api_key"),
        api_base=params.get("api_base"),
    )
```

---

### Step 4: Observability (Already Handled)

**Langfuse tracing**: Already configured globally in `app.py`:
```python
# app.py:65-67
if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
    litellm.success_callback = ["langfuse"]
```

All LiteLLM calls (including those from ragas) are automatically traced.

**Trace grouping**: Metadata passed to `llm_factory` in Step 3 enables trace grouping:
```python
metadata={"trace_id": context.trace_id, "tags": ["datagenflow", "ragas"]}
```

**Note**: Ragas doesn't expose token usage directly, so `_usage` tracking is not available for this block.

---

### Step 5: Implement Execute Method

```python
async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
    from lib.blocks.commons import UsageTracker

    # 1. collect inputs from configured fields
    inputs = {
        "question": context.get_state(self.question_field, ""),
        "answer": context.get_state(self.answer_field, ""),
        "contexts": self._normalize_contexts(context.get_state(self.contexts_field, [])),
        "ground_truth": context.get_state(self.ground_truth_field, ""),
    }

    # 2. basic validation - need at least question and answer
    if not inputs["question"] or not inputs["answer"]:
        logger.warning("missing question or answer")
        return {"ragas_scores": self._empty_scores()}

    # 3. setup ragas LLM
    try:
        llm = await self._create_ragas_llm(context)
    except Exception as e:
        logger.error(f"failed to create LLM: {e}")
        return {"ragas_scores": self._empty_scores()}

    # 4. setup embeddings if needed
    embeddings = None
    if "answer_relevancy" in self.metrics:
        embeddings = await self._create_ragas_embeddings()

    # 5. build metrics
    metrics = self._build_metrics(llm, embeddings)

    # 6. evaluate (with per-metric validation)
    scores = await self._evaluate(inputs, metrics)

    # 7. get accumulated usage from ragas LLM calls
    usage = UsageTracker.to_pipeline_usage(context.trace_id)

    # 8. check threshold (only on non-zero scores)
    valid_scores = [s for s in scores.values() if s > 0]
    passed = len(valid_scores) > 0 and all(s >= self.score_threshold for s in valid_scores)

    return {
        "ragas_scores": {
            **scores,
            "passed": passed,
        },
        "_usage": usage.model_dump(),
    }
```

---

### Step 6: Helper Methods

```python
def _validate_metric_inputs(
    self,
    metric_name: str,
    inputs: dict[str, Any],
) -> tuple[bool, str]:
    """validate inputs for a specific metric

    Returns:
        (is_valid, error_message)
    """
    required = METRIC_REQUIREMENTS.get(metric_name, [])
    missing = []

    for field in required:
        value = inputs.get(field)
        if not value:
            missing.append(field)
        # contexts must be non-empty list
        if field == "contexts" and isinstance(value, list) and len(value) == 0:
            missing.append(field)

    if missing:
        return False, f"{metric_name} requires: {', '.join(missing)}"
    return True, ""

def _normalize_contexts(self, contexts: Any) -> list[str]:
    """convert contexts to list of strings"""
    if isinstance(contexts, str):
        try:
            parsed = json.loads(contexts)
            if isinstance(parsed, list):
                return [str(c) for c in parsed]
        except json.JSONDecodeError:
            pass
        return [contexts] if contexts else []
    if isinstance(contexts, list):
        return [str(c) for c in contexts]
    return []

def _empty_scores(self) -> dict[str, Any]:
    """return empty scores with passed=False"""
    return {metric: 0.0 for metric in self.metrics} | {"passed": False}

def _build_metrics(self, llm, embeddings) -> dict:
    """build metric instances"""
    # use ragas.metrics.collections for ragas 0.4.x (not ragas.metrics which is deprecated)
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    available = {
        "faithfulness": Faithfulness(llm=llm),
        "context_precision": ContextPrecision(llm=llm),
        "context_recall": ContextRecall(llm=llm),
    }

    if embeddings:
        available["answer_relevancy"] = AnswerRelevancy(llm=llm, embeddings=embeddings)

    return {k: v for k, v in available.items() if k in self.metrics}

async def _evaluate(
    self,
    inputs: dict[str, Any],
    metrics: dict,
) -> dict[str, float]:
    """evaluate with all selected metrics, validating inputs first"""
    from ragas import SingleTurnSample

    scores = {}
    for name, metric in metrics.items():
        # validate inputs for this specific metric
        is_valid, error_msg = self._validate_metric_inputs(name, inputs)
        if not is_valid:
            logger.warning(f"skipping {name}: {error_msg}")
            scores[name] = 0.0
            continue

        try:
            sample = SingleTurnSample(
                user_input=inputs["question"],
                response=inputs["answer"],
                retrieved_contexts=inputs.get("contexts") or None,
                reference=inputs.get("ground_truth") or None,
            )
            score = await metric.single_turn_ascore(sample)
            scores[name] = float(score)
        except Exception as e:
            logger.warning(f"metric {name} failed: {e}")
            scores[name] = 0.0

    return scores
```

---

### Step 7: Update Tests

**File**: `tests/blocks/test_ragas_metrics.py`

```python
import pytest
from lib.blocks.builtin.ragas_metrics import RagasMetrics, METRIC_REQUIREMENTS
from lib.entities.block_execution_context import BlockExecutionContext


def make_context(state: dict) -> BlockExecutionContext:
    """helper to create test context"""
    return BlockExecutionContext(
        trace_id="test-trace",
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
        assert block.metrics == ["faithfulness"]
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

    def test_threshold_clamped(self):
        block = RagasMetrics(score_threshold=1.5)
        assert block.score_threshold == 1.0
        block = RagasMetrics(score_threshold=-0.5)
        assert block.score_threshold == 0.0


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

    def test_empty_input(self):
        block = RagasMetrics()
        assert block._normalize_contexts([]) == []
        assert block._normalize_contexts("") == []
        assert block._normalize_contexts(None) == []


class TestValidateMetricInputs:
    def test_answer_relevancy_valid(self):
        block = RagasMetrics()
        inputs = {"question": "What?", "answer": "Something"}
        is_valid, msg = block._validate_metric_inputs("answer_relevancy", inputs)
        assert is_valid is True

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
```

**File**: `tests/blocks/test_field_mapper.py`

```python
import pytest
from lib.blocks.builtin.field_mapper import FieldMapper
from lib.entities.block_execution_context import BlockExecutionContext


def make_context(state: dict) -> BlockExecutionContext:
    """helper to create test context"""
    return BlockExecutionContext(
        trace_id="test-trace",
        pipeline_id=1,
        accumulated_state=state,
    )


class TestFieldMapper:
    def test_init_with_mappings(self):
        block = FieldMapper(mappings={"a": "{{ b }}"})
        assert block.mappings == {"a": "{{ b }}"}

    def test_init_empty(self):
        block = FieldMapper()
        assert block.mappings == {}

    @pytest.mark.asyncio
    async def test_simple_mapping(self):
        block = FieldMapper(mappings={"x": "{{ y }}"})
        result = await block.execute(make_context({"y": "hello"}))
        assert result["x"] == "hello"

    @pytest.mark.asyncio
    async def test_nested_mapping(self):
        block = FieldMapper(mappings={"flat": "{{ nested.deep.value }}"})
        result = await block.execute(make_context({"nested": {"deep": {"value": "found"}}}))
        assert result["flat"] == "found"

    @pytest.mark.asyncio
    async def test_json_parsing(self):
        block = FieldMapper(mappings={"items": "{{ data | tojson }}"})
        result = await block.execute(make_context({"data": ["a", "b", "c"]}))
        assert result["items"] == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_template_error_returns_empty_string(self):
        block = FieldMapper(mappings={"bad": "{{ undefined_var }}"})
        result = await block.execute(make_context({}))
        assert result["bad"] == ""

    @pytest.mark.asyncio
    async def test_empty_mappings_returns_empty(self):
        block = FieldMapper(mappings={})
        result = await block.execute(make_context({"some": "data"}))
        assert result == {}

    def test_schema(self):
        schema = FieldMapper.get_schema()
        assert schema["name"] == "Field Mapper"
        assert schema["category"] == "utilities"
        assert schema["outputs"] == ["*"]  # dynamic outputs handled by frontend
```

**File**: `tests/blocks/test_usage_tracker.py`

```python
import pytest
from unittest.mock import MagicMock

from lib.blocks.commons.usage_tracker import UsageTracker


class TestUsageTracker:
    def setup_method(self):
        """clear tracker state before each test"""
        UsageTracker._usage.clear()

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

    def test_get_and_clear_removes_entry(self):
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.cache_read_input_tokens = 0

        kwargs = {"metadata": {"trace_id": "test-trace-2"}}
        UsageTracker.callback(kwargs, response, 0.0, 1.0)

        # first call returns usage
        usage1 = UsageTracker.get_and_clear("test-trace-2")
        assert usage1["input_tokens"] == 100

        # second call returns zeros (entry cleared)
        usage2 = UsageTracker.get_and_clear("test-trace-2")
        assert usage2["input_tokens"] == 0

    def test_to_pipeline_usage(self):
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.cache_read_input_tokens = 25

        kwargs = {"metadata": {"trace_id": "test-trace-3"}}
        UsageTracker.callback(kwargs, response, 0.0, 1.0)

        usage = UsageTracker.to_pipeline_usage("test-trace-3")

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
```

---

### Step 8: Cleanup

1. Delete `lib/blocks/builtin/ragas_batch_metrics.py`
2. Delete `lib/blocks/builtin/json_field_extractor.py` (replaced by FieldMapper)
3. Delete `tests/blocks/test_ragas_batch_metrics.py` (if exists)
4. `CleanJSONLLM` wrapper class removed (not needed with ragas 0.4.x)

---

### Step 9: Frontend - Dynamic Outputs for FieldMapper

**Problem**: Block outputs are defined at class level, but FieldMapper outputs depend on user config (mappings keys). The UI field dropdowns won't show FieldMapper outputs.

**Solution**: Modify `getAvailableFields` in PipelineEditor to extract keys from FieldMapper's mappings config.

**File**: `frontend/src/components/pipeline-editor/PipelineEditor.tsx`

**Change** (around line 431-440):

```typescript
// collect all outputs from predecessor nodes
const availableFields = new Set<string>();

nodes.forEach((node) => {
  if (predecessors.has(node.id)) {
    const outputs = node.data.block.outputs || [];
    outputs.forEach((output: string) => {
      if (output !== "*") {
        availableFields.add(output);
      }
    });

    // NEW: For FieldMapper, extract keys from mappings config
    if (node.data.block.type === "FieldMapper" && node.data.config?.mappings) {
      Object.keys(node.data.config.mappings).forEach((key) => {
        availableFields.add(key);
      });
    }
  }
});
```

**Result**: When user configures FieldMapper with:
```yaml
mappings:
  question: "{{ parsed_json.qa.q }}"
  answer: "{{ parsed_json.qa.a }}"
```

Downstream blocks (like RagasMetrics) will show `question` and `answer` in their field dropdowns.

---

## File Changes Summary

| Action | File |
|--------|------|
| CREATE | `lib/blocks/commons/__init__.py` |
| CREATE | `lib/blocks/commons/usage_tracker.py` |
| CREATE | `lib/blocks/builtin/field_mapper.py` |
| CREATE | `lib/blocks/builtin/ragas_metrics.py` |
| CREATE | `lib/templates/ragas_evaluation.yaml` |
| CREATE | `lib/templates/seeds/seed_ragas_evaluation.json` |
| CREATE | `tests/blocks/test_usage_tracker.py` |
| CREATE | `tests/blocks/test_field_mapper.py` |
| CREATE | `tests/blocks/test_ragas_metrics.py` |
| MODIFY | `app.py` (register UsageTracker callback) |
| MODIFY | `frontend/src/components/pipeline-editor/PipelineEditor.tsx` |
| MODIFY | `llm/state-backend.md` (update block list and lifespan section) |
| DELETE | `lib/blocks/builtin/ragas_batch_metrics.py` |
| DELETE | `lib/blocks/builtin/json_field_extractor.py` |
| DELETE | `examples/ragas/ragas-qa-evaluation-pipeline.json` |
| DELETE | `examples/ragas/README.md` |

---

### Step 10: Create RAGAS Template

**File**: `lib/templates/ragas_evaluation.yaml`

```yaml
name: QA Generation with RAGAS Evaluation
description: Generate QA pairs from content and evaluate quality using RAGAS metrics
blocks:
  - type: StructuredGenerator
    config:
      system_prompt: "You are an expert at creating high-quality question-answer pairs from given content."
      user_prompt: |
        Based on the following content, generate a question-answer pair.
        The question should be answerable from the content.
        The answer should be accurate and complete.

        Content:
        {{ content }}
      json_schema:
        type: object
        properties:
          question:
            type: string
            description: A clear question based on the content
          answer:
            type: string
            description: A complete answer to the question
          ground_truth:
            type: string
            description: The expected reference answer
          contexts:
            type: array
            items:
              type: string
            description: Relevant passages from the content
        required:
          - question
          - answer

  - type: FieldMapper
    config:
      mappings:
        question: "{{ generated.question }}"
        answer: "{{ generated.answer }}"
        ground_truth: "{{ generated.ground_truth | default('') }}"
        contexts: "{{ generated.contexts | default([]) | tojson }}"

  - type: RagasMetrics
    config:
      question_field: question
      answer_field: answer
      contexts_field: contexts
      ground_truth_field: ground_truth
      metrics:
        - faithfulness
        - answer_relevancy
      score_threshold: 0.7
```

**Note**: No JSONValidatorBlock needed - StructuredGenerator already validates and parses JSON.

**File**: `lib/templates/seeds/seed_ragas_evaluation.json`

```json
[
  {
    "content": "Python is a high-level, interpreted programming language known for its clear syntax and readability. It was created by Guido van Rossum and first released in 1991. Python supports multiple programming paradigms including procedural, object-oriented, and functional programming."
  },
  {
    "content": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing algorithms that can access data and use it to learn for themselves."
  }
]
```

---

### Step 11: Remove Old RAGAS Examples

**Delete**: `examples/ragas/` directory (contains old `RagasBatchMetrics` example)

- `examples/ragas/ragas-qa-evaluation-pipeline.json`
- `examples/ragas/README.md`

---

### Step 12: Update Documentation

**File**: `llm/state-backend.md`

Update to reflect new blocks and removed blocks:

**Structure section** (line ~14):
- Change `builtin/` comment from "9 blocks" to "9 blocks" (count stays same: -2 removed, +2 added)
- Update block list: remove `json_field_extractor`, add `field_mapper`, `ragas_metrics`
- Add new `commons/` entry for usage tracker

**Builtin blocks section** (line ~414):
Remove:
- JSONFieldExtractorBlock entry (line ~423-424, replaced by FieldMapper)

Add:
```
- **FieldMapper**: create fields from Jinja2 expressions (mappings)
  - outputs: dynamic (keys from mappings config)
- **RagasMetrics**: evaluate QA using RAGAS metrics (question_field, answer_field, etc.)
  - outputs: ragas_scores
```

**Lifespan section** (line ~496):
Update callback setup to include UsageTracker:
```python
if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
    litellm.success_callback = ["langfuse", UsageTracker.callback]
else:
    litellm.success_callback = [UsageTracker.callback]
```

---

## Dependencies

**Keep** (already in `pyproject.toml`):
- `ragas>=0.4.0` (currently 0.4.2)
- `litellm` (provides `AsyncOpenAI` client)

**Remove** from `pyproject.toml`:
- `langchain-community` - no longer needed
- `langchain-openai` - no longer needed
- `langchain-google-genai` - no longer needed

**Note**: `openai` package is a transitive dependency of `litellm`, no need to add explicitly.

---

## Acceptance Criteria

- [ ] UsageTracker utility in `lib/blocks/commons/` for reusable usage accumulation
- [ ] UsageTracker callback registered in `app.py`
- [ ] FieldMapper block works with Jinja2 expressions (replaces JSONFieldExtractorBlock)
- [ ] FieldMapper outputs appear in downstream block field dropdowns (frontend change)
- [ ] RagasMetrics uses direct field references (no nested paths)
- [ ] RagasMetrics validates inputs per-metric with clear error messages
- [ ] RagasMetrics returns `_usage` with accumulated token counts
- [ ] Model selection works same as TextGenerator
- [ ] Embedding model selection uses `llm_config_manager.get_embedding_model()`
- [ ] Uses `ragas.metrics.collections` imports (ragas 0.4.x)
- [ ] Uses `LiteLLMEmbeddings` (not deprecated `embedding_factory`)
- [ ] Uses `adapter="litellm"` consistently for all providers
- [ ] LangChain dependencies removed from `pyproject.toml`
- [ ] All tests pass
- [ ] Pipeline example works end-to-end
- [ ] `llm/state-backend.md` updated with new blocks and removed blocks
