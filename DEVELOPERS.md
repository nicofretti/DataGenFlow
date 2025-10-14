# Developer Guide

Complete technical documentation for DataGenFlow developers.

## Table of Contents
- [Architecture](#architecture)
- [Development Setup](#development-setup)
- [Testing](#testing)
- [API Reference](#api-reference)
- [Debugging](#debugging)
- [Code Quality](#code-quality)

## Architecture

### Project Structure

```
lib/
  blocks/
    builtin/          # Stable blocks (llm, validator, json_validator, output)
    custom/           # Experimental blocks
    base.py           # BaseBlock interface
    registry.py       # Auto-discovery engine
  templates/          # Pipeline templates (YAML)
  errors.py           # Custom exception classes
  workflow.py         # Pipeline execution with tracing
  storage.py          # Database operations (aiosqlite)
  generator.py        # LLM wrapper (OpenAI-compatible)
  template_renderer.py  # Jinja2 template rendering

frontend/
  src/
    pages/
      Pipelines.tsx   # Visual pipeline builder and manager
      Generator.tsx   # Dataset generation with progress tracking
      Review.tsx      # Review records with execution traces
    components/
      pipeline-editor/  # ReactFlow-based visual editor

tests/
  conftest.py         # Test configuration and fixtures
  blocks/             # Block unit tests
  test_api.py         # API endpoint tests
  test_workflow.py    # Pipeline execution tests
  test_storage.py     # Database operations tests
  test_errors.py      # Error handling tests
```

### Core Concepts

**Block System**
- Blocks are the fundamental building units
- Each block declares inputs and outputs
- Blocks execute asynchronously and return dictionaries
- Output validation enforced at runtime

**Pipeline Execution**
- Sequential execution with accumulated state
- Full trace capture (inputs, outputs, timing, errors)
- Correlation IDs for request tracking
- Graceful error handling with context

**Storage Layer**
- SQLite with aiosqlite for async operations
- Separate tables: pipelines, jobs, records
- Automatic schema migrations
- Foreign key constraints for data integrity

## Development Setup

### Prerequisites
- Python 3.10+
- Node.js 16+ and Yarn
- uv (Python package manager)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd QADataGen

# Install dependencies
make dev

# Run tests
make test
```

### Development Workflow

```bash
# Start development servers (hot reload)
make run-dev

# Run separately
make dev-backend  # Backend only (port 8000)
make dev-ui       # Frontend only (port 5173)

# Code quality
make lint          # Backend linting (ruff)
make typecheck     # Type checking (mypy)
make format        # Format code (ruff)
make lint-frontend # Frontend linting (ESLint)
make typecheck-frontend  # TypeScript type checking

# Production build
make build-ui      # Build frontend
make run           # Run production server
```

## Testing

### Running Tests

```bash
# All tests (93 tests)
make test

# Specific test suites
uv run pytest tests/blocks/ -v
uv run pytest tests/test_api.py -v
uv run pytest tests/test_workflow.py -v

# With coverage
uv run pytest --cov=lib --cov=app tests/
```

### Test Database

Tests use a separate database (`data/test_qa_records.db`) that is:
- Automatically created before tests
- Completely isolated from production data
- Cleaned up after test session

See `TEST_DATABASE.md` for detailed information.

### Writing Tests

```python
import pytest

@pytest.mark.asyncio
async def test_pipeline_execution():
    """Test pipeline execution with trace"""
    pipeline = Pipeline(...)
    result, trace, trace_id = await pipeline.execute({"input": "test"})
    
    assert "output" in result
    assert len(trace) > 0
    assert trace_id is not None
```

## API Reference

### Blocks API

**List all blocks**
```bash
GET /api/blocks
```

Response:
```json
[
  {
    "type": "LLMBlock",
    "name": "LLM Generator",
    "description": "Generate text using LLM",
    "inputs": ["system", "user"],
    "outputs": ["assistant"],
    "config": {
      "temperature": "float",
      "max_tokens": "int"
    }
  }
]
```

### Pipelines API

**Create pipeline**
```bash
POST /api/pipelines
Content-Type: application/json

{
  "name": "My Pipeline",
  "blocks": [
    {
      "type": "LLMBlock",
      "config": {"temperature": 0.7}
    }
  ]
}
```

**Execute pipeline**
```bash
POST /api/pipelines/{id}/execute
Content-Type: application/json

{"text": "input data"}
```

Response:
```json
{
  "result": {"output": "..."},
  "trace": [
    {
      "block_type": "LLMBlock",
      "input": {...},
      "output": {...},
      "accumulated_state": {...},
      "execution_time": 1.234
    }
  ],
  "trace_id": "uuid"
}
```

### Jobs API

**Start generation job**
```bash
POST /api/generate
Content-Type: multipart/form-data

file=@seeds.json
pipeline_id=1
```

**Get job status**
```bash
GET /api/jobs/{job_id}
```

Response:
```json
{
  "id": 1,
  "pipeline_id": 1,
  "status": "running",
  "total_seeds": 100,
  "records_generated": 45,
  "records_failed": 2
}
```

### Records API

**List records**
```bash
GET /api/records?status=pending&limit=100&job_id=1
```

**Update record**
```bash
PUT /api/records/{id}
Content-Type: application/json

{
  "status": "accepted",
  "output": "updated text"
}
```

**Export records**
```bash
GET /api/export?status=accepted&job_id=1
GET /api/export/download?status=accepted
```

## Debugging

### Debug Mode

Enable detailed logging in `.env`:
```bash
DEBUG=true
```

**Features:**
- Correlation IDs in all logs
- Per-block execution timing
- Full input/output state logging
- Stack traces with context

**Example logs:**
```
2025-10-14 10:15:32 [INFO] [a1b2c3d4] Pipeline 'Data Gen' started (3 blocks)
2025-10-14 10:15:32 [DEBUG] [a1b2c3d4] Block 1/3: LLMBlock executing
2025-10-14 10:15:35 [DEBUG] [a1b2c3d4] LLMBlock completed (3.124s)
2025-10-14 10:15:35 [INFO] [a1b2c3d4] Pipeline completed successfully
```

### Error Handling

**Custom Exceptions**
- `BlockNotFoundError`: Block type not registered
- `BlockExecutionError`: Runtime execution failure
- `ValidationError`: Output validation failure

All exceptions include:
- Structured error message
- Context dictionary with details
- HTTP-appropriate status codes

**Error Response Format:**
```json
{
  "error": "Block 'InvalidBlock' not found",
  "detail": {
    "block_type": "InvalidBlock",
    "available_blocks": ["LLMBlock", "ValidatorBlock", ...]
  }
}
```

## Code Quality

### Type Checking

**Mypy Configuration** (`pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true

[[tool.mypy.overrides]]
module = "tests.*"
disable_error_code = ["no-untyped-def"]
```

Run type checking:
```bash
make typecheck  # Backend
make typecheck-frontend  # Frontend
```

### Linting

**Ruff (Backend)**
```bash
make lint    # Check
make format  # Fix
```

**ESLint (Frontend)**
```bash
make lint-frontend  # Check
```

### Code Style

- **Backend**: Follow PEP 8, enforced by ruff
- **Frontend**: Prettier + ESLint
- **Line length**: 100 characters
- **Imports**: Sorted automatically
- **Type hints**: Required for all public APIs

## Custom Block Development

### Block Interface

```python
from lib.blocks.base import BaseBlock
from typing import Any

class MyBlock(BaseBlock):
    # Required class attributes
    name: str = "My Block"
    description: str = "What this block does"
    inputs: list[str] = ["input_field"]
    outputs: list[str] = ["output_field"]
    
    # Optional: Get config schema for UI
    def get_schema(self) -> dict[str, Any]:
        return {
            "my_param": {
                "type": "string",
                "default": "default_value",
                "description": "Parameter description"
            }
        }
    
    # Required: Execute logic
    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # Access config
        param = self.config.get("my_param", "default")
        
        # Access input
        input_value = data["input_field"]
        
        # Your logic here
        result = process(input_value, param)
        
        # Return only declared outputs
        return {"output_field": result}
```

### Block Discovery

1. Create file in `user_blocks/` or `lib/blocks/custom/`
2. Inherit from `BaseBlock`
3. Restart server
4. Block automatically appears in UI

**Registry scans:**
- `lib/blocks/builtin/` - Stable blocks
- `lib/blocks/custom/` - Experimental blocks  
- `user_blocks/` - User-created blocks

### Testing Custom Blocks

```python
import pytest
from your_block import MyBlock

@pytest.mark.asyncio
async def test_my_block():
    block = MyBlock(config={"my_param": "test"})
    
    result = await block.execute({"input_field": "test data"})
    
    assert "output_field" in result
    assert result["output_field"] == expected_value
```

## Performance Optimization

### Database

- Use `LIMIT` and `OFFSET` for large result sets
- Records API supports pagination
- Indexes on frequently queried fields (`status`, `created_at`)

### Pipeline Execution

- Blocks execute sequentially (one at a time)
- Use `asyncio` for I/O-bound operations
- Trace overhead is minimal (~1-2ms per block)

### Frontend

- ReactFlow handles large pipelines efficiently
- Record review uses windowed scrolling
- API calls are debounced where appropriate

## Deployment

### Production Checklist

```bash
# Build frontend
make build-ui

# Set production environment
DEBUG=false
LLM_API_KEY=your-production-key

# Run with production server
make run

# Or use systemd/supervisor/docker
uv run uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (Optional)

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code style and conventions
- PR title format
- Review process
- Testing requirements

## Additional Resources

- [User Guide](docs/how_to_use.md)
- [Custom Blocks Guide](docs/how_to_create_blocks.md)
- [Test Database](TEST_DATABASE.md)
- [Contributing Guidelines](CONTRIBUTING.md)
