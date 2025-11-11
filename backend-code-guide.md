# Backend Code Guide - DataGenFlow

**version**: 1.0
**focus**: keep it simple, maintainable, and correct

---

## core principles

**1. simplicity over cleverness**
```python
# bad
"id": (row_dict := dict(row))["id"]

# good
row_dict = dict(row)
return {"id": row_dict["id"]}
```

**2. fail fast and loud**
```python
# bad
except ImportError:
    pass

# good
except ImportError as e:
    logger.warning(f"failed to load module: {e}")
```

**3. explicit dependencies**
```python
# bad
job_queue = JobQueue()  # global

# good
async def handler(job_queue: JobQueue):  # explicit
```

**4. single responsibility**
```python
# bad
def process_seeds(seeds):
    validate(seeds)  # and
    transform(seeds)  # and
    save(seeds)      # and

# good: split into three functions
def validate_seeds(seeds: list) -> None
def transform_seeds(seeds: list) -> list
def save_seeds(db: Storage, seeds: list) -> None
```

**rules**:
- max 30 lines per function
- max 3 parameters (use dataclass for more)
- max 7 public methods per class
- if function has "and" in description, split it

---

## error handling

**catch specific exceptions**
```python
# bad
except Exception as e:
    logger.error(f"failed: {e}")  # lost traceback

# good
except (BlockExecutionError, ValidationError) as e:
    logger.error(f"failed: {e.message}", extra={"detail": e.detail})
    raise
except Exception as e:
    logger.exception("unexpected error")  # preserves traceback
    raise
```

**provide context**
```python
# bad
raise ValueError("invalid data")

# good
raise ValidationError(
    f"seed missing 'metadata': got {list(seed.keys())}",
    detail={"seed_index": idx, "expected": "metadata"}
)
```

**rules**:
- never catch `Exception` unless you re-raise
- use `logger.exception()` to preserve stack traces
- include context in exception detail dict
- no silent failures (empty except blocks)

---

## database

**use transactions**
```python
# bad: no transaction, partial delete possible
await db.execute("DELETE FROM records WHERE pipeline_id = ?", (id,))
await db.execute("DELETE FROM jobs WHERE pipeline_id = ?", (id,))
await db.execute("DELETE FROM pipelines WHERE id = ?", (id,))

# good: atomic operation
async with conn.execute("BEGIN"):
    try:
        await conn.execute("DELETE FROM records WHERE pipeline_id = ?", (id,))
        await conn.execute("DELETE FROM jobs WHERE pipeline_id = ?", (id,))
        await conn.execute("DELETE FROM pipelines WHERE id = ?", (id,))
        await conn.execute("COMMIT")
    except Exception:
        await conn.execute("ROLLBACK")
        raise
```

**parameterized queries**
```python
# bad
query = f"SELECT * FROM records WHERE status = '{status}'"

# good
query = "SELECT * FROM records WHERE status = ?"
cursor = await db.execute(query, (status,))
```

**log slow queries**
```python
async def _execute_with_logging(self, query: str, params: tuple):
    start = time.time()
    result = await self.db.execute(query, params)
    duration = time.time() - start
    if duration > 1.0:
        logger.warning(f"slow query ({duration:.2f}s): {query[:100]}")
    return result
```

**rules**:
- use transactions for multi-step operations
- never use string formatting for query values
- log slow queries (>1s)
- whitelist allowed fields for dynamic queries

---

## api design

**validate input**
```python
# bad
@app.post("/api/pipelines")
async def create_pipeline(request: dict):
    pipeline_id = await storage.save_pipeline(request["name"], request["data"])

# good
class CreatePipelineRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    pipeline_data: dict = Field(...)

    @validator("pipeline_data")
    def validate_blocks(cls, v):
        if "blocks" not in v:
            raise ValueError("pipeline_data must contain 'blocks'")
        return v

@app.post("/api/pipelines")
async def create_pipeline(request: CreatePipelineRequest):
    pipeline_id = await storage.save_pipeline(request.name, request.pipeline_data)
```

**consistent error handling**
```python
@app.exception_handler(PipelineError)
async def pipeline_error_handler(request: Request, exc: PipelineError):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "type": exc.__class__.__name__
        }
    )
```

**dependency injection**
```python
# bad
storage = Storage(db_path)  # global

# good
async def get_storage():
    storage = Storage(settings.DATABASE_PATH)
    await storage.init_db()
    try:
        yield storage
    finally:
        await storage.close()

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: int, storage: Storage = Depends(get_storage)):
    return await storage.get_job(job_id)
```

**rules**:
- use pydantic for request validation
- consistent error response format
- dependency injection for services
- add size limits to file uploads

---

## async/await

**don't block event loop**
```python
# bad
async def process():
    with open("file.txt") as f:  # blocks!
        return f.read()

# good
async def process():
    async with aiofiles.open("file.txt") as f:
        return await f.read()
```

**concurrent operations**
```python
# bad: sequential (slow)
results = []
for seed in seeds:
    result = await process_seed(seed)
    results.append(result)

# good: concurrent (fast)
tasks = [process_seed(seed) for seed in seeds]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**cleanup resources**
```python
# bad
task = asyncio.create_task(background_job())  # never cancelled!

# good
task = asyncio.create_task(background_job())
try:
    await some_work()
finally:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
```

**rules**:
- use async i/o (aiofiles, aiosqlite)
- use asyncio.gather for concurrent operations
- always cancel background tasks in cleanup

---

## testing

**one behavior per test**
```python
# bad: multiple assertions
def test_record():
    record = create_record()
    assert record.id == 1
    assert record.status == "pending"

# good: focused tests
def test_create_record_generates_id():
    record = create_record()
    assert isinstance(record.id, int)

def test_create_record_default_status_is_pending():
    record = create_record()
    assert record.status == "pending"
```

**test error cases**
```python
async def test_get_pipeline_success(storage):
    pipeline = await storage.get_pipeline(1)
    assert pipeline is not None

async def test_get_pipeline_not_found(storage):
    pipeline = await storage.get_pipeline(999)
    assert pipeline is None
```

**rules**:
- one behavior per test
- test error cases, not just happy path
- use fixtures for setup
- name: `test_<method>_<scenario>_<expected>`

---

## security

**never log secrets**
```python
# bad
logger.info(f"api_key={settings.LLM_API_KEY}")

# good
logger.info("connecting to llm api")
```

**validate inputs**
```python
# bad
def get_pipeline(pipeline_id: int):
    return db.query(f"SELECT * FROM pipelines WHERE id = {pipeline_id}")

# good
def get_pipeline(pipeline_id: int) -> Pipeline | None:
    if not isinstance(pipeline_id, int) or pipeline_id < 1:
        raise ValueError(f"invalid pipeline_id: {pipeline_id}")
    return db.query("SELECT * FROM pipelines WHERE id = ?", (pipeline_id,))
```

**size limits**
```python
# bad
contents = await file.read()

# good
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
contents = await file.read(MAX_FILE_SIZE + 1)
if len(contents) > MAX_FILE_SIZE:
    raise HTTPException(status_code=413, detail="file too large")
```

**rules**:
- never log secrets or sensitive data
- validate all inputs at api boundary
- enforce size limits on uploads
- always use parameterized sql queries

---

## performance

**profile before optimizing**
```python
import cProfile

profiler = cProfile.Profile()
profiler.enable()
result = expensive_function()
profiler.disable()
profiler.print_stats(sort='cumulative')
```

**avoid n+1 queries**
```python
# bad: n+1 queries
for pipeline in pipelines:
    jobs = await storage.get_jobs(pipeline.id)  # 1 per pipeline

# good: batch query
pipeline_ids = [p.id for p in pipelines]
all_jobs = await storage.get_jobs_by_pipeline_ids(pipeline_ids)  # 1 total
```

**rules**:
- profile before optimizing
- avoid n+1 queries
- use connection pooling
- cache expensive computations

---

## checklist

before committing, verify:

**functions and classes**
- [ ] functions <30 lines
- [ ] classes <7 public methods
- [ ] no magic numbers/strings
- [ ] clear names

**error handling**
- [ ] specific exceptions, never bare `Exception`
- [ ] `logger.exception()` for stack traces
- [ ] error messages include context
- [ ] no silent failures

**database**
- [ ] parameterized queries
- [ ] transactions for multi-step ops
- [ ] connection cleanup
- [ ] slow queries logged

**api**
- [ ] pydantic validation
- [ ] consistent error format
- [ ] dependency injection
- [ ] size limits on uploads

**async**
- [ ] async i/o (aiofiles, aiosqlite)
- [ ] gather for concurrent ops
- [ ] cleanup background tasks

**testing**
- [ ] tests exist for new features
- [ ] error cases tested
- [ ] test names: `test_<method>_<scenario>_<expected>`

**security**
- [ ] no secrets in logs
- [ ] all inputs validated
- [ ] size limits enforced
- [ ] sql parameterized

**type hints**
- [ ] all parameters typed
- [ ] all returns typed
- [ ] use `| None` not `Optional`

---

**golden rule**: if you can't explain what your code does in one sentence, it's too complex.
