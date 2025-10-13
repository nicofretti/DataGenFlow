<div align="center">
  <img src="images/logo/banner.png" alt="DataGenFlow Logo"/>
</div>

[![License](https://img.shields.io/github/license/nicofretti/DataGenFlow)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/release/python-390/)

<div align="center">
  <p><strong>1. Build smarter workflows visually</strong><br>
  Drag, drop, and connect blocks in an intuitive pipeline builder.</p>
  <img src="images/pipelines.png" alt="Pipeline Builder" width="600"/>
  <br/>

  <p><strong>2. Generate Q&A records in seconds</strong><br>
  Feed your seed data and let custom pipelines do the heavy lifting.</p>
  <img src="images/generator.png" alt="Generator phase" width="600"/>
  <br/>

  <p><strong>3. Review and perfect your results</strong><br>
  Instantly edit, accept, or reject generated records with full trace visibility.</p>
  <img src="images/review.png" alt="Review phase" width="600"/>
  <br/>
</div>

## Quick Start

```bash
# install dependencies
make setup
make dev

# start both backend and frontend (single command)
make run-dev

# open browser at http://localhost:8000
```

## Using the Application

### 1. Creating Pipelines

1. Open http://localhost:8000
2. Navigate to "Builder" tab
3. Click "Add Block" to add blocks to your pipeline
4. Click on a block to configure it in the right panel
5. Blocks automatically chain together (data flows top to bottom)
6. Click "Save Pipeline" and give it a name

**Example Pipeline**:
- **LLMBlock**: Generate text using your LLM
- **ValidatorBlock**: Ensure output meets quality standards
- **OutputBlock**: Format the final result

For a detailed guide, see [How to Use QADataGen](docs/how_to_use.md).

### 2. Generating Records

1. Navigate to "Generator" tab
2. Upload your seed JSON file (see format below)
3. Select a pipeline from the dropdown
4. Click "Generate"
5. Wait for completion (progress indicator shows status)

### 3. Reviewing Results

1. Navigate to "Review" tab
2. Review each generated record
3. **Accept** (✅), **Reject** (❌), or **Edit** the output
4. Click "View Trace" to debug issues
5. Export accepted records as JSONL

## Seed File Format

Seed files define the variables used in your pipeline templates.

**Single seed**:
```json
{
  "repetitions": 2,
  "metadata": {
    "topic": "Python programming",
    "difficulty": "beginner"
  }
}
```

**Multiple seeds**:
```json
[
  {
    "repetitions": 1,
    "metadata": {
      "topic": "Python lists",
      "difficulty": "beginner"
    }
  },
  {
    "repetitions": 1,
    "metadata": {
      "topic": "Python dictionaries",
      "difficulty": "intermediate"
    }
  }
]
```

**Fields**:
- `repetitions`: How many times to run the pipeline with this seed
- `metadata`: Variables accessible in templates via `{{ variable_name }}`

## Configuration

Create `.env` file (or copy from `.env.example`):

```bash
# LLM Configuration
LLM_ENDPOINT=http://localhost:11434/v1  # Ollama, OpenAI, etc.
LLM_API_KEY=                            # Optional for some endpoints
LLM_MODEL=llama3.2

# Database
DATABASE_PATH=data/qa_records.db

# Server
HOST=0.0.0.0
PORT=8000

# Debug mode (optional)
DEBUG=false  # set to true for detailed logging
```

## Features

### Core System
- **Block-based pipelines**: Compose workflows from reusable blocks
- **Visual pipeline builder**: Drag-and-drop UI for creating pipelines
- **Execution tracing**: Full state history with timing for debugging
- **Pipeline templates**: Pre-configured pipelines for quick start
- **Custom blocks**: Easy extension with auto-discovery

### Built-in Blocks
- **LLMBlock**: Generate text using LLM (OpenAI-compatible)
- **ValidatorBlock**: Validate output against rules (length, forbidden words)
- **JSONValidatorBlock**: Parse and validate JSON from any field in accumulated state
- **OutputBlock**: Define final pipeline output using Jinja2 templates for the review system

### Developer Experience
- **Debug logging**: Toggle detailed execution logs with `DEBUG=true`
- **Trace IDs**: Track pipeline executions across logs and API responses
- **Execution timing**: Per-block timing in trace output
- **Error handling**: Structured error responses with context
- **Test isolation**: Separate test database, auto-cleanup

### Web UI
- **Builder**: Visual pipeline creation with drag-and-drop
- **Pipelines**: Manage and execute pipelines
- **Generator**: Generate Q&A datasets from seeds
- **Review**: Review, edit, accept/reject generated records with trace visualization

## Creating Custom Blocks

Create a file in `user_blocks/`:

```python
from lib.blocks.base import BaseBlock
from typing import Any

class MyBlock(BaseBlock):
    name = "My Block"
    description = "Does something useful"
    inputs = ["text"]
    outputs = ["result"]

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # your logic here
        result = data["text"].upper()
        return {"result": result}
```

The block is auto-discovered on startup and immediately available in the UI.

For detailed instructions and examples, see [How to Create Custom Blocks](docs/how_to_create_blocks.md).

## Development

```bash
# both backend and frontend (single command with hot reload)
make run-dev

# or run separately in different terminals
make dev-backend  # backend only
make dev-ui       # frontend only

# production mode (builds frontend)
make run

# code quality
make lint      # run linting
make typecheck # run type checking
make format    # format code
```

## Testing

```bash
# Run all tests
make test

# Run specific test suite
uv run pytest tests/blocks/ -v
uv run pytest tests/test_api.py -v

# Run with coverage
uv run pytest --cov=lib --cov=app tests/
```

Tests use a separate database (`data/test_qa_records.db`) that is automatically created and cleaned up. See `TEST_DATABASE.md` for details.

## Architecture

```
lib/
  blocks/
    builtin/          # Stable blocks (llm, validator, formatter, json_validator)
    custom/           # Experimental blocks
    base.py           # BaseBlock interface
    registry.py       # Auto-discovery engine
  templates/          # Pipeline templates
  errors.py           # Custom exception classes
  workflow.py         # Pipeline execution with tracing
  storage.py          # Database operations
  generator.py        # LLM wrapper

frontend/
  src/pages/
    Builder.tsx       # Visual pipeline builder
    Pipelines.tsx     # Pipeline manager
    Generator.tsx     # Dataset generation
    Review.tsx        # Review records with trace

tests/
  conftest.py         # Test configuration
  blocks/             # Block unit tests
  test_api.py         # API endpoint tests
  test_workflow.py    # Pipeline execution tests
```

## Advanced Usage (Optional)

### Using Pipeline Templates via API

Quick start with pre-configured pipelines:

```bash
# list available templates
curl http://localhost:8000/api/templates

# create pipeline from template
curl -X POST http://localhost:8000/api/pipelines/from_template/text_generation

# execute the pipeline
curl -X POST http://localhost:8000/api/pipelines/1/execute \
  -H "Content-Type: application/json" \
  -d '{"system": "You are helpful", "user": "Hello"}'
```

Available templates:
- `text_generation` - Simple LLM generation
- `validated_generation` - LLM + validation
- `text_transformation` - Text transformation chain
- `complete_qa_generation` - Full QA pipeline with validation and formatting

### API Endpoints

**Blocks**
- `GET /api/blocks` - List all registered blocks with schemas

**Templates**
- `GET /api/templates` - List available pipeline templates
- `POST /api/pipelines/from_template/{template_id}` - Create pipeline from template

**Pipelines**
- `POST /api/pipelines` - Create pipeline
- `GET /api/pipelines` - List all pipelines
- `GET /api/pipelines/{id}` - Get pipeline by ID
- `DELETE /api/pipelines/{id}` - Delete pipeline
- `POST /api/pipelines/{id}/execute` - Execute pipeline, returns `{result, trace, trace_id}`

**Records**
- `GET /api/records` - List records (supports status, limit, offset)
- `GET /api/records/{id}` - Get record by ID
- `PUT /api/records/{id}` - Update record
- `DELETE /api/records` - Delete all records
- `GET /api/export` - Export records as JSONL
- `GET /api/export/download` - Download export as file

**Generation**
- `POST /api/generate` - Generate records from seed file using pipeline

### Debug Mode

Enable debug logging to see detailed execution information:

```bash
# In .env
DEBUG=true
```

When enabled:
- Logs include trace IDs for correlation
- Per-block execution timing
- Detailed block name and step information

Example log output:
```
2025-10-06 10:15:32 [INFO] [a1b2c3d4-...] Starting pipeline 'Simple Text Generation' with 1 blocks
2025-10-06 10:15:32 [DEBUG] [a1b2c3d4-...] Executing block 1/1: LLMBlock
2025-10-06 10:15:35 [DEBUG] [a1b2c3d4-...] LLMBlock completed in 3.124s
2025-10-06 10:15:35 [INFO] [a1b2c3d4-...] Pipeline 'Simple Text Generation' completed successfully
```

## Error Handling

The system includes comprehensive error handling:

- **BlockNotFoundError**: When a block type doesn't exist (shows available blocks)
- **BlockExecutionError**: When a block fails (includes block name, step number, context)
- **ValidationError**: When a block returns undeclared fields (shows expected vs actual)

All errors return structured JSON responses with error messages and context for debugging.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- PR title conventions with icons (🚀 Feat, 🧩 Fix, etc.)
- PR description guidelines
- Code style guidelines
- Development workflow

## KISS Principles

This project follows Keep It Simple, Stupid principles:
- Minimal abstraction layers
- Flat structure over deep nesting
- Explicit over implicit
- Simple composition over inheritance
- Easy to understand and modify
