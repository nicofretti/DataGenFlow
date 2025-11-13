# Code Style Guide - DataGenFlow

this guide defines how to write clean, maintainable code following the KISS (Keep It Simple, Stupid) principle.

---

## core principles

### 1. simplicity over cleverness
- write code that is obvious, not clever
- if it requires a comment to explain *what* it does, it's too complex
- prefer explicit over implicit
- avoid abstractions until you need them three times

### 2. clarity over abstraction
- clear, simple code beats elegant complexity
- one clear function beats one abstract framework
- name things what they are, not what they could be

### 3. explain intent, not mechanics
- comments should explain *why*, never *what*
- start comments in lowercase
- if you need to explain what the code does, refactor the code

### 4. one step better, not a full rewrite
- improve code incrementally
- don't rebuild what works
- fix the smell, don't perfume it

---

## code organization

### functions
```python
# bad: does too much
def process_data(data):
    # validate
    if not data: raise ValueError()
    # transform
    result = [x * 2 for x in data]
    # save
    db.save(result)
    # notify
    send_email(result)
    return result

# good: single responsibility
def process_data(data):
    validated = validate_data(data)
    return transform_data(validated)
```

**rules:**
- one function = one responsibility
- max 30 lines (if longer, split it)
- max 3 parameters (if more, use a dataclass)
- no side effects unless the name says so (e.g., `save_`, `update_`, `send_`)

### classes
```python
# bad: god object
class Storage:
    def save_record(self): ...
    def get_record(self): ...
    def save_pipeline(self): ...
    def get_pipeline(self): ...
    def save_job(self): ...
    def migrate_schema(self): ...
    def export_jsonl(self): ...

# good: separate concerns
class RecordRepository:
    def save(self, record): ...
    def get(self, id): ...

class PipelineRepository:
    def save(self, pipeline): ...
    def get(self, id): ...

class DatabaseMigrator:
    def migrate(self): ...
```

**rules:**
- one class = one concern
- max 7 public methods (if more, split the class)
- no class should do more than one thing
- prefer composition over inheritance

---

## anti-patterns to avoid

### 1. duplicated logic (DRY violation)
```python
# bad: duplicated ollama config in text_generator.py and structured_generator.py
def _prepare_llm_config(self):
    if "11434" in settings.LLM_ENDPOINT:
        model = f"ollama/{self.model}" if "/" not in self.model else self.model
        # ... more duplicated code

# good: extract to shared utility
class LLMConfigBuilder:
    @staticmethod
    def prepare(model: str, endpoint: str) -> tuple[str, str, str | None]:
        if LLMConfigBuilder.is_ollama(endpoint):
            return LLMConfigBuilder._ollama_config(model, endpoint)
        return model, endpoint, settings.LLM_API_KEY
```

**rule:** if you copy-paste code, create a function instead

### 2. magic numbers and strings
```python
# bad: scattered magic values
if "11434" in endpoint:  # what is 11434?
deque(maxlen=10)  # why 10?

# good: named constants
class Constants:
    OLLAMA_DEFAULT_PORT = "11434"
    MAX_JOB_HISTORY = 10

if Constants.OLLAMA_DEFAULT_PORT in endpoint:
deque(maxlen=Constants.MAX_JOB_HISTORY)
```

**rule:** any literal that appears twice needs a constant

### 3. long methods (>30 lines)
```python
# bad: 134-line method (workflow.py:173-307)
async def _execute_multiplier_pipeline(self, ...):
    # 134 lines of complex logic

# good: split into smaller methods
async def _execute_multiplier_pipeline(self, ...):
    seeds = await self._generate_seeds(initial_data)
    await self._update_seed_count(job_id, len(seeds))
    return await self._process_all_seeds(seeds, ...)

async def _process_all_seeds(self, seeds, ...):
    results = []
    for seed_idx, seed_data in enumerate(seeds):
        result = await self._process_single_seed(seed_idx, seed_data, ...)
        results.append(result)
    return results
```

**rule:** if a method doesn't fit on your screen, it's too long

### 4. god objects
```python
# bad: class with 20+ methods doing everything
class Storage:
    # connection management
    async def init_db(self): ...
    async def close(self): ...
    # schema migrations
    async def _migrate_schema(self): ...
    # record CRUD
    async def save_record(self): ...
    async def get_all(self): ...
    # pipeline CRUD
    async def save_pipeline(self): ...
    async def list_pipelines(self): ...
    # job CRUD
    async def create_job(self): ...
    async def list_jobs(self): ...
    # export
    async def export_jsonl(self): ...

# good: single responsibility classes
class DatabaseConnection:
    async def connect(self): ...
    async def close(self): ...

class RecordRepository:
    def __init__(self, db: DatabaseConnection): ...
    async def save(self, record): ...
    async def find_all(self, filters): ...

class PipelineRepository:
    def __init__(self, db: DatabaseConnection): ...
```

**rule:** if a class name is vague (Manager, Handler, Service, Storage), it's probably doing too much

### 5. poor error handling
```python
# bad: silent failures
try:
    seed_path.unlink()
except Exception:
    pass  # what happened? why did we ignore it?

# bad: catching too broadly
except Exception as e:
    logger.error(f"Job failed: {e}")  # lost the traceback

# good: specific and intentional
try:
    seed_path.unlink()
except FileNotFoundError:
    logger.debug(f"seed file already deleted: {seed_path}")
except OSError as e:
    logger.warning(f"failed to delete seed file {seed_path}: {e}")
```

**rule:** never catch `Exception` unless you re-raise it. catch specific exceptions.

### 6. deep nesting
```python
# bad: nested ifs
if condition1:
    if condition2:
        if condition3:
            do_something()
        else:
            do_other()
    else:
        handle()
else:
    error()

# good: early returns
if not condition1:
    error()
    return

if not condition2:
    handle()
    return

if not condition3:
    do_other()
    return

do_something()
```

**rule:** max nesting depth = 2. use early returns instead.

### 7. complex conditionals
```python
# bad: hard to understand
if self._conn or (self.db_path != ":memory:" and not skip_close):
    # what is this checking?

# good: named booleans
is_persistent = self._conn is not None
is_file_db = self.db_path != ":memory:"
should_close = is_file_db and not skip_close

if is_persistent or should_close:
    # clear intent
```

**rule:** if a condition has more than 2 operators, extract it to a named variable

### 8. inconsistent naming
```python
# bad: mixed styles
async def get_all(self): ...
async def list_pipelines(self): ...
async def fetch_jobs(self): ...

# good: consistent verbs
async def list_records(self): ...
async def list_pipelines(self): ...
async def list_jobs(self): ...
```

**rule:** use consistent verbs - get (single), list (multiple), create, update, delete

---

## naming conventions

### variables and functions
```python
# use snake_case
user_name = "john"
def calculate_total(): ...

# avoid abbreviations
# bad
usr_nm, calc_tot, proc_data
# good
user_name, calculate_total, process_data

# boolean variables start with is/has/can
is_valid = True
has_permission = False
can_edit = user.is_admin
```

### classes
```python
# use PascalCase
class UserAccount: ...
class PaymentProcessor: ...

# avoid vague suffixes unless necessary
# bad
class UserManager: ...  # what does it manage?
class DataHandler: ...  # what does it handle?

# good
class UserAuthenticator: ...  # authenticates users
class PaymentValidator: ...  # validates payments
```

### constants
```python
# use UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT = 30
OLLAMA_PORT = "11434"
```

---

## type hints

always use type hints. they are documentation.

```python
# bad: no types
def process(data):
    return data * 2

# good: clear types
def process(data: list[int]) -> list[int]:
    return [x * 2 for x in data]

# good: complex types
from typing import Any

async def execute(
    self,
    data: dict[str, Any],
    job_id: int | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    ...
```

**rule:** every function parameter and return value gets a type hint

---

## error handling

### be specific
```python
# bad
except Exception:
    handle_error()

# good
except (ValueError, TypeError) as e:
    logger.error(f"invalid input: {e}")
    raise
```

### fail fast
```python
# bad: validate late
def process(data):
    # ... 50 lines of processing
    if not data:  # should check first
        raise ValueError()

# good: validate early
def process(data):
    if not data:
        raise ValueError("data cannot be empty")
    # ... processing
```

### provide context
```python
# bad: vague error
raise ValueError("invalid data")

# good: specific error
raise ValueError(
    f"expected dict with 'metadata' key, got {type(data).__name__}"
)
```

---

## testing

### test files mirror source files
```
lib/workflow.py       -> tests/test_workflow.py
lib/storage.py        -> tests/test_storage.py
lib/blocks/base.py    -> tests/blocks/test_base.py
```

### test naming
```python
# pattern: test_<method>_<scenario>_<expected>
def test_execute_valid_data_returns_result(): ...
def test_execute_missing_field_raises_error(): ...
def test_execute_empty_blocks_returns_initial_data(): ...
```

### one assert per test
```python
# bad: multiple assertions
def test_user():
    user = create_user()
    assert user.name == "john"
    assert user.age == 25
    assert user.is_active is True

# good: focused tests
def test_create_user_sets_name():
    user = create_user(name="john")
    assert user.name == "john"

def test_create_user_sets_age():
    user = create_user(age=25)
    assert user.age == 25
```

---

## imports

### order
```python
# 1. standard library
import json
import logging
from datetime import datetime
from typing import Any

# 2. third-party
from fastapi import FastAPI
from pydantic import BaseModel

# 3. local
from config import settings
from lib.storage import Storage
```

### avoid wildcards
```python
# bad
from lib.blocks import *

# good
from lib.blocks import BaseBlock, TextGenerator
```

---

## comments

### when to comment
```python
# bad: stating the obvious
# increment counter
counter += 1

# bad: explaining what (code should be clear)
# loop through users and check if active
for user in users:
    if user.is_active:
        ...

# good: explaining why
# ollama requires a specific model prefix format
if not model.startswith("ollama/"):
    model = f"ollama/{model}"

# good: explaining non-obvious business logic
# skip records with zero repetitions to avoid wasting API credits
if repetitions == 0:
    continue
```

### todo comments
```python
# format: TODO: <what> - <why> - <who/when>
# TODO: extract ollama config to shared util - DRY violation - @nicof 2024-11
```

---

## sql and databases

### use parameterized queries (always)
```python
# bad: f-string (sql injection risk)
query = f"SELECT * FROM users WHERE id = {user_id}"

# good: parameters
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```

### keep queries simple
```python
# bad: complex dynamic query
query = f"SELECT * FROM {table} WHERE {' AND '.join(conditions)}"

# good: explicit query
query = "SELECT * FROM records WHERE status = ? AND pipeline_id = ?"
cursor.execute(query, (status, pipeline_id))
```

---

## async/await

### don't mix sync and async
```python
# bad: sync in async context
async def process():
    data = read_file()  # blocking call
    return await save_data(data)

# good: all async
async def process():
    data = await read_file_async()
    return await save_data(data)
```

### await in loops (be careful)
```python
# bad: sequential (slow)
results = []
for item in items:
    result = await process(item)  # waits for each
    results.append(result)

# good: concurrent (fast)
tasks = [process(item) for item in items]
results = await asyncio.gather(*tasks)
```

---

## git workflow

### commit messages
```
format: <type>: <description>

types:
- fix: bug fix
- feat: new feature
- edit: refactor or improvement
- clean: remove unused code
- docs: documentation only

examples:
fix: prevent double API call on page load
feat: add user authentication
edit: extract ollama config to shared util
clean: remove unused import
docs: add code style guide
```

### commit rules
- never commit unless asked
- never include llm/* files
- ask for confirmation first
- one logical change per commit

---

## file structure

### keep files small
```
# bad: 500+ lines in one file
lib/api.py  # everything

# good: split by concern
lib/api/routes.py      # route handlers
lib/api/validators.py  # input validation
lib/api/responses.py   # response formatting
```

**rule:** max 300 lines per file

### organize by feature, not type
```
# bad: organized by type
models/user.py
models/payment.py
services/user.py
services/payment.py

# good: organized by feature
users/model.py
users/service.py
payments/model.py
payments/service.py
```

---

## performance

### profile before optimizing
don't optimize without measuring. premature optimization is evil.

```python
# don't do this without profiling first
# "this loop might be slow, let me optimize it"

# do this instead
import cProfile
cProfile.run('my_function()')
# now you know what's actually slow
```

### avoid n+1 queries
```python
# bad: n+1 queries
for pipeline in pipelines:
    jobs = await storage.get_jobs(pipeline.id)  # 1 query per pipeline

# good: batch query
pipeline_ids = [p.id for p in pipelines]
all_jobs = await storage.get_jobs_batch(pipeline_ids)  # 1 query total
```

---

## security

### never log secrets
```python
# bad
logger.info(f"connecting with api_key={api_key}")

# good
logger.info("connecting to llm api")
```

### validate all inputs
```python
# bad: trust user input
def get_record(record_id):
    return db.query(f"SELECT * FROM records WHERE id = {record_id}")

# good: validate and parameterize
def get_record(record_id: int) -> Record | None:
    if not isinstance(record_id, int) or record_id < 1:
        raise ValueError(f"invalid record_id: {record_id}")
    return db.query("SELECT * FROM records WHERE id = ?", (record_id,))
```

---

## summary checklist

before committing code, check:

- [ ] functions are <30 lines
- [ ] classes have <7 public methods
- [ ] no duplicated code
- [ ] no magic numbers/strings
- [ ] nesting depth ≤2
- [ ] all parameters have type hints
- [ ] errors are specific, not `Exception`
- [ ] comments explain why, not what
- [ ] names are clear and consistent
- [ ] tests are included
- [ ] no secrets in logs
- [ ] sql uses parameters, not f-strings

**when in doubt: simpler is better.**
