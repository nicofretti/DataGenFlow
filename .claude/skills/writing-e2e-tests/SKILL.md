---
name: writing-e2e-tests
description: Use when writing Playwright end-to-end tests for DataGenFlow UI. Covers test file creation, database cleanup, navigation, file uploads, confirmation modals, and job monitoring. Use for new UI features, extending existing test suites (pipelines, generator, review, settings), or verifying UI flows after frontend changes.
---

# Writing E2E Tests for DataGenFlow

Tests use Playwright **sync API** against a running app. Follow patterns in `tests/e2e/`.

## Test Infrastructure

```
tests/e2e/
├── test_helpers.py            # get_headless_mode, cleanup_database, wait_for_server, get_pipeline_count
├── test_pipelines_e2e.py      # pipeline CRUD tests
├── test_generator_e2e.py      # generation flow tests
├── test_review_e2e.py         # review page tests
├── run_all_tests.sh           # run all suites
└── fixtures/                  # seed files for tests
```

**Running tests:**
```bash
# single suite
python .claude/skills/webapp-testing/scripts/with_server.py \
  --server "cd /home/nicof/develop/DataGenFlow && DATABASE_PATH=data/test_qa_records.db uv run python app.py" \
  --port 8000 \
  -- python tests/e2e/test_<feature>_e2e.py

# all suites
bash tests/e2e/run_all_tests.sh

# visible browser
E2E_HEADLESS=false bash tests/e2e/run_all_tests.sh --ui
```

**WARNING:** `cleanup_database()` deletes ALL data. Only use with `DATABASE_PATH=data/test_qa_records.db`.

## Test File Template

```python
"""e2e tests for <feature> page"""
import json
import pytest
from playwright.sync_api import sync_playwright
from tests.e2e.test_helpers import cleanup_database, get_headless_mode

BASE_URL = "http://localhost:8000"

@pytest.fixture(autouse=True)
def setup_and_cleanup():
    cleanup_database()
    yield
    cleanup_database()

def test_feature_page_loads(tmp_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=get_headless_mode())
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        page.click("text=<Page Name>")
        page.wait_for_load_state("networkidle")

        assert page.locator("text=<Expected Heading>").is_visible()
        page.screenshot(path=str(tmp_path / "feature_page.png"))
        browser.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

## Key Patterns

**Navigation:**
```python
page.goto(BASE_URL, wait_until="networkidle")
page.click("text=Pipelines")  # sidebar nav
page.wait_for_load_state("networkidle")
```

**File upload:**
```python
seed_data = [{"repetitions": 1, "metadata": {"content": "test"}}]
seed_file = tmp_path / "test_seed.json"
seed_file.write_text(json.dumps(seed_data))
page.locator('input[type="file"]').set_input_files(str(seed_file))
```

**Confirmation modals (shadcn):**
```python
page.click("button:has-text('Delete')")
page.wait_for_selector("[role='alertdialog'], [role='dialog']")
page.locator("[role='alertdialog'] button:has-text('Delete'), [role='dialog'] button:has-text('Delete')").click()
```

**Waiting:**
```python
page.wait_for_selector("text=My Pipelines", timeout=10000)
page.wait_for_selector("text=Loading", state="hidden", timeout=10000)
page.locator("text=completed").wait_for(timeout=30000)
```

## Common UI Selectors

| Element | Selector |
|---------|----------|
| Sidebar nav | `text=Pipelines`, `text=Generator`, `text=Review`, `text=Settings` |
| Template cards | `button:has-text('Use Template')` |
| Delete/Edit buttons | `[aria-label='delete']`, `[aria-label='edit']` |
| File input | `input[type='file']` |
| Generate button | `button:has-text('Generate')` |
| Confirmation dialog | `[role='alertdialog'], [role='dialog']` |
| ReactFlow canvas | `.react-flow` |
| Toast notifications | `[data-sonner-toast]` |
| Select/Combobox | `[role='combobox'], select` |
| Options dropdown | `[role='option']` |

## Adding to run_all_tests.sh

```bash
echo "Running <feature> tests..."
python .claude/skills/webapp-testing/scripts/with_server.py \
  --server "cd $PROJECT_DIR && DATABASE_PATH=data/test_qa_records.db uv run python app.py" \
  --port 8000 \
  -- python tests/e2e/test_<feature>_e2e.py
```

## Checklist

- [ ] File named `test_<feature>_e2e.py`
- [ ] Uses `sync_playwright` (not async)
- [ ] `autouse=True` cleanup fixture
- [ ] `wait_until="networkidle"` after navigation
- [ ] Screenshots via `tmp_path`
- [ ] Standalone `if __name__ == "__main__"` block
- [ ] Tests pass with `with_server.py`
- [ ] Added to `run_all_tests.sh`

## Related Skills

- `webapp-testing` — Playwright utilities and `with_server.py`
- `debugging-pipelines` — pipeline logic failures in tests
