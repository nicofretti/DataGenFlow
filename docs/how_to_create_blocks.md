---
title: How to Create Custom Blocks
description: Extend DataGenFlow with custom blocks for your specific use cases
---

# How to Create Custom Blocks

This guide shows you how to extend DataGenFlow with custom blocks.

## Table of Contents
- [What is a Block?](#what-is-a-block)
- [Quick Example](#quick-example)
- [Block Anatomy](#block-anatomy)
- [Step-by-Step Guide](#step-by-step-guide)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Testing Custom Blocks](#testing-custom-blocks)
- [Debugging](#debugging)
- [Common Patterns](#common-patterns)
- [Next Steps](#next-steps)

## What is a Block?

A block is a reusable component that:
1. Takes inputs from accumulated state (previous blocks' outputs + seed data)
2. Executes custom logic
3. Outputs data that gets added to accumulated state

Blocks are the building blocks of pipelines, connected visually in the pipeline editor.

### Built-in Blocks

DataGenFlow includes these atomic blocks:

**Generators:**
- **TextGenerator**: Generate text using LiteLLM (multi-provider LLM access)
- **StructuredGenerator**: Generate structured JSON with schema validation

**Metrics:**
- **DiversityScore**: Calculate lexical diversity for text variations
- **CoherenceScore**: Measure text coherence based on sentence structure
- **RougeScore**: Calculate ROUGE score comparing generated vs reference text

**Validators:**
- **ValidatorBlock**: Validate text content (length, forbidden words, patterns)
- **JSONValidatorBlock**: Parse and validate JSON from any accumulated state field

**Seeders:**
- **MarkdownMultiplierBlock**: Split markdown documents into chunks for batch processing

You can create custom blocks to add your own logic and integrate with external services.

## Quick Example

```python
from lib.blocks.base import BaseBlock
from typing import Any

class UppercaseBlock(BaseBlock):
    """converts text to uppercase"""

    name = "Uppercase"
    description = "Convert text to uppercase"
    inputs = ["text"]
    outputs = ["result"]

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text = data.get("text", "")
        return {"result": text.upper()}
```

That's it! Save this in `user_blocks/uppercase.py` and it's automatically available in the UI.

## Block Anatomy

### Class Definition

```python
from lib.blocks.base import BaseBlock

class MyBlock(BaseBlock):
    # ...
```

All custom blocks must inherit from `BaseBlock`.

### Required Attributes

```python
name = "My Block"           # Display name in UI
description = "What it does" # Help text for users
inputs = ["field1", "field2"]  # Expected input fields
outputs = ["result"]        # Output field names
```

**Special values**:
- `inputs = ["*"]` - Accept all available fields
- `inputs = []` - No inputs required
- `outputs = []` - No outputs (terminal block)

### Configuration Parameters

```python
def __init__(self, param1: str, param2: int = 10):
    self.param1 = param1
    self.param2 = param2
```

Parameters become configuration options in the UI:
- Type hints are used for validation
- Default values make parameters optional
- Supported types: `str`, `int`, `float`, `bool`, `dict`, `list`
  - `str`/`int`/`float`/`bool`: Rendered as text/number/checkbox inputs
  - `dict`: Rendered as Monaco JSON editor with syntax highlighting
  - `list`: Rendered as Monaco JSON editor (for complex lists) or array input

### UI Configuration Features

**Enum Dropdowns:**
```python
class MyBlock(BaseBlock):
    _config_enums = {
        "mode": ["fast", "accurate", "balanced"]
    }

    def __init__(self, mode: str = "balanced"):
        self.mode = mode
```
The UI will show a dropdown with the three options instead of a text input.

**Field Reference Dropdowns:**
```python
class MyBlock(BaseBlock):
    _field_references = ["input_field", "reference_field"]

    def __init__(self, input_field: str = "assistant", reference_field: str = "reference"):
        self.input_field = input_field
        self.reference_field = reference_field
```
The UI will show editable dropdowns populated with available fields from previous blocks in the pipeline. Users can select from suggestions or type custom field names.

**Field Descriptions (Inline Help):**
```python
class MyBlock(BaseBlock):
    _config_descriptions = {
        "prompt": "Jinja2 template. Reference fields with {{ field_name }} or {{ metadata.field_name }}",
        "api_key": "Your API key from the service dashboard"
    }

    def __init__(self, prompt: str = "", api_key: str = ""):
        self.prompt = prompt
        self.api_key = api_key
```
The UI will show these descriptions below each config field to help users understand how to use them.

**Object/Dict Configuration (JSON Editor):**
```python
class MyBlock(BaseBlock):
    _config_descriptions = {
        "json_schema": "JSON Schema defining the structure of output data"
    }

    def __init__(self, json_schema: dict[str, Any]):
        self.json_schema = json_schema
```
The UI will show a Monaco JSON editor with syntax highlighting for `dict` and `list` type parameters.

**Complete Example with All Features:**
```python
from lib.blocks.base import BaseBlock
from typing import Any

class AdvancedBlock(BaseBlock):
    name = "Advanced Block"
    description = "Example block with all UI features"
    inputs = []
    outputs = ["result"]

    # Enum dropdown for mode selection
    _config_enums = {
        "mode": ["fast", "balanced", "accurate"]
    }

    # Field reference dropdowns
    _field_references = ["input_field"]

    # Inline help text
    _config_descriptions = {
        "prompt": "Jinja2 template. Use {{ field_name }} to reference previous outputs",
        "schema": "JSON Schema for validation",
        "mode": "Processing mode affects speed and quality"
    }

    def __init__(
        self,
        input_field: str = "assistant",
        prompt: str = "",
        schema: dict[str, Any] = None,
        mode: str = "balanced",
        temperature: float = 0.7
    ):
        self.input_field = input_field
        self.prompt = prompt
        self.schema = schema or {}
        self.mode = mode
        self.temperature = temperature

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # Your implementation here
        return {"result": "processed"}
```

This will generate a UI with:
- `input_field`: Editable dropdown with available fields
- `prompt`: Text input with help text below
- `schema`: Monaco JSON editor with syntax highlighting
- `mode`: Dropdown with three options
- `temperature`: Number input

### Execute Method

```python
async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
    # 1. Extract inputs
    input_value = data.get("input_field")

    # 2. Process data
    result = self._do_something(input_value)

    # 3. Return outputs
    return {"output_field": result}
```

The `data` dict contains:
- All outputs from previous blocks
- Initial seed metadata
- This is called "accumulated state"

## Step-by-Step Guide

### 1. Choose a Location

**Option A: User blocks** (recommended)
```bash
user_blocks/
└── my_block.py
```
Use this for personal/experimental blocks.

**Option B: Custom blocks**
```bash
lib/blocks/custom/
└── my_block.py
```
Use this for blocks you might contribute back to the project.

### 2. Create the File

```python
"""
my custom block that does X
"""
from lib.blocks.base import BaseBlock
from typing import Any

class MyBlock(BaseBlock):
    name = "My Block"
    description = "Describe what your block does"
    inputs = ["required_field"]
    outputs = ["result"]

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # your logic here
        value = data.get("required_field")
        result = value.upper()  # example
        return {"result": result}
```

### 3. Test It

**Option A: Via UI**
1. Restart the server (`make run`)
2. Go to Builder tab
3. Click "Add Block"
4. Your block should appear in the list

**Option B: Via Test**
```python
import pytest
from user_blocks.my_block import MyBlock

@pytest.mark.asyncio
async def test_my_block():
    block = MyBlock()
    result = await block.execute({"required_field": "hello"})
    assert result["result"] == "HELLO"
```

Run: `pytest tests/`

### 4. Use in Pipeline

1. Create pipeline in UI
2. Add your block
3. Configure it
4. Connect to other blocks
5. Test with seed data

## Examples

### Example 1: Text Transformation

```python
from lib.blocks.base import BaseBlock
from typing import Any

class SentenceCaseBlock(BaseBlock):
    """converts text to sentence case"""

    name = "Sentence Case"
    description = "Capitalize first letter, lowercase the rest"
    inputs = ["text"]
    outputs = ["result"]

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text = data.get("text", "")

        # early return for empty input
        if not text:
            return {"result": ""}

        # capitalize first char, lowercase rest
        result = text[0].upper() + text[1:].lower()
        return {"result": result}
```

### Example 2: Block with Configuration

```python
from lib.blocks.base import BaseBlock
from typing import Any

class TruncateBlock(BaseBlock):
    """truncate text to max length"""

    name = "Truncate"
    description = "Limit text to maximum length"
    inputs = ["text"]
    outputs = ["result"]

    def __init__(self, max_length: int = 100, suffix: str = "..."):
        self.max_length = max_length
        self.suffix = suffix

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text = data.get("text", "")

        # no truncation needed
        if len(text) <= self.max_length:
            return {"result": text}

        # truncate and add suffix
        truncated = text[:self.max_length - len(self.suffix)]
        result = truncated + self.suffix
        return {"result": result}
```

**UI shows**:
- Max Length: [100] (number input)
- Suffix: [...] (text input)

### Example 3: Multiple Inputs/Outputs

```python
from lib.blocks.base import BaseBlock
from typing import Any

class CombineBlock(BaseBlock):
    """combine two text fields"""

    name = "Combine Text"
    description = "Join two text fields with a separator"
    inputs = ["text1", "text2"]
    outputs = ["combined", "length"]

    def __init__(self, separator: str = " "):
        self.separator = separator

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text1 = data.get("text1", "")
        text2 = data.get("text2", "")

        combined = f"{text1}{self.separator}{text2}"

        return {
            "combined": combined,
            "length": len(combined)
        }
```

### Example 4: Using External APIs

```python
from lib.blocks.base import BaseBlock
from typing import Any
import httpx

class TranslateBlock(BaseBlock):
    """translate text using external API"""

    name = "Translate"
    description = "Translate text to another language"
    inputs = ["text"]
    outputs = ["translated"]

    def __init__(self, target_language: str = "es"):
        self.target_language = target_language

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text = data.get("text", "")

        # call external translation API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://translation-api.example.com/translate",
                json={
                    "text": text,
                    "target": self.target_language
                }
            )
            result = response.json()

        return {"translated": result["translation"]}
```

### Example 5: Accept All Inputs

```python
from lib.blocks.base import BaseBlock
from typing import Any
import json

class DebugBlock(BaseBlock):
    """print all accumulated state for debugging"""

    name = "Debug"
    description = "Print all available data"
    inputs = ["*"]  # accept everything
    outputs = ["debug_info"]

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # format all data as JSON
        debug_info = json.dumps(data, indent=2)
        print("DEBUG:", debug_info)

        return {"debug_info": debug_info}
```

### Example 6: Field References and Descriptions (Real-World)

```python
from lib.blocks.base import BaseBlock
from typing import Any
from difflib import SequenceMatcher

class TextSimilarityBlock(BaseBlock):
    """compare two text fields for similarity"""

    name = "Text Similarity"
    description = "Calculate similarity score between two text fields"
    inputs = []
    outputs = ["similarity_score"]

    # Mark which parameters reference accumulated state fields
    _field_references = ["field1", "field2"]

    # Provide helpful descriptions for users
    _config_descriptions = {
        "field1": "First field to compare (select from previous block outputs)",
        "field2": "Second field to compare (select from previous block outputs)"
    }

    def __init__(self, field1: str = "assistant", field2: str = "reference"):
        self.field1 = field1
        self.field2 = field2

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text1 = data.get(self.field1, "")
        text2 = data.get(self.field2, "")

        # calculate similarity
        similarity = SequenceMatcher(None, text1, text2).ratio()

        return {"similarity_score": similarity}
```

**In the UI, users will see:**
- `field1`: Dropdown showing available fields (e.g., "assistant", "text", "generated") with help text
- `field2`: Dropdown showing available fields with help text
- Both dropdowns are editable, so users can type custom field names if needed

### Example 7: JSON Schema Configuration

```python
from lib.blocks.base import BaseBlock
from typing import Any
import jsonschema

class SchemaValidator(BaseBlock):
    """validate data against a JSON schema"""

    name = "Schema Validator"
    description = "Validate JSON data against a custom schema"
    inputs = []
    outputs = ["valid", "errors"]

    _field_references = ["data_field"]

    _config_descriptions = {
        "data_field": "Field containing the data to validate",
        "schema": "JSON Schema for validation (use Monaco editor)"
    }

    def __init__(self, data_field: str = "generated", schema: dict[str, Any] = None):
        self.data_field = data_field
        self.schema = schema or {}

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        data_to_validate = data.get(self.data_field)

        try:
            jsonschema.validate(instance=data_to_validate, schema=self.schema)
            return {"valid": True, "errors": []}
        except jsonschema.ValidationError as e:
            return {"valid": False, "errors": [str(e)]}
```

**In the UI, users will see:**
- `data_field`: Editable dropdown with available fields
- `schema`: Monaco JSON editor with syntax highlighting, line numbers, and auto-formatting

## Best Practices

### Error Handling

```python
async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
    text = data.get("required_field")

    # validate input exists
    if text is None:
        raise ValueError("required_field is missing from data")

    # handle processing errors
    try:
        result = self._process(text)
    except Exception as e:
        raise RuntimeError(f"processing failed: {e}")

    return {"result": result}
```

### Input Validation

```python
def __init__(self, max_length: int = 100):
    # validate config at initialization
    if max_length <= 0:
        raise ValueError("max_length must be positive")

    self.max_length = max_length
```

### Async Operations

```python
async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
    # use await for async operations
    result = await self._fetch_from_api()

    # multiple async operations in parallel
    import asyncio
    results = await asyncio.gather(
        self._fetch_1(),
        self._fetch_2(),
    )

    return {"result": results}
```

### Documentation

```python
class MyBlock(BaseBlock):
    """
    one-line summary

    longer description if needed explaining:
    - what the block does
    - when to use it
    - any limitations or requirements
    """

    name = "My Block"
    # ...
```

## Testing Custom Blocks

### Unit Test Template

```python
import pytest
from user_blocks.my_block import MyBlock

@pytest.mark.asyncio
async def test_basic_functionality():
    """test that block produces expected output"""
    block = MyBlock()
    result = await block.execute({"input": "test"})
    assert result["output"] == "expected"

@pytest.mark.asyncio
async def test_with_config():
    """test block with custom configuration"""
    block = MyBlock(param=123)
    result = await block.execute({"input": "test"})
    assert result["output"] == "expected with param"

@pytest.mark.asyncio
async def test_missing_input():
    """test error handling for missing inputs"""
    block = MyBlock()
    with pytest.raises(ValueError):
        await block.execute({})  # no input provided
```

Run tests:
```bash
pytest tests/ -v
```

## Debugging

### Enable Debug Logging

In `.env`:
```bash
DEBUG=true
```

Restart server and check logs for:
- Block execution timing
- Data passed between blocks
- Errors with full stack traces

### Use Execution Traces

In the Review tab:
1. Click "View Trace" on a record
2. Find your block in the trace
3. Check `accumulated_state` to see inputs
4. Check outputs to verify results

### Print Debugging

```python
async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
    print(f"DEBUG: input data = {data}")

    result = self._process(data)

    print(f"DEBUG: result = {result}")

    return {"output": result}
```

Check terminal/logs for output.

## Common Patterns

### Conditional Logic

```python
async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
    text = data.get("text", "")

    # early return for edge cases
    if not text:
        return {"result": ""}

    if len(text) < 10:
        return {"result": text.upper()}

    return {"result": text.lower()}
```

### String Templates (Jinja2)

```python
from lib.template_renderer import render_template

async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
    # use jinja2 templates with accumulated state
    template = "Hello {{ name }}, you are {{ age }} years old"
    result = render_template(template, data)
    return {"result": result}
```

### State Accumulation

```python
# Block 1 outputs: {"text": "hello", "count": 5}
# Block 2 outputs: {"uppercase": "HELLO"}
# Block 3 receives: {"text": "hello", "count": 5, "uppercase": "HELLO"}

async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
    # access outputs from previous blocks
    original = data.get("text")
    uppercase = data.get("uppercase")
    count = data.get("count")

    # all previous outputs available
    return {"combined": f"{uppercase} ({count})"}
```

## Reference: Built-in Blocks Implementation

Study these for real-world examples:

**StructuredGenerator** (`lib/blocks/builtin/structured_generator.py`):
- Uses `dict[str, Any]` for `json_schema` parameter (Monaco JSON editor)
- Uses `_config_descriptions` to explain Jinja2 template syntax
- Shows how to integrate with LiteLLM for structured generation

**RougeScore** (`lib/blocks/builtin/rouge_score.py`):
- Uses `_config_enums` for `rouge_type` dropdown
- Uses `_field_references` for `generated_field` and `reference_field`
- Example of comparing two fields from accumulated state

**TextGenerator** (`lib/blocks/builtin/text_generator.py`):
- Uses `_config_descriptions` for prompt fields
- Shows async LLM API calls
- Demonstrates conditional logic based on configuration

**JSONValidatorBlock** (`lib/blocks/builtin/json_validator.py`):
- Handles both string and parsed object inputs
- Uses `_field_references` for flexible field selection
- Shows error handling with strict/non-strict modes

## Next Steps

- **Check builtin blocks for examples**: Explore `lib/blocks/builtin/` for reference implementations
- **Read developer guide**: [DEVELOPERS.md](DEVELOPERS) for architecture details and API reference
- **Contribute your block**: Share useful blocks with the community via [CONTRIBUTING.md](CONTRIBUTING)
