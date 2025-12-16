> **Important**
> The file should reflect the current backend status for remembering purposes
> to describe the actual api design, endpoints and implementation decisions. It must be technical and include the minimal number of words

# backend state

## stack
fastapi + aiosqlite + pydantic + jinja2 + pyyaml + litellm + rouge-score

## structure
```
lib/
  blocks/
    builtin/              # 9 blocks: text_generator, structured_generator, validator,
                          # json_validator, diversity_score, coherence_score,
                          # rouge_score, markdown_multiplier, langfuse
    custom/               # user experimental blocks
    base.py               # BaseBlock interface
    config.py             # schema extraction from __init__
    registry.py           # auto-discovery from builtin/custom/user_blocks
  entities/               # pydantic models
    block_execution_context.py, pipeline.py, api.py, database.py,
    job.py, record.py, llm_config.py
  templates/              # yaml templates + TemplateRegistry
  errors.py               # PipelineError, BlockNotFoundError, BlockExecutionError, ValidationError
  workflow.py             # Pipeline execution + validation + tracing
  storage.py              # sqlite crud + migrations
  template_renderer.py    # jinja2 with custom filters
  job_queue.py            # in-memory job tracking
  job_processor.py        # background processing + usage tracking + constraints
  llm_config.py           # LLMConfigManager
  constants.py            # RECORD_UPDATABLE_FIELDS
app.py                    # endpoints + lifespan
config.py                 # env Settings
```

## api endpoints

### core
- `GET /health` - health check
- `GET /api/langfuse/status` - langfuse integration status

### blocks
- `GET /api/blocks` - list registered blocks with schemas

### templates
- `GET /api/templates` - list pipeline templates
- `POST /api/pipelines/from_template/{template_id}` - create from template

### pipelines
- `POST /api/pipelines` - create pipeline
- `GET /api/pipelines` - list all
- `GET /api/pipelines/{id}` - get by id
- `PUT /api/pipelines/{id}` - update pipeline
- `DELETE /api/pipelines/{id}` - delete
- `POST /api/pipelines/{id}/execute` - execute, returns {result, trace, trace_id}
- `GET /api/pipelines/{id}/accumulated_state_schema` - get required fields
- `PUT /api/pipelines/{id}/validation_config` - update validation config

### jobs
- `POST /api/generate` - start job (file upload), returns {job_id}
- `POST /api/generate_from_file` - legacy endpoint
- `GET /api/jobs/active` - get running job
- `GET /api/jobs/{id}` - get job status
- `GET /api/jobs?pipeline_id={id}` - list jobs for pipeline
- `DELETE /api/jobs/{id}` - cancel + delete job

### records
- `GET /api/records?status={s}&job_id={j}` - list records
- `GET /api/records/{id}` - get by id
- `PUT /api/records/{id}` - update status/output
- `DELETE /api/records?job_id={id}` - delete records (and job if job_id provided)
- `GET /api/export?status={s}&job_id={j}` - export jsonl string
- `GET /api/export/download?status={s}&job_id={j}` - download file

### seeds
- `POST /api/seeds/validate` - validate seeds against pipeline requirements

### llm config
- `GET /api/llm-models` - list llm configs
- `GET /api/llm-models/{name}` - get config
- `POST /api/llm-models` - create config
- `PUT /api/llm-models/{name}` - update config
- `DELETE /api/llm-models/{name}` - delete config
- `POST /api/llm-models/test` - test connection

### embedding config
- `GET /api/embedding-models` - list embedding configs
- `GET /api/embedding-models/{name}` - get config
- `POST /api/embedding-models` - create config
- `PUT /api/embedding-models/{name}` - update config
- `DELETE /api/embedding-models/{name}` - delete config
- `POST /api/embedding-models/test` - test connection

## database schema

```sql
CREATE TABLE pipelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    definition TEXT NOT NULL,  -- json: {blocks: [{type, config}], constraints: {...}}
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
    usage TEXT,  -- json: {total_tokens, total_input_tokens, total_output_tokens, total_cached_tokens, start_time, end_time}
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
);

CREATE TABLE records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    output TEXT NOT NULL,
    metadata TEXT NOT NULL,  -- json
    status TEXT NOT NULL,
    pipeline_id INTEGER,
    job_id INTEGER,
    trace TEXT,  -- json: [{block_type, input, output, accumulated_state, execution_time}]
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE TABLE llm_models (
    name TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    api_base TEXT,
    api_key TEXT,
    is_default INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE embedding_models (
    name TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    api_base TEXT,
    api_key TEXT,
    is_default INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

## key classes

### Storage (lib/storage.py)
**methods:**
- pipelines: save_pipeline, get_pipeline, list_pipelines, delete_pipeline
- jobs: create_job, get_job, list_jobs, update_job, delete_job
- records: save_record, get_by_id, get_all, update_record, delete_all_records, export_jsonl

**patterns:**
- _execute_with_connection helper (async with for temp connections, commit on persistent)
- migration via _migrate_schema (checks columns with PRAGMA)
- persistent connection stored in self._conn

### Pipeline (lib/workflow.py)
**signature:**
```python
# normal pipeline (single result)
async def execute(initial_data: dict) -> tuple[dict, list[dict], str]:
    # returns (result, trace, trace_id)

# multiplier pipeline (multiple results)
async def execute(initial_data: dict) -> list[tuple[dict, list[dict], str]]:
    # returns [(result, trace, trace_id), ...]
```

**multiplier detection:**
```python
has_multiplier = (
    len(pipeline._block_instances) > 0
    and getattr(pipeline._block_instances[0], "is_multiplier", False)
)
```

**normal flow:**
1. generate trace_id (uuid)
2. copy initial_data to accumulated_data
3. for each block:
   - execute with accumulated_data
   - validate output matches declared outputs
   - merge result into accumulated_data
   - set pipeline_output if last block and not set
   - append to trace
4. return (accumulated_data, trace, trace_id)

**multiplier flow:**
1. first block (multiplier) generates N seeds
2. set total_seeds in job tracking
3. for each seed:
   - generate new trace_id
   - execute remaining blocks sequentially
   - save record immediately to database (workflow.py:260-265)
   - increment records_generated counter (workflow.py:267-272)
   - update current_seed, progress, current_block, current_step
   - increment records_failed on failure, continue processing
4. return list of (result, trace, trace_id) tuples

**trace format:**
```python
{
    "block_type": "LLMBlock",
    "input": {...},
    "output": {...},
    "accumulated_state": {...},
    "execution_time": 0.5
}
```

### JobQueue (lib/job_queue.py)
- in-memory queue: Dict[int, JobStatus]
- thread-safe operations with asyncio.Lock
- tracks: job_id, status, current_seed, current_block, current_step
- auto-cleanup: keep last 10 jobs per pipeline

### JobProcessor (lib/job_processor.py)
- background task runs in asyncio thread
- processes seeds sequentially per job
- detects multiplier pipelines via is_multiplier attribute
- for multipliers: workflow saves records incrementally (real-time visibility)
- for normal pipelines: processor saves records after execution
- updates job progress in database + memory
- handles errors per seed (continues on failure)
- updates records_generated, records_failed counts
- sets job status to completed/failed on finish

### Generator (lib/generator.py)
**generate method:**
```python
async def generate(prompt: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
    # calls LLM_ENDPOINT with httpx
    # returns generated text
```

### TemplateRenderer (lib/template_renderer.py)
- jinja2 environment with custom filters
- render method: `render(template_str: str, context: dict) -> str`
- custom filters: tojson, truncate

### TemplateRegistry (lib/templates/__init__.py)
- loads *.yaml files from lib/templates/
- loads seed files: seed_{template_id}.json or seed_{template_id}.md
- markdown seeds: wrapped in [{"repetitions": 1, "metadata": {"file_content": "..."}}]
- list_templates returns [{id, name, description, example_seed}]
- get_template returns full definition with blocks

## error handling

### custom exceptions (lib/errors.py)
```python
class PipelineError(Exception):
    message: str
    detail: dict | None

class BlockNotFoundError(PipelineError):
    # detail: block_type, available_blocks

class BlockExecutionError(PipelineError):
    # detail: block_type, step, error, input

class ValidationError(PipelineError):
    # detail: block_type, declared_outputs, actual_outputs, extra_fields
```

### api error responses
all errors return structured json:
```json
{
  "detail": "error message with context"
}
```

improved error messages:
- "Only JSON files are accepted. Please upload a .json file."
- "The JSON file is invalid: {error}. Please check your file syntax."
- "Seed {i} is missing the required 'metadata' field."

## job system

### job creation
1. `POST /api/generate` receives file + pipeline_id
2. validates json, creates job in database
3. adds job to JobQueue (in-memory)
4. starts JobProcessor if not running
5. returns {job_id}

### job processing
1. JobProcessor polls queue for pending jobs
2. loads pipeline + seeds
3. detects multiplier via is_multiplier attribute
4. for each seed:
   - renders templates with metadata
   - executes pipeline (normal or multiplier)
   - saves record(s) (success/failure)
   - updates job progress (current_seed, total_seeds, progress, current_block, current_step)
   - increments records_generated on success
   - increments records_failed on failure, continues processing
5. sets job completed_at on finish
6. only 1 concurrent job allowed

### job status tracking
- database: persistent storage with progress, current_seed, total_seeds, records_generated, records_failed
- memory: JobQueue for fast access during processing
- workflow: updates tracking fields in real-time for multipliers
- frontend: polls GET /api/jobs/{id} every 2 seconds for live updates
- GET /api/jobs/active returns currently running job

### job cleanup
- keep last 10 jobs per pipeline
- older jobs auto-deleted from memory
- database jobs persist (manual delete via api)

### job cancellation
cancellation stops processing at 4 checkpoint locations to prevent background execution from continuing:

**normal pipeline (workflow.py:126-137):**
- checks job status before each block execution
- returns partial result with trace if cancelled

**multiplier pipeline - between seeds (workflow.py:438-443):**
- checks job status before processing each seed
- breaks from seed loop if cancelled

**multiplier pipeline - between blocks (workflow.py:312-317):**
- checks job status before executing each block within seed
- returns None to signal cancellation

**job processor - after repetitions (job_processor.py:310-318):**
- checks job status after inner loop (repetitions) completes
- prevents continuing to next seed when cancelled
- critical fix: without this check, cancellation only broke from inner loop but continued processing remaining seeds

when cancelled, job status becomes "cancelled" and processing stops immediately at next checkpoint.

## configuration (config.py)

```python
class Settings:
    LLM_ENDPOINT: str       # default: http://localhost:11434/api/generate
    LLM_API_KEY: str        # default: ""
    LLM_MODEL: str          # default: "llama3"
    DATABASE_PATH: str      # default: data/qa_records.db
    HOST: str               # default: 0.0.0.0
    PORT: int               # default: 8000
    DEBUG: bool             # default: false
    LANGFUSE_PUBLIC_KEY: str   # optional
    LANGFUSE_SECRET_KEY: str   # optional
    LANGFUSE_HOST: str         # default: https://cloud.langfuse.com
```

debug mode: logging.DEBUG, detailed logs with trace_id, execution timing per block

## block system

### BaseBlock interface
```python
from lib.entities.block_execution_context import BlockExecutionContext

class BaseBlock:
    name: str
    description: str
    category: str  # generators, validators, metrics, seeders, general
    inputs: list[str]
    outputs: list[str]

    # optional ui metadata
    _config_enums: dict[str, list[str]]      # enum dropdown options
    _field_references: list[str]              # field reference dropdowns
    _config_descriptions: dict[str, str]      # inline help text

    async def execute(context: BlockExecutionContext) -> dict:
        # receives typed execution context instead of plain dict
        # must return only declared outputs
        pass

    @classmethod
    def get_config_schema() -> dict:
        # returns config schema for ui (auto-generated from __init__)
        pass

    @classmethod
    def get_schema() -> dict:
        # returns full schema (inputs, outputs, config, category, is_multiplier)
        pass
```

### block config schema
- extracts from `__init__` signature using inspect (via BlockConfigSchema.get_config_schema)
- type hints → json schema types (str, int, float, bool, dict, list)
- dict[str, Any] → type: "object" (json editor in ui)
- list → type: "array"
- default values included in schema
- `_config_enums` → enum arrays in schema
- `_field_references` → isFieldReference: true in schema
- `_config_descriptions` → description fields in schema

### builtin blocks
- **TextGenerator**: text via litellm (system_prompt, user_prompt, model, temperature, max_tokens)
  - outputs: assistant, system, user
- **StructuredGenerator**: json via litellm (json_schema, user_prompt, model, temperature, max_tokens)
  - outputs: generated
- **MarkdownMultiplierBlock**: split markdown into chunks (is_multiplier: true, must be first)
  - outputs: content (per chunk)
- **ValidatorBlock**: validate text (min_length, max_length, forbidden_words)
  - outputs: text, valid, assistant
- **JSONValidatorBlock**: parse json from field (field_name, required_fields, strict)
  - outputs: valid, parsed_json
- **DiversityScore**: lexical diversity (field_name)
  - outputs: diversity_score
- **CoherenceScore**: text coherence (field_name)
  - outputs: coherence_score
- **RougeScore**: rouge comparison (generated_field, reference_field, rouge_type)
  - outputs: rouge_score
- **LangfuseBlock**: observability logging (public_key, secret_key, host, session_id)
  - outputs: langfuse_trace_url

### block discovery
- registry scans: lib/blocks/builtin/, lib/blocks/custom/, user_blocks/
- auto-discovers classes inheriting BaseBlock
- no manual registration needed

### jinja2 templates

### runtime rendering
- TextGenerator/StructuredGenerator render system/user templates before llm call
- uses accumulated_data as context
- supports: variables, conditionals, loops, filters
- custom filters: tojson, truncate

### seed file format
```json
[
  {
    "repetitions": 2,
    "metadata": {
      "system": "You are a {{ role }}.",
      "user": "Explain {{ topic }}.",
      "role": "teacher",
      "topic": "gravity"
    }
  }
]
```

### flow
1. metadata loaded as initial accumulated_data
2. blocks can modify variables
3. TextGenerator/StructuredGenerator renders templates with current state
4. pipeline_output extracted from final accumulated_state

## constraint enforcement

pipelines support optional execution limits:
- max_total_tokens: total tokens (input + output + cached)
- max_total_input_tokens: input tokens only
- max_total_output_tokens: output tokens only
- max_total_cached_tokens: cached tokens only
- max_total_execution_time: elapsed seconds

**enforcement:**
- constraints defined in pipeline.definition["constraints"]
- checked after each seed execution
- cumulative usage tracked across all seeds
- job stops with status="stopped" when exceeded

**two code paths:**
- multiplier pipelines: workflow.py:420-437 checks after each generated seed
- normal pipelines: job_processor.py:279-294 checks after each execution
- both use Constraints.is_exceeded() method for consistency

**usage tracking:**
- Usage class in lib/entities/pipeline.py
- tracks: input_tokens, output_tokens, cached_tokens, start_time, end_time
- stored in jobs.usage as JSON
- accumulated_usage updated after each block execution

## lifespan (app.py)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await storage.init_db()
    # configure langfuse if credentials set
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        litellm.success_callback = ["langfuse"]
    yield
    await storage.close()
```

cors: allow all origins (*), allow credentials, expose content-disposition
static: frontend/dist served at /, spa fallback for routing
