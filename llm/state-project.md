> **Important**
> The file should reflect the current status of the project for remembering purposes
> to describe the actual design, decisions and implementations. It must be technical and include the minimal number of words

# technical reference

## architecture

### core concepts
- **block-based pipelines**: compose workflows from reusable blocks
- **sequential execution**: blocks execute in order, accumulated state flows through
- **output validation**: blocks must return only declared outputs (enforced at runtime)
- **execution trace**: full history with input/output/accumulated_state/execution_time per step
- **trace_id**: unique identifier per execution for log correlation
- **usage tracking**: automatic token usage tracking (input/output/cached tokens + timing)
- **pipeline constraints**: optional limits (max tokens, max execution time) stop job when exceeded
  - constraints stored in pipeline.definition["constraints"]
  - enforced in two paths: workflow.py (multiplier) and job_processor.py (normal)
  - job status becomes "stopped" with constraint error message
- **pipeline_output**: special field for visualization (any block can set, defaults to assistant or last block's first output)
- **error handling**: structured exceptions with context (BlockNotFoundError, BlockExecutionError, ValidationError)
- **pipeline templates**: pre-configured pipelines for quick start

### stack
- backend: fastapi + aiosqlite + pydantic + jinja2 + pyyaml + litellm + rouge-score
- frontend: react + typescript + primer react + reactflow
- testing: pytest + pytest-asyncio
- tools: uv (python), yarn (js)

### directory structure
```
lib/
  blocks/
    builtin/          # atomic blocks (text_generator, structured_generator, metrics, validators)
    custom/           # experimental blocks
    base.py           # BaseBlock interface
    config.py         # BlockConfigSchema (schema extraction with defaults/enums/field_refs)
    registry.py       # auto-discovery engine
  entities/
    pipeline.py       # ExecutionResult, Constraints, Usage pydantic models
  templates/          # pipeline templates (yaml files)
    __init__.py       # TemplateRegistry class
  errors.py           # custom exception classes
  workflow.py         # Pipeline class (execution + validation + tracing)
  storage.py          # Storage class (crud + migrations)
  template_renderer.py  # Jinja2 template renderer
  job_queue.py        # JobQueue class (in-memory job tracking)
  job_processor.py    # background job processing (usage tracking + constraint enforcement)

frontend/
  src/
    pages/
      Builder.tsx     # visual pipeline builder
      Pipelines.tsx   # pipeline manager
      Generator.tsx   # dataset generation
      Review.tsx      # review records with trace

tests/
  conftest.py         # test configuration (test db, fixtures)
  blocks/             # block unit tests
  test_api.py         # api endpoint tests
  test_workflow.py    # pipeline execution tests
  test_storage_comprehensive.py  # storage crud tests
  test_integration.py # end-to-end tests
  test_error_handling_api.py  # error handling tests
```

## block system

### BaseBlock interface
```python
class BaseBlock:
    name: str              # display name
    description: str       # what it does
    inputs: list[str]      # required input fields
    outputs: list[str]     # declared output fields

    # optional class attributes for UI configuration
    _config_enums: dict[str, list] = {}      # enum dropdowns: {"param": ["opt1", "opt2"]}
    _field_references: list[str] = []        # field dropdowns: ["generated_field", "reference_field"]

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # must return only fields declared in outputs
        pass

    def get_schema(self) -> dict:
        # returns schema with defaults, enums, and field_refs extracted from __init__
        pass
```

### block discovery
- registry scans: `lib/blocks/builtin/`, `lib/blocks/custom/`, `user_blocks/`
- discovers all classes inheriting from BaseBlock
- auto-registers on startup
- no manual registration needed

### builtin blocks

**8 atomic blocks (research blocks removed)**

**generators:**
- **TextGenerator**: generate text using litellm
  - inputs: [] (optional: system, user from data)
  - outputs: assistant, system, user
  - config: model, temperature, max_tokens, system_prompt, user_prompt
  - uses litellm.acompletion for multi-provider LLM access
  - auto-detects ollama: adds "ollama/" prefix and fixes api_base url

- **StructuredGenerator**: generate structured JSON using litellm
  - inputs: [] (optional: user_prompt from data)
  - outputs: generated (dict)
  - config: json_schema, model, temperature, max_tokens, user_prompt
  - uses litellm response_format for JSON mode
  - auto-detects ollama: adds "ollama/" prefix and fixes api_base url

**multipliers:**
- **MarkdownMultiplierBlock**: split markdown into chunks (must be first block)
  - inputs: [] (requires file_content from metadata)
  - outputs: content (per chunk)
  - config: none
  - is_multiplier: true
  - generates N seeds from single input file

**metrics (individual blocks, configurable field names):**
- **DiversityScore**: calculate lexical diversity for text variations
  - inputs: []
  - outputs: diversity_score (float 0-1)
  - config: field_name (default: "assistant")
  - _field_references: ["field_name"]

- **CoherenceScore**: measure text coherence based on sentence structure
  - inputs: []
  - outputs: coherence_score (float 0-1)
  - config: field_name (default: "assistant")
  - _field_references: ["field_name"]

- **RougeScore**: calculate ROUGE score comparing generated vs reference text
  - inputs: []
  - outputs: rouge_score (float 0-1)
  - config: generated_field, reference_field, rouge_type
  - _config_enums: {"rouge_type": ["rouge1", "rouge2", "rougeL"]}
  - _field_references: ["generated_field", "reference_field"]

**validators:**
- **ValidatorBlock**: validates text/assistant against rules
  - inputs: text, assistant (prefers non-empty)
  - outputs: text, valid, assistant

- **JSONValidatorBlock**: parse and validate JSON from any field
  - inputs: * (all accumulated state)
  - outputs: valid (bool), parsed_json (object/null)
  - config: field_name, required_fields, strict

## error handling

### custom exceptions (lib/errors.py)
```python
class PipelineError(Exception):
    """Base exception for all pipeline-related errors"""
    def __init__(self, message: str, detail: dict | None = None):
        self.message = message
        self.detail = detail or {}

class BlockNotFoundError(PipelineError):
    """Raised when a block type is not registered"""
    # detail includes: block_type, available_blocks

class BlockExecutionError(PipelineError):
    """Raised when a block fails during execution"""
    # detail includes: block_type, step, error, input

class ValidationError(PipelineError):
    """Raised when a block returns fields not declared in outputs"""
    # detail includes: block_type, declared_outputs, actual_outputs, extra_fields
```

### error responses
All API errors return structured JSON:
```json
{
  "error": "Block 'LLMBlock' failed at step 2: Connection timeout",
  "detail": {
    "block_type": "LLMBlock",
    "step": 2,
    "error": "Connection timeout",
    "input": {...}
  }
}
```

## pipeline execution

### signature
```python
# normal pipeline (single result)
async def execute(self, initial_data: dict[str, Any]) -> tuple[dict[str, Any], list[dict], str]:
    # returns: (result, trace, trace_id)

# multiplier pipeline (multiple results)
async def execute(self, initial_data: dict[str, Any]) -> list[tuple[dict[str, Any], list[dict], str]]:
    # returns: [(result, trace, trace_id), ...]
```

### multiplier detection
```python
has_multiplier = (
    len(pipeline._block_instances) > 0
    and getattr(pipeline._block_instances[0], "is_multiplier", False)
)
```
multiplier blocks must be first in pipeline and generate multiple seeds from single input

### flow
```python
async def execute(self, initial_data: dict[str, Any]) -> tuple[dict[str, Any], list[dict], str]:
    trace_id = str(uuid.uuid4())
    accumulated_data = initial_data.copy()
    trace = []

    logger.info(f"[{trace_id}] Starting pipeline '{self.name}' with {len(self._block_instances)} blocks")

    for i, block in enumerate(self._block_instances):
        logger.debug(f"[{trace_id}] Executing block {i + 1}/{len(self._block_instances)}: {block_name}")

        start_time = time.time()
        try:
            # 1. execute block with accumulated data
            result = await block.execute(accumulated_data)
            execution_time = time.time() - start_time

            logger.debug(f"[{trace_id}] {block_name} completed in {execution_time:.3f}s")

            # 2. validate output matches declared schema
            self._validate_output(block, result)

            # 3. merge result into accumulated data
            accumulated_data.update(result)

            # 4. set pipeline_output if not already set and this is the last block
            if is_last_block and "pipeline_output" not in accumulated_data:
                if "assistant" in accumulated_data:
                    accumulated_data["pipeline_output"] = accumulated_data["assistant"]
                elif block.outputs:
                    accumulated_data["pipeline_output"] = accumulated_data[block.outputs[0]]

            # 5. capture trace
            trace.append({
                "block_type": block_name,
                "input": block_input,
                "output": result,
                "accumulated_state": accumulated_data.copy(),
                "execution_time": execution_time
            })
        except ValidationError:
            logger.error(f"[{trace_id}] {block_name} validation error at step {i + 1}")
            raise
        except Exception as e:
            logger.error(f"[{trace_id}] {block_name} failed at step {i + 1}: {str(e)}")
            raise BlockExecutionError(...)

    logger.info(f"[{trace_id}] Pipeline '{self.name}' completed successfully")
    return accumulated_data, trace, trace_id
```

### key patterns
- **trace_id**: unique uuid per execution, included in all logs for correlation
- **execution_time**: per-block timing captured in trace
- **accumulated state**: union of all block outputs flows through pipeline
- **output validation**: `actual_keys.issubset(declared_keys)` enforced
- **trace format**: `[{block_type, input, output, accumulated_state, execution_time}, ...]`
- **pipeline_output**: last-wins if multiple blocks set it
- **error context**: BlockExecutionError includes block name, step number, input data

## jinja2 template system

### template renderer (lib/template_renderer.py)
```python
class TemplateRenderer:
    """jinja2-based template renderer with custom filters"""

    def render(self, template_str: str, context: dict[str, Any]) -> str:
        # renders jinja2 template with context
        # supports: variables, conditionals, loops, filters, nested access
```

### supported syntax
```jinja2
# variables
{{ variable }}

# conditionals
{% if condition %}...{% endif %}

# loops
{% for item in list %}{{ item }}{% endfor %}

# filters
{{ variable | upper }}
{{ dict | tojson }}
{{ long_text | truncate(50) }}

# nested access
{{ metadata.field.nested }}
```

### custom filters
- **tojson**: pretty-print dicts/lists as JSON
- **truncate(length)**: truncate strings with ellipsis

### runtime template rendering
- templates in seed files use jinja2 syntax: `{{ variable }}`
- TextGenerator/StructuredGenerator render prompts with current accumulated state
- variables can be modified by blocks before generation
- templates always use latest values from accumulated state

### example flow
```json
{
  "metadata": {
    "role": "assistant",
    "topic": "AI"
  }
}
```
1. initial state: `role = "assistant"`, `topic = "AI"`
2. blocks can modify: `accumulated_state["role"] = "expert"`
3. TextGenerator renders prompt: `"You are an expert. Explain AI."`
4. rendered values saved to record

## pipeline templates

### template registry (lib/templates/__init__.py)
```python
class TemplateRegistry:
    def __init__(self, templates_dir: Path | None = None):
        self.templates_dir = templates_dir or Path(__file__).parent
        self._templates: dict[str, dict[str, Any]] = {}
        self._load_templates()  # loads *.yaml files

    def list_templates(self) -> list[dict[str, Any]]:
        # returns: [{"id": "...", "name": "...", "description": "..."}, ...]

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        # returns template definition with blocks
```

### template format (YAML)
```yaml
name: Template Name
description: What this template does
blocks:
  - type: TextGenerator
    config:
      user_prompt: "Generate text about {{ topic }}"
      temperature: 0.7

  - type: JSONValidatorBlock
    config:
      field_name: "assistant"
      strict: false
```

### built-in templates
- **json_generation**: Extract title and description from text (StructuredGenerator + JSONValidator)
- **text_classification**: Classify text into categories with confidence (StructuredGenerator + JSONValidator)
- **qa_generation**: Generate Q&A pairs from text (TextGenerator + StructuredGenerator + JSONValidator)

## storage

### database schema
```sql
CREATE TABLE pipelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    definition TEXT NOT NULL,  -- json
    constraints TEXT,            -- json (optional: max_total_tokens, max_total_input_tokens, max_total_output_tokens, max_total_cached_tokens, max_total_execution_time)
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL,
    status TEXT NOT NULL,  -- running|completed|failed|cancelled|stopped
    total_seeds INTEGER NOT NULL,
    current_seed INTEGER DEFAULT 0,
    records_generated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    progress REAL DEFAULT 0.0,
    current_block TEXT,
    current_step TEXT,
    usage TEXT,  -- json (total_tokens, total_input_tokens, total_output_tokens, total_cached_tokens, start_time, end_time)
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
);

CREATE TABLE records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    output TEXT NOT NULL,           -- final pipeline output
    metadata TEXT NOT NULL,         -- json (input variables)
    status TEXT NOT NULL,
    pipeline_id INTEGER,
    job_id INTEGER,
    trace TEXT,                     -- json (execution history)
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
```

### key methods

**pipelines:**
- `async def save_pipeline(name, definition) -> int`
- `async def get_pipeline(pipeline_id) -> dict | None`
- `async def list_pipelines() -> list[dict]`
- `async def delete_pipeline(pipeline_id) -> bool`

**jobs:**
- `async def create_job(pipeline_id, total_seeds, status) -> int`
- `async def get_job(job_id) -> dict | None`
- `async def list_jobs(pipeline_id, limit) -> list[dict]`
- `async def update_job(job_id, **updates) -> bool`

**records:**
- `async def save_record(record, pipeline_id, job_id) -> int`
- `async def get_by_id(record_id) -> Record | None`
- `async def get_all(status, limit, offset, job_id) -> list[Record]`
- `async def update_record(record_id, **kwargs) -> bool`
- `async def delete_all_records(job_id) -> int`  # deletes job too if job_id provided
- `async def export_jsonl(status, job_id) -> str`

### migration pattern
- `_migrate_schema()` checks for missing columns via PRAGMA
- adds columns with ALTER TABLE if missing
- called on init_db()

### :memory: handling
- persistent connection stored in `self._conn`
- `_execute_with_connection()` helper manages connection lifecycle

## api endpoints

### blocks
- `GET /api/blocks` - list all registered blocks with schemas

### templates
- `GET /api/templates` - list available pipeline templates
- `POST /api/pipelines/from_template/{template_id}` - create pipeline from template

### pipelines
- `POST /api/pipelines` - create pipeline
- `GET /api/pipelines` - list all pipelines
- `GET /api/pipelines/{id}` - get pipeline by id
- `DELETE /api/pipelines/{id}` - delete pipeline
- `POST /api/pipelines/{id}/execute` - execute pipeline, returns `{result, trace, trace_id}`

### jobs
- `POST /api/generate` - start background job, returns `{job_id}`
- `GET /api/jobs/active` - get currently running job
- `GET /api/jobs/{id}` - get job status by id
- `GET /api/jobs?pipeline_id={id}` - list jobs for pipeline
- `DELETE /api/jobs/{id}` - cancel running job

### records
- `GET /api/records?status={status}&job_id={id}` - list records (supports filtering)
- `GET /api/records/{id}` - get record by id
- `PUT /api/records/{id}` - update record
- `DELETE /api/records?job_id={id}` - delete records (and job if job_id provided)
- `GET /api/export?status={status}&job_id={id}` - export records as jsonl
- `GET /api/export/download?status={status}&job_id={id}` - download export as file

## configuration

### environment variables (config.py)
```python
class Settings:
    LLM_ENDPOINT: str = os.getenv("LLM_ENDPOINT", "http://localhost:11434/api/generate")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/qa_records.db")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
```

### debug mode
When `DEBUG=true`:
- logging level set to DEBUG
- detailed logs include module name
- per-block execution logged with timing
- trace_id included in all logs
- example log: `2025-10-06 10:15:32 [DEBUG] lib.workflow: [a1b2c3d4-...] LLMBlock completed in 3.124s`

## testing

### test database isolation
- environment variable set in `tests/conftest.py` before any imports
- `DATABASE_PATH=data/test_qa_records.db`
- session fixture deletes test db before and after all tests
- production database (`data/qa_records.db`) never touched by tests

### test fixtures
```python
# conftest.py
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """Clean up test database before and after test session"""
    test_db = Path("data/test_qa_records.db")
    if test_db.exists():
        test_db.unlink()
    yield
    if test_db.exists():
        test_db.unlink()

@pytest.fixture(scope="function")
def client():
    """Create test client with lifespan handling"""
    from app import app
    with TestClient(app) as client:
        yield client
```

### test structure
- **blocks/**: unit tests for each block
- **test_api.py**: api endpoint tests
- **test_workflow.py**: pipeline execution tests
- **test_storage_comprehensive.py**: storage crud tests
- **test_integration.py**: end-to-end scenarios
- **test_error_handling_api.py**: error handling tests

### key patterns
- use `@pytest.mark.asyncio` for async tests
- `pipeline.execute()` returns `(result, trace, trace_id)` tuple
- mock Generator with `@patch('lib.generator.Generator.generate')`
- test database automatically created/cleaned up
- client fixture handles app lifespan events

### running tests
```bash
# all tests
uv run pytest tests/ -v

# specific suite
uv run pytest tests/blocks/ -v

# with coverage
uv run pytest --cov=lib --cov=app tests/
```

## current status

**production ready** - full-stack data generation platform with visual pipeline builder

### core features
- 8 atomic blocks: TextGenerator, StructuredGenerator, MarkdownMultiplierBlock, ValidatorBlock, JSONValidatorBlock, DiversityScore, CoherenceScore, RougeScore
- block auto-discovery from builtin/, custom/, user_blocks/
- visual reactflow pipeline editor with drag-and-drop
- jinja2 template rendering with custom filters
- 3 yaml pipeline templates
- background job processing with real-time progress tracking
- full crud api for pipelines, jobs, records
- incremental record visibility during execution
- job-scoped operations (delete, export, filter)
- execution trace with timing and accumulated state
- structured error handling with context
- cross-platform sqlite storage with migrations
- 88 passing tests

### ui
- 3 pages: Pipelines (templates + editor), Generator (upload + progress), Review (cards + trace)
- primer react components with dark mode
- real-time job progress (2-second polling)
- accumulated state visualization per block
- validation before pipeline save

---

## common tasks

### adding new block
1. create file in `lib/blocks/custom/myblock.py`
2. inherit from BaseBlock
3. define name, description, inputs, outputs
4. implement `async def execute()`

```python
from lib.blocks.base import BaseBlock
from typing import Any

class MyBlock(BaseBlock):
    name = "My Block"
    description = "Does something useful"
    inputs = ["text"]
    outputs = ["result"]

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        return {"result": data["text"].upper()}
```

### adding pipeline template
1. create yaml file in `lib/templates/my_template.yaml`
2. define name, description, blocks

```yaml
name: My Template
description: What it does
blocks:
  - type: TextGenerator
    config:
      user_prompt: "Generate about {{ topic }}"
      temperature: 0.7

  - type: JSONValidatorBlock
    config:
      field_name: "assistant"
```

auto-discovered on startup, available via `GET /api/templates`

### seed file format
seed files provide metadata variables for pipeline execution:

```json
[
  {
    "repetitions": 2,
    "metadata": {
      "system": "You are a {{ role }} who specializes in {{ domain }}.",
      "user": "Explain {{ topic }} in simple terms.",
      "role": "teacher",
      "domain": "physics",
      "topic": "gravity"
    }
  }
]
```

**flow:**
1. metadata loaded as initial accumulated state
2. pipeline blocks execute, can access and modify variables
3. TextGenerator/StructuredGenerator render prompts with current accumulated state
4. pipeline_output extracted from final trace's accumulated_state
5. record saved with output field (extracted from pipeline_output)

### adding storage method
```python
async def my_method(self, param: str) -> Any:
    async def _operation(db):
        cursor = await db.execute("SELECT * FROM table WHERE field = ?", (param,))
        return await cursor.fetchone()
    return await self._execute_with_connection(_operation)
```

### debugging with trace_id
1. enable debug mode: `DEBUG=true` in .env
2. execute pipeline, note trace_id in response
3. grep logs for trace_id: `grep "a1b2c3d4" logs.txt`
4. see full execution flow with timing

## important notes

### output validation
- blocks MUST return only declared outputs
- extra fields cause ValidationError
- enforced at runtime in pipeline.execute()
- error includes: block_type, declared_outputs, actual_outputs, extra_fields

### pipeline_output
- any block can set it (last one wins)
- defaults to assistant field if not set
- defaults to last block's first output if no assistant

### accumulated state
- union of all block outputs
- flows through entire pipeline
- each block sees all previous outputs

### trace format
```python
{
    "block_type": "ValidatorBlock",
    "input": {"assistant": "hello"},
    "output": {"valid": True, "assistant": "hello"},
    "accumulated_state": {"assistant": "hello", "valid": True, ...},
    "execution_time": 0.001
}
```

### error handling
- all errors return structured JSON with error + detail
- BlockNotFoundError includes available_blocks list
- BlockExecutionError includes block_type, step, error, input
- ValidationError includes declared vs actual outputs

### debug logging
- trace_id correlates logs with API responses
- execution_time per block in trace
- logger.debug shows block execution flow
- logger.error shows failures with context

### test database
- tests use `data/test_qa_records.db`
- production uses `data/qa_records.db`
- automatic cleanup before/after tests
- no manual intervention needed

## debugging

### common issues
- **block not discovered**: check file in builtin/custom/user_blocks, check BaseBlock inheritance
- **output validation error**: check block returns only declared outputs
- **storage method error**: use _execute_with_connection helper
- **test async fixture error**: use @pytest.mark.asyncio
- **test database not cleaned**: check conftest.py fixture running

### useful commands
```bash
# check registered blocks
curl http://localhost:8000/api/blocks | jq

# list templates
curl http://localhost:8000/api/templates | jq

# create pipeline from template
curl -X POST http://localhost:8000/api/pipelines/from_template/text_generation

# execute pipeline
curl -X POST http://localhost:8000/api/pipelines/1/execute \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}' | jq

# check trace_id in logs
grep "a1b2c3d4" logs.txt
```

## kiss principles
- minimal abstraction layers
- flat structure over deep nesting
- explicit over implicit
- simple composition over inheritance
- keep it simple, stupid
