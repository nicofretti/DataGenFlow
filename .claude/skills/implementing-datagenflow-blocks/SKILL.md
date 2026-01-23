---
name: implementing-datagenflow-blocks
description: Use when creating new blocks for DataGenFlow pipeline system or modifying existing blocks to ensure consistency with established patterns
---

# Implementing DataGenFlow Blocks

## Overview

DataGenFlow blocks are composable pipeline components. Follow KISS principles: write minimal functions, make code self-explanatory, keep it simple.

## When to Use

- Creating a new block
- Modifying existing block behavior
- Reviewing block implementations
- Debugging block execution issues

**When NOT to use:**
- General backend code (use llm/rules-backend.md)
- Frontend development (use llm/rules-frontend.md)

## Block Structure

```python
import logging
from typing import Any

import litellm  # if using LLM

from lib.blocks.base import BaseBlock
from lib.entities import pipeline
from lib.entities.block_execution_context import BlockExecutionContext
from lib.template_renderer import render_template  # if using templates

logger = logging.getLogger(__name__)


class MyBlock(BaseBlock):
    name = "My Block"
    description = "Short description of what this block does"
    category = "generators"  # generators|transformers|validators|utilities
    inputs = ["field1"]      # or ["*"] for any input fields
    outputs = ["field2"]     # or ["*"] for dynamic outputs

    _config_descriptions = {
        "param_name": "Help text shown in UI",
    }

    def __init__(
        self,
        param1: str,
        model: str | None = None,  # EXACTLY "model" for LLM selection UI
        temperature: float = 0.7,
    ):
        self.param1 = param1
        self.model_name = model  # store as model_name
        self.temperature = temperature

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        from app import llm_config_manager  # import inside execute

        # your logic here

        return {"field": value, "_usage": usage_info}
```

## UI Integration Patterns

The frontend automatically renders different UI controls based on parameter names, types, and class attributes.

### Model Dropdown (LLM)

**Parameter MUST be named exactly `model`** for automatic dropdown:

```python
def __init__(
    self,
    model: str | None = None,  # MUST be "model" and str|None
    temperature: float = 0.7,
    max_tokens: int = 2048,
):
    self.model_name = model  # store as model_name
```

**Config description:**
```python
_config_descriptions = {
    "model": "Select LLM model to use (leave empty for default)",
}
```

**Usage in execute:**
```python
async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
    from app import llm_config_manager

    llm_config = await llm_config_manager.get_llm_model(self.model_name)
    llm_params = llm_config_manager.prepare_llm_call(
        llm_config,
        messages=messages,
        temperature=self.temperature,
        max_tokens=self.max_tokens,
    )
```

### Embedding Model Dropdown

**Parameter MUST be named exactly `embedding_model`**:

```python
def __init__(
    self,
    embedding_model: str | None = None,  # MUST be "embedding_model"
):
    self.embedding_model_name = embedding_model
```

**Config description:**
```python
_config_descriptions = {
    "embedding_model": "Embedding model to use (leave empty for default)",
}
```

**Usage:**
```python
embedding_config = await llm_config_manager.get_embedding_model(
    self.embedding_model_name
)
```

### Enum Dropdown

Use `_config_enums` class attribute to create dropdown with predefined options:

```python
class MyBlock(BaseBlock):
    _config_enums = {
        "mode": ["strict", "lenient", "auto"],
        "format": ["json", "yaml", "xml"],
    }

    def __init__(
        self,
        mode: str = "auto",
        format: str = "json",
    ):
        self.mode = mode
        self.format = format
```

### Multi-Select Checkboxes

For array parameters with enum values:

```python
class MyBlock(BaseBlock):
    _config_enums = {
        "features": ["feature_a", "feature_b", "feature_c"],
    }

    def __init__(
        self,
        features: list[str] | None = None,
    ):
        self.features = features or []
```

### Field Reference Dropdown

Use `_field_references` to create dropdown showing available fields from pipeline:

```python
class MyBlock(BaseBlock):
    _field_references = ["source_field", "target_field"]

    _config_descriptions = {
        "source_field": "Field to read from",
        "target_field": "Field to write to",
    }

    def __init__(
        self,
        source_field: str,
        target_field: str,
    ):
        self.source_field = source_field
        self.target_field = target_field
```

### Template Fields (Monaco Editor)

Parameters with these patterns automatically get Monaco editor:
- Name contains "prompt", "template", or "instruction"
- Or set `schema.format = "jinja2"` via config

```python
def __init__(
    self,
    user_prompt: str = "",      # automatically gets editor
    system_prompt: str = "",    # automatically gets editor
    custom_template: str = "",  # automatically gets editor
):
    self.user_prompt = user_prompt
```

**Config description should mention Jinja2:**
```python
_config_descriptions = {
    "user_prompt": (
        "Jinja2 template. Reference fields with {{ field_name }} or "
        "{{ metadata.field_name }}"
    ),
}
```

**Rendering:**
```python
from lib.template_renderer import render_template

rendered = render_template(self.user_prompt, context.accumulated_state)
```

### JSON Object/Array (Monaco Editor)

Parameters typed as `dict` or `list` get JSON Monaco editor:

```python
def __init__(
    self,
    json_schema: dict[str, Any],  # JSON editor
    field_list: list[str],        # JSON editor
):
    self.json_schema = json_schema
    self.field_list = field_list
```

### Number Input

Parameters typed as `int` or `float` get number input:

```python
def __init__(
    self,
    temperature: float = 0.7,  # number input
    max_tokens: int = 2048,    # number input
):
    self.temperature = temperature
```

### Textarea

Parameters with these patterns get multi-line textarea:
- String length > 100 characters
- Name contains "description"
- Type has long content

```python
def __init__(
    self,
    description: str = "",  # automatically gets textarea
):
    self.description = description
```

### Text Input (Default)

Short string parameters get single-line text input:

```python
def __init__(
    self,
    name: str,
    label: str = "",
):
    self.name = name
```

## JSON Array as String Pattern

For parameters that should accept either JSON array or Jinja template (like `fields_to_generate`):

```python
def __init__(
    self,
    fields_to_generate: str,  # str, not list[str]
):
    self.fields_to_generate_template = fields_to_generate

_config_descriptions = {
    "fields_to_generate": (
        'JSON array or Jinja template. Examples: ["bio", "storage"] or '
        '{{ fields_to_generate | tojson }}'
    ),
}
```

**Parsing in execute:**
```python
import json

fields_rendered = render_template(
    self.fields_to_generate_template,
    context.accumulated_state
)
try:
    fields_list = json.loads(fields_rendered)
    if not isinstance(fields_list, list):
        raise BlockExecutionError("Must be JSON array")
except json.JSONDecodeError as e:
    raise BlockExecutionError(f"Invalid JSON: {str(e)}")
```

**Template usage:**
```yaml
fields_to_generate: "{{ fields_to_generate | tojson }}"
```

## LLM Integration Pattern

Full pattern for blocks that call LLM:

```python
async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
    from app import llm_config_manager

    # prepare messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # get llm config
    llm_config = await llm_config_manager.get_llm_model(self.model_name)
    llm_params = llm_config_manager.prepare_llm_call(
        llm_config,
        messages=messages,
        temperature=self.temperature,
        max_tokens=self.max_tokens,
    )

    # add trace metadata for langfuse grouping
    llm_params["metadata"] = {
        "trace_id": context.trace_id,
        "tags": ["datagenflow"],
    }

    logger.info(f"Calling LiteLLM with model={llm_params.get('model')}")

    try:
        response = await litellm.acompletion(**llm_params)
    except Exception as e:
        logger.error(f"LLM call failed for {self.name}: {e}")
        raise

    content = response.choices[0].message.content

    # extract usage info
    usage_info = pipeline.Usage(
        input_tokens=response.usage.prompt_tokens or 0,
        output_tokens=response.usage.completion_tokens or 0,
        cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
    )

    return {
        "generated": content,
        "_usage": usage_info.model_dump(),
    }
```

## Embedding Integration Pattern

Full pattern for blocks that call embedding APIs:

```python
async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
    from app import llm_config_manager

    # get embedding config
    embedding_config = await llm_config_manager.get_embedding_model(
        self.embedding_model_name
    )

    # prepare embedding call
    embedding_params = llm_config_manager._prepare_embedding_call(
        embedding_config,
        input_text=texts,  # list of strings
    )

    response = await litellm.aembedding(**embedding_params)
    embeddings = [item["embedding"] for item in response.data]

    # extract usage from embedding response (no output tokens)
    usage_info = pipeline.Usage(
        input_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
        output_tokens=0,  # embeddings don't have output tokens
        cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
    )

    return {
        "embeddings": embeddings,
        "_usage": usage_info.model_dump(),
    }
```

**Note:** If making multiple API calls, accumulate usage:

```python
total_usage = pipeline.Usage(
    input_tokens=usage1.input_tokens + usage2.input_tokens,
    output_tokens=usage1.output_tokens + usage2.output_tokens,
    cached_tokens=usage1.cached_tokens + usage2.cached_tokens,
)
```

**Important:** `_usage` must be at the TOP LEVEL of the return dict, not nested inside other fields. If processing multiple items that each have usage, aggregate before returning:

```python
# aggregate usage from all items
total_usage = pipeline.Usage()
for item in items:
    if "_usage" in item:
        item_usage = item.pop("_usage")
        total_usage.input_tokens += item_usage.get("input_tokens", 0)
        total_usage.output_tokens += item_usage.get("output_tokens", 0)
        total_usage.cached_tokens += item_usage.get("cached_tokens", 0)

return {"items": items, "_usage": total_usage.model_dump()}
```

## State Management

### Reading State

```python
async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
    # get current record
    current = context.accumulated_state.copy()

    # remove internal fields
    current.pop("_usage", None)
    current.pop("_hints", None)

    # get reference data from initial state
    samples = context.get_state("samples", [])
```

### Caching Per Execution

**Never use instance-level state that persists across jobs.** Use trace_id-keyed caching:

```python
def __init__(self):
    # cache per trace_id (one cache per pipeline execution)
    self._embeddings_cache: dict[str, list[list[float]]] = {}

async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
    trace_id = context.trace_id

    # build cache once per pipeline execution
    if trace_id not in self._embeddings_cache:
        # compute embeddings
        self._embeddings_cache[trace_id] = embeddings

    # use cached data
    cached_embeddings = self._embeddings_cache[trace_id]
```

## Multiplier Blocks

Blocks that generate multiple items from one input:

```python
from lib.blocks.base import BaseMultiplierBlock
from lib.entities.block_execution_context import BlockExecutionContext

class StructureSampler(BaseMultiplierBlock):
    name = "Structure Sampler"
    category = "seeders"

    async def execute(
        self,
        context: BlockExecutionContext
    ) -> list[dict[str, Any]]:
        # read from context and return list of records
        return [record1, record2, record3]
```

## Code Quality

### KISS Principle

Write minimal number of functions, make code self-explanatory:

```python
# ✅ good - simple and clear
def _prepare_prompts(self, data: dict[str, Any]) -> tuple[str, str]:
    """render jinja2 templates with data context"""
    system_template = self.system_prompt or data.get("system", "")
    user_template = self.user_prompt or data.get("user", "")

    system = render_template(system_template, data) if system_template else ""
    user = render_template(user_template, data) if user_template else ""

    return system, user

# ❌ bad - over-engineered with too many tiny functions
def _get_system(self, data): ...
def _get_user(self, data): ...
def _render_system(self, template, data): ...
def _render_user(self, template, data): ...
```

### Comments

Comments in lowercase, explain WHY not WHAT:

```python
# ✅ good - explains why
def _extract_text(self, record: dict[str, Any]) -> str:
    """
    extract text from specified fields or all string fields
    joins with spaces for embedding
    """

# ❌ bad - just describes what code does
def _extract_text(self, record: dict[str, Any]) -> str:
    """Extract text from record fields"""
    # Loop through fields and get string values
```

### Imports

All imports at top of file, not inside functions (except `from app import llm_config_manager`):

```python
# ✅ good
import json
import logging
from typing import Any

import litellm

from lib.blocks.base import BaseBlock

# ❌ bad
def execute(self, context):
    import json  # wrong place
```

**Exception:** `from app import llm_config_manager` goes inside `execute()` to avoid circular imports.

## Testing

### Unit Tests

Create `tests/blocks/test_<block_name>.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from lib.blocks.builtin.my_block import MyBlock
from lib.entities.block_execution_context import BlockExecutionContext


def make_context(state: dict) -> BlockExecutionContext:
    """helper to create test context"""
    return BlockExecutionContext(
        trace_id="test-trace",
        pipeline_id=1,
        accumulated_state=state,
    )


class TestMyBlockInit:
    def test_init_basic(self):
        block = MyBlock(param="value")
        assert block.param == "value"


class TestMyBlockExecution:
    @pytest.mark.asyncio
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_basic(self, mock_config_manager, mock_completion):
        # setup mocks
        mock_config_manager.get_llm_model = AsyncMock(...)
        mock_completion.return_value = MagicMock(...)

        block = MyBlock(param="value")
        context = make_context({"field": "value"})

        result = await block.execute(context)

        assert result["field"] == "expected"
```

### Integration Tests

Add to `tests/integration/test_data_augmentation.py`.

## Documentation Updates

**Always update after implementing:**

1. **llm/state-project.md** - block count, description
2. **llm/state-backend.md** - block count, details
3. **lib/templates/** - template YAML if applicable

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Parameter named `model_name` | No dropdown UI | Name it exactly `model` |
| Parameter named `embedding` | No dropdown UI | Name it exactly `embedding_model` |
| `list[str]` for JSON arrays | Can't use templates | Use `str`, render + parse |
| Instance-level cache | Data leaks between jobs | Use `dict[str, T]` keyed by `trace_id` |
| Imports inside functions | Not the codebase style | Move to top (except llm_config_manager) |
| Over-engineering | Too many tiny functions | KISS - keep it simple |
| Comments describe what | Obvious from code | Explain WHY, lowercase |
| Forgot `_usage` | Usage not tracked | Always return `_usage` from LLM/embeddings |
| `_usage` nested in items | Usage not found | `_usage` must be at TOP LEVEL of return dict |
| Missing `_config_descriptions` | No help text in UI | Add descriptions for all params |
| Wrong enum format | UI doesn't render dropdown | Use `_config_enums` class attribute |

## Implementation Checklist

**Design:**
- [ ] Choose block type (BaseBlock vs BaseMultiplierBlock)
- [ ] Define inputs/outputs
- [ ] Identify parameters and their types
- [ ] Name model parameters correctly (`model`, `embedding_model`)
- [ ] Decide which params need enum dropdowns or field references

**Implementation:**
- [ ] Add all imports at top (except llm_config_manager)
- [ ] Create class with `name`, `description`, `category`, `inputs`, `outputs`
- [ ] Add `_config_descriptions` with helpful UI text
- [ ] Add `_config_enums` if using dropdowns
- [ ] Add `_field_references` if using field selection
- [ ] Implement `__init__` with correct parameter types
- [ ] Implement `execute()` method
- [ ] Add template rendering if needed
- [ ] Use `llm_config_manager.get_llm_model()` for LLM
- [ ] Use `llm_config_manager.get_embedding_model()` for embeddings
- [ ] Add trace metadata to `llm_params["metadata"]`
- [ ] Track usage with `pipeline.Usage()` and return `_usage` (LLM and embeddings)
- [ ] Use trace_id-keyed caching if needed
- [ ] Write lowercase comments explaining WHY

**Testing:**
- [ ] Create unit test file `tests/blocks/test_<block_name>.py`
- [ ] Test initialization variants
- [ ] Test execution with mocked LLM config
- [ ] Test edge cases and error handling
- [ ] Add integration test
- [ ] Run `pytest tests/` - all pass

**Documentation:**
- [ ] Update `llm/state-project.md`
- [ ] Update `llm/state-backend.md`
- [ ] Create template YAML if applicable

**Review:**
- [ ] Model parameters named exactly right
- [ ] Imports at top (except llm_config_manager)
- [ ] No instance-level state
- [ ] KISS principle followed
- [ ] `_usage` returned if using LLM or embeddings
- [ ] All UI integrations correct (enums, field refs, descriptions)

## Reference Examples

**Simple:** `lib/blocks/builtin/field_mapper.py`

**LLM:** `lib/blocks/builtin/text_generator.py`

**Structured:** `lib/blocks/builtin/structured_generator.py`

**Multiplier:** `lib/blocks/builtin/structure_sampler.py`

**Embedding:** `lib/blocks/builtin/duplicate_remover.py`
