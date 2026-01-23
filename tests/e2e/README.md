# DataGenFlow E2E Tests

end-to-end tests for the DataGenFlow application using Playwright.

## Overview

these tests verify the full application stack (backend + frontend) by simulating real user interactions in a browser. they cover the main user workflows:

- **pipelines**: create, edit, delete pipelines
- **generator**: upload seeds, start jobs, monitor progress
- **review**: view records, update status, export data

## Setup

### 1. Install dependencies

```bash
# install dev dependencies (includes playwright)
uv sync --dev

# install chromium browser for playwright
uv run playwright install chromium
```

### 2. Verify servers can start

make sure both backend and frontend can start:

```bash
# test backend (port 8000)
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000

# test frontend (port 5173, in another terminal)
cd frontend && yarn dev
```

## Running Tests

### Quick start

```bash
# using make (recommended)
make test-e2e        # run all tests (headless mode)
make test-e2e-ui     # run all tests with visible browser UI

# or directly
./tests/e2e/run_all_tests.sh        # headless mode
./tests/e2e/run_all_tests.sh --ui   # visible browser UI
```

### Using the server helper (recommended)

the `scripts/with_server.py` helper automatically manages server lifecycle:

```bash
# run all e2e tests with server management (headless)
python scripts/with_server.py \
  --server "uv run uvicorn app:app --host 0.0.0.0 --port 8000" --port 8000 \
  --server "cd frontend && yarn dev" --port 5173 \
  -- python tests/e2e/test_pipelines_e2e.py

# run with visible browser UI
E2E_HEADLESS=false python scripts/with_server.py \
  --server "uv run uvicorn app:app --host 0.0.0.0 --port 8000" --port 8000 \
  --server "cd frontend && yarn dev" --port 5173 \
  -- python tests/e2e/test_pipelines_e2e.py
```

### Run specific test suites

```bash
# pipelines tests
python scripts/with_server.py \
  --server "uv run uvicorn app:app --host 0.0.0.0 --port 8000" --port 8000 \
  --server "cd frontend && yarn dev" --port 5173 \
  -- python tests/e2e/test_pipelines_e2e.py

# generator tests
python scripts/with_server.py \
  --server "uv run uvicorn app:app --host 0.0.0.0 --port 8000" --port 8000 \
  --server "cd frontend && yarn dev" --port 5173 \
  -- python tests/e2e/test_generator_e2e.py

# review tests
python scripts/with_server.py \
  --server "uv run uvicorn app:app --host 0.0.0.0 --port 8000" --port 8000 \
  --server "cd frontend && yarn dev" --port 5173 \
  -- python tests/e2e/test_review_e2e.py
```

### Manual testing (servers already running)

if you already have servers running, you can run tests directly:

```bash
# start servers in separate terminals first
# terminal 1
make dev-backend

# terminal 2
make dev-ui

# terminal 3 - run tests
python tests/e2e/test_pipelines_e2e.py
python tests/e2e/test_generator_e2e.py
python tests/e2e/test_review_e2e.py
```

## Test Structure

```text
tests/e2e/
├── README.md                      # this file
├── test_helpers.py                # database cleanup utilities
├── fixtures/                      # test data
│   ├── simple_seed.json          # basic seed file
│   ├── qa_seed.json              # qa generation seed
│   ├── classification_seed.json  # classification seed
│   └── sample_markdown.md        # markdown multiplier test
├── test_pipelines_e2e.py         # pipeline workflows (with cleanup)
├── test_generator_e2e.py         # generation workflows
└── test_review_e2e.py            # review workflows
```

## Database Cleanup

> **WARNING**: e2e tests delete ALL pipelines, jobs, and records. Always use a dedicated test database or isolated environment - never run against production data.

the **pipelines tests** automatically clean the database before and after running to ensure test isolation:

- **before tests**: deletes all pipelines, jobs, and records
- **after tests**: cleans up any created data

this ensures each test run starts with a clean state.

## Test Coverage

### test_pipelines_e2e.py
- ✓ pipelines page loads
- ✓ view templates
- ✓ create pipeline from template
- ✓ delete pipeline
- ✓ pipeline editor opens

### test_generator_e2e.py
- ✓ generator page loads
- ✓ select pipeline
- ✓ upload seed file
- ✓ start generation job
- ✓ job progress monitoring

### test_review_e2e.py
- ✓ review page loads
- ✓ select job
- ✓ view records
- ✓ update record status
- ✓ expand trace
- ✓ delete records
- ✓ export records

## Debugging

### Screenshots

all tests save screenshots to `/tmp/` for debugging:
- `/tmp/pipelines_page.png`
- `/tmp/templates_view.png`
- `/tmp/pipeline_created.png`
- `/tmp/generator_page.png`
- `/tmp/job_started.png`
- etc.

### Browser visibility

to see the browser during tests:

```bash
# using run script
./tests/e2e/run_all_tests.sh --ui

# using environment variable
E2E_HEADLESS=false python tests/e2e/test_pipelines_e2e.py

# or export it for the session
export E2E_HEADLESS=false
python tests/e2e/test_pipelines_e2e.py
```

the tests will automatically detect the `E2E_HEADLESS` environment variable:
- `E2E_HEADLESS=false` → visible browser (chromium UI)
- `E2E_HEADLESS=true` or unset → headless mode (default)

### Slow down execution

add delays to observe actions:

```python
import time
time.sleep(2)  # wait 2 seconds
```

## Writing New Tests

follow the webapp-testing skill patterns:

1. **wait for networkidle** after page load:
```python
page.goto("http://localhost:5173")
page.wait_for_load_state("networkidle")
```

2. **use descriptive selectors**:
```python
# good - semantic selectors
page.get_by_role("button").filter(has_text="Create")
page.get_by_text("Pipeline", exact=False)

# avoid - fragile css
page.locator("#btn-123")
```

3. **take screenshots** for debugging:
```python
page.screenshot(path="/tmp/debug.png", full_page=True)
```

4. **add appropriate waits**:
```python
time.sleep(1)  # wait for animation
page.wait_for_selector(".record-card")  # wait for element
```

## Fixtures

test fixtures are in `fixtures/`:

- `simple_seed.json`: basic text generation (2 variations)
- `qa_seed.json`: question-answer generation (5 total)
- `classification_seed.json`: text classification (2 samples)
- `sample_markdown.md`: markdown multiplier test

use fixtures in tests:

```python
seed_path = "tests/e2e/fixtures/simple_seed.json"
file_input.set_input_files(seed_path)
```

## Troubleshooting

### servers don't start
- check ports 8000 and 5173 are not in use
- verify `uv` and `yarn` are installed
- check backend/frontend dependencies installed

### tests fail with timeout
- increase `max_wait` in with_server.py
- add longer waits in tests
- check browser console for errors

### elements not found
- take screenshots to see actual page state
- use browser devtools to find correct selectors
- add wait time for dynamic content

### cleanup issues
- servers may not stop cleanly - use `pkill -f "uvicorn.*8000"` (or match your configured port) to avoid terminating unrelated processes. `killall` affects all matching processes on the machine.
- remove test database (only if using a dedicated test path): `rm data/test_qa_records.db`

## CI/CD Integration

example GitHub Actions workflow:

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: |
          uv venv && uv sync
          cd frontend && yarn install

      - name: Install Playwright
        run: |
          uv pip install playwright
          uv run playwright install chromium

      - name: Run E2E tests
        run: |
          python scripts/with_server.py \
            --server "uv run uvicorn app:app --host 0.0.0.0 --port 8000" --port 8000 \
            --server "cd frontend && yarn dev" --port 5173 \
            -- python tests/e2e/test_pipelines_e2e.py
```

## Best Practices

1. **keep tests independent**: each test should work standalone
2. **clean up state**: delete created pipelines/jobs after tests
3. **use fixtures**: reuse seed files from `fixtures/`
4. **handle async**: wait for network requests to complete
5. **screenshot failures**: capture state when tests fail
6. **descriptive names**: test names should describe what they verify

## Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [Playwright Best Practices](https://playwright.dev/python/docs/best-practices)
- [DataGenFlow API docs](/DEVELOPERS.md)
