# Integration Tests

Integration tests verify actual integrations with external services like Ollama.

## Running Integration Tests

Integration tests are **NOT run by default**. They require external services to be running.

### Run all integration tests:
```bash
.venv/bin/pytest tests/integration/ -m integration -v
```

### Run specific integration test:
```bash
.venv/bin/pytest tests/integration/test_text_generator_integration.py::test_text_generator_ollama -m integration -v
```

### Run with output visible:
```bash
.venv/bin/pytest tests/integration/ -m integration -v -s
```

## Prerequisites

### Ollama
The TextGenerator and StructuredGenerator integration tests require Ollama to be running:

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull gemma3:1b`
3. Start Ollama (usually auto-starts): `ollama serve`
4. Verify it's running: `curl http://localhost:11434/api/tags`

## Adding New Integration Tests

1. Create test file in `tests/integration/`
2. Mark all integration tests with `@pytest.mark.integration`
3. Add async support with `@pytest.mark.asyncio` if needed
4. Document prerequisites in this README

Example:
```python
import pytest
from lib.blocks.builtin.text_generator import TextGenerator


@pytest.mark.integration
@pytest.mark.asyncio
async def test_text_generator_ollama():
    block = TextGenerator(model="gemma3:1b")
    result = await block.execute({"user": "Say hello"})
    assert "assistant" in result
```

## Why Skip by Default?

Integration tests:
- Require external services (Ollama, databases, APIs)
- Are slower than unit tests
- May have network dependencies
- Can fail due to service availability

Unit tests should cover logic; integration tests verify actual integrations.
