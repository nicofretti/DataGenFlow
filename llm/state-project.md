> **Important**
> The file should reflect the current status of the project for remembering purposes
> to describe the actual design, decisions and implementations. It must be technical and include the minimal number of words

# project state

## architecture

### core concepts
- **block pipelines**: compose workflows from reusable blocks
- **sequential execution**: blocks in order, accumulated state flows through
- **output validation**: blocks return only declared outputs (runtime enforced)
- **trace**: full history (input/output/accumulated_state/execution_time per step)
- **trace_id**: unique per execution for log correlation
- **BlockExecutionContext**: type-safe context (job_id=0 for API, job_id>0 for jobs)
- **usage tracking**: automatic token tracking (input/output/cached + timing)
- **constraints**: optional limits (tokens, time) stop job when exceeded
- **pipeline_output**: visualization field (defaults to assistant or last block output)
- **error handling**: structured exceptions with context

### stack
backend: fastapi + aiosqlite + pydantic + jinja2 + litellm + rouge-score
frontend: react + typescript + primer + reactflow + monaco + shadcn/ui
testing: pytest + pytest-asyncio
tools: uv (python), yarn (js)

### directory structure
```
lib/
  blocks/
    builtin/          # 14 blocks (generators, multiplier, validators, metrics, seeders, observability, utilities)
    custom/           # experimental
    base.py           # BaseBlock interface
    config.py         # schema extraction
    registry.py       # auto-discovery
  entities/           # pydantic models (BlockExecutionContext, Pipeline, Job, Record, etc)
  templates/          # yaml templates + TemplateRegistry
  errors.py           # structured exceptions
  workflow.py         # Pipeline execution + validation + tracing
  storage.py          # sqlite crud + migrations
  template_renderer.py  # jinja2 renderer
  job_queue.py        # in-memory tracking
  job_processor.py    # background processing + usage + constraints
  llm_config.py       # LLMConfigManager

frontend/src/
  pages/              # Pipelines, Generator, Review, Settings
  components/         # GlobalJobIndicator, pipeline-editor/, settings/, ui/

.claude/
  skills/
    implementing-datagenflow-blocks/  # guide for creating new blocks
    debugging-pipelines/              # systematic debugging workflow for pipeline issues

tests/
  conftest.py         # test db setup
  blocks/             # block unit tests
  integration/        # integration tests with external services
  e2e/                # browser-based end-to-end tests (playwright)
  test_*.py           # api, workflow, storage, constraints, cancellation
```

## execution model

### BlockExecutionContext
type-safe context passed to all blocks (lib/entities/block_execution_context.py)

```python
class BlockExecutionContext(BaseModel):
    trace_id: str                      # unique execution id
    job_id: int = 0                    # 0=API, >0=job
    pipeline_id: int
    accumulated_state: dict[str, Any]  # previous outputs
    usage: Usage                       # token tracking
    trace: list[dict[str, Any]]        # execution history
    constraints: Constraints           # limits
```

**benefits**: no None checks, type safety, sentinel job_id, single source of truth
**validators**: Job.usage None→{}, Record.trace None→[]

## block system

### BaseBlock interface
```python
class BaseBlock:
    name: str
    description: str
    inputs: list[str]
    outputs: list[str]
    _config_enums: dict[str, list] = {}      # dropdown options
    _field_references: list[str] = []        # field dropdowns
    _config_formats: dict[str, str] = {}     # json schema format hints (e.g., "json-or-template")

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        # must return only declared outputs
        pass

    def get_schema() -> dict:
        # auto-extracts from __init__ signature
        pass
```

### builtin blocks (14 total)

**seeders:**
- StructureSampler: statistical sampler (target_count, categorical_fields, numeric_fields, dependencies, seed) → * (skeletons + hints)

**generators:**
- TextGenerator: litellm text (system_prompt, user_prompt, model, temp, max_tokens) → assistant, system, user
- StructuredGenerator: litellm json (json_schema, user_prompt, model, temp, max_tokens) → generated
- SemanticInfiller: complete skeletons (fields_to_generate, model, temperature, max_tokens) → * (merged skeleton + generated)

**multipliers:**
- MarkdownMultiplierBlock: split markdown (file_content required, is_multiplier: true) → content (per chunk)

**validators:**
- ValidatorBlock: text rules (min_length, max_length, forbidden_words) → text, valid, assistant
- JSONValidatorBlock: parse json (field_name, required_fields, strict) → valid, parsed_json
- DuplicateRemover: embedding similarity (similarity_threshold, comparison_fields, embedding_model) → generated_samples (enriched with is_duplicate, similarity_to_seeds, similarity_to_generated)

**metrics:**
- DiversityScore: lexical diversity (field_name) → diversity_score
- CoherenceScore: text coherence (field_name) → coherence_score
- RougeScore: rouge comparison (generated_field, reference_field, rouge_type) → rouge_score
- RagasMetrics: evaluate QA using RAGAS metrics (question_field, answer_field, etc.) → ragas_scores

**utilities:**
- FieldMapper: create fields from Jinja2 expressions (mappings) → * (dynamic based on mappings)

**observability:**
- LangfuseBlock: logging (public_key, secret_key, host, session_id) → langfuse_trace_url

### discovery
registry scans lib/blocks/builtin/, lib/blocks/custom/, user_blocks/ for BaseBlock subclasses

## error handling

### exceptions (lib/errors.py)
```python
class PipelineError(Exception):
    message: str
    detail: dict | None

class BlockNotFoundError(PipelineError):  # detail: block_type, available_blocks
class BlockExecutionError(PipelineError):  # detail: block_type, step, error, input
class ValidationError(PipelineError):      # detail: declared_outputs, actual_outputs, extra_fields
```

all API errors return: `{"error": "message", "detail": {...}}`

## pipeline execution

### signature
```python
# normal: single result
async def execute(initial_data: dict) -> tuple[dict, list[dict], str]:
    return (result, trace, trace_id)

# multiplier: multiple results
async def execute(initial_data: dict) -> list[tuple[dict, list[dict], str]]:
    return [(result, trace, trace_id), ...]
```

multiplier detection: `getattr(first_block, "is_multiplier", False)`

### flow
1. generate trace_id (uuid)
2. copy initial_data to accumulated_data
3. for each block:
   - execute with accumulated_data
   - validate output matches declared outputs
   - merge result into accumulated_data
   - set pipeline_output if last block and not set
   - append to trace
4. return (accumulated_data, trace, trace_id)

multiplier flow: first block generates N seeds, execute remaining blocks per seed, save incrementally

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

## jinja2 templates

### renderer (lib/template_renderer.py)
renders jinja2 with custom filters (tojson, truncate)
supports: variables `{{ var }}`, conditionals `{% if %}`, loops `{% for %}`, filters `{{ var | upper }}`

### runtime rendering
- seed metadata loaded as initial accumulated_state
- blocks can modify variables
- TextGenerator/StructuredGenerator render prompts with current state
- templates always use latest values

### example
```json
{"metadata": {"role": "assistant", "topic": "AI"}}
```
→ blocks modify role to "expert"
→ TextGenerator renders: "You are an expert. Explain AI."

## pipeline templates

### TemplateRegistry (lib/templates/)
loads *.yaml from lib/templates/, auto-discovered on startup

### format
```yaml
name: Template Name
description: What it does
blocks:
  - type: TextGenerator
    config:
      user_prompt: "Generate text about {{ topic }}"
      temperature: 0.7
```

### built-in (4 templates)
- **json_generation**: extract title/description (StructuredGenerator + JSONValidator)
- **text_classification**: classify with confidence (StructuredGenerator + JSONValidator)
- **qa_generation**: generate Q&A pairs (TextGenerator + StructuredGenerator + JSONValidator)
- **data_augmentation**: synthetic records from samples (StructureSampler + SemanticInfiller + DuplicateRemover)

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

### structure
blocks/, integration/, test_api.py, test_workflow.py, test_storage.py, test_constraints.py, test_job_cancellation.py

### patterns
- DATABASE_PATH=data/test_qa_records.db (isolated from production)
- session fixture: cleanup before/after tests
- @pytest.mark.asyncio for async tests
- pipeline.execute() returns (result, trace, trace_id)

### run
`uv run pytest tests/ -v` or `uv run pytest --cov=lib --cov=app tests/`

## status

production-ready full-stack data generation platform

### features
- 14 blocks (seeders, generators, multiplier, validators, metrics, observability, utilities)
- auto-discovery from builtin/custom/user_blocks
- reactflow visual editor with drag-drop
- jinja2 templates + 4 yaml templates
- background jobs with real-time progress
- incremental record visibility
- job-scoped delete/export/filter
- execution trace with timing
- structured errors with context
- sqlite with migrations
- type-safe BlockExecutionContext
- LLM/embedding config management (multi-provider)
- 4 pages: Pipelines, Generator, Review, Settings
- primer + dark mode
- accumulated state visualization
- constraint enforcement (tokens, time)

## common tasks

### add block
```python
# lib/blocks/custom/myblock.py
from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext

class MyBlock(BaseBlock):
    name, description, category, inputs, outputs = ...
    async def execute(self, context: BlockExecutionContext) -> dict:
        return {"result": context.get_state("text", "").upper()}
```

### add template
```yaml
# lib/templates/my_template.yaml
name: My Template
description: What it does
blocks:
  - type: TextGenerator
    config:
      user_prompt: "Generate {{ topic }}"
```

### seed format
```json
[{"repetitions": 2, "metadata": {"system": "You are {{ role }}", "role": "teacher"}}]
```
metadata → initial accumulated_state → blocks execute → templates render → pipeline_output extracted

### debug with trace_id
DEBUG=true, grep logs for trace_id, see execution flow with timing

## important notes

### output validation
blocks MUST return only declared outputs, extra fields cause ValidationError (enforced at runtime)

### pipeline_output
any block can set it (last wins), defaults to assistant or last block's first output

### accumulated state
union of all block outputs, flows through pipeline, each block sees all previous outputs

### trace format
`{block_type, input, output, accumulated_state, execution_time}`

### job cancellation
4 checkpoints: normal pipeline (before each block), multiplier (before each seed + before each block within seed), job processor (after inner loop)

### debug logging
trace_id correlates logs with API responses, execution_time per block in trace

### test database
tests use data/test_qa_records.db, production uses data/qa_records.db, automatic cleanup

## kiss principles
minimal abstraction, flat structure over nesting, explicit over implicit, simple composition over inheritance
