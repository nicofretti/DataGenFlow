> **Important**
> The file should reflect the current backend status for remembering purposes
> to describe the actual api design, endpoints and implementation decisions. It must be technical and include the minimal number of words

# backend reference

## stack
- fastapi (web framework)
- aiosqlite (async database)
- pydantic (validation)
- jinja2 (template rendering)
- pyyaml (template files)
- litellm (multi-provider llm calls)

## structure
```
lib/
  blocks/
    builtin/              # stable blocks
      llm.py              # LLMBlock
      validator.py        # ValidatorBlock, JSONValidatorBlock
      output.py           # OutputBlock
    custom/               # experimental blocks
    base.py               # BaseBlock interface
    registry.py           # auto-discovery
  templates/              # yaml pipeline templates
    __init__.py           # TemplateRegistry
  errors.py               # PipelineError, BlockNotFoundError, etc
  workflow.py             # Pipeline class
  storage.py              # Storage class (sqlite crud)
  generator.py            # Generator class (llm wrapper)
  template_renderer.py    # Jinja2 renderer
  job_queue.py            # JobQueue (in-memory)
  job_processor.py        # background job processing

app.py                    # fastapi app, lifespan, endpoints
config.py                 # Settings (env vars)
```

## api endpoints

### blocks
- `GET /api/blocks` - list registered blocks with schemas

### templates
- `GET /api/templates` - list pipeline templates
- `POST /api/pipelines/from_template/{template_id}` - create from template

### pipelines
- `POST /api/pipelines` - create pipeline
- `GET /api/pipelines` - list all
- `GET /api/pipelines/{id}` - get by id
- `DELETE /api/pipelines/{id}` - delete
- `POST /api/pipelines/{id}/execute` - execute, returns {result, trace, trace_id}

### jobs
- `POST /api/generate` - start job (file upload), returns {job_id}
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

## database schema

```sql
CREATE TABLE pipelines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    definition TEXT NOT NULL,  -- json
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    total_seeds INTEGER NOT NULL,
    current_seed INTEGER DEFAULT 0,
    records_generated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    progress REAL DEFAULT 0.0,
    current_block TEXT,
    current_step TEXT,
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
    trace TEXT,              -- json
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
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
```

### debug mode
when DEBUG=true:
- logging level: DEBUG
- logs include: trace_id, module name, execution timing
- example: `[a1b2c3d4] LLMBlock completed in 3.124s`

## block system

### BaseBlock interface
```python
class BaseBlock:
    name: str
    description: str
    inputs: list[str]
    outputs: list[str]

    # optional ui metadata
    _config_enums: dict[str, list[str]]      # enum dropdown options
    _field_references: list[str]              # field reference dropdowns
    _config_descriptions: dict[str, str]      # inline help text

    async def execute(data: dict) -> dict:
        # must return only declared outputs
        pass

    @classmethod
    def get_schema() -> dict:
        # returns schema for ui (auto-generated from __init__)
        pass
```

### block config schema
- extracts from `__init__` signature using inspect
- type hints → json schema types (str, int, float, bool, dict, list)
- dict[str, Any] → type: "object" (json editor in ui)
- list → type: "array"
- default values included in schema
- `_config_enums` → enum arrays in schema
- `_field_references` → isFieldReference: true in schema
- `_config_descriptions` → description fields in schema

### builtin blocks
- **TextGenerator**: generates text via litellm
  - inputs: []
  - outputs: assistant, system, user
  - config: model, temperature, max_tokens, system_prompt, user_prompt
- **StructuredGenerator**: generates json via litellm with schema
  - inputs: []
  - outputs: generated
  - config: json_schema (dict), model, temperature, max_tokens, user_prompt
- **MarkdownMultiplierBlock**: splits markdown into chunks (must be first block)
  - inputs: [] (requires file_content from metadata)
  - outputs: content (per chunk)
  - config: none
  - is_multiplier: true
  - generates N seeds from single input
- **ValidatorBlock**: validates text length
  - inputs: text, assistant
  - outputs: text, valid, assistant
  - config: min_length, max_length, forbidden_words
- **JSONValidatorBlock**: parses json from any field (handles both strings and parsed objects)
  - inputs: * (all accumulated state)
  - outputs: valid, parsed_json
  - config: field_name, required_fields, strict
- **OutputBlock**: formats output with jinja2
  - inputs: * (all accumulated state)
  - outputs: pipeline_output
  - config: format_template
- **DiversityScore**: calculates lexical diversity
  - inputs: []
  - outputs: diversity_score
  - config: field_name
- **CoherenceScore**: calculates text coherence
  - inputs: []
  - outputs: coherence_score
  - config: field_name
- **RougeScore**: calculates rouge score
  - inputs: []
  - outputs: rouge_score
  - config: generated_field, reference_field, rouge_type

### block discovery
- registry scans: lib/blocks/builtin/, lib/blocks/custom/, user_blocks/
- auto-discovers classes inheriting BaseBlock
- no manual registration needed

## jinja2 templates

### runtime rendering
- LLMBlock renders system/user templates before llm call
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
3. LLMBlock renders templates with current state
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
    # startup
    await storage.init_db()
    job_processor.start()

    yield

    # shutdown
    job_processor.stop()
```

## cors
- allows all origins (*)
- allows credentials
- exposes content-disposition header (for downloads)

## static files
- frontend built to frontend/dist
- served at /
- spa fallback for client-side routing
