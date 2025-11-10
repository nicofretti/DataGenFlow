# Contributing to DataGenFlow

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Conventions](#pull-request-conventions)
- [Code Style](#code-style)
- [Commit Messages](#commit-messages)
- [Questions](#questions)

## Getting Started

1. **Fork the repository**
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/DataGenFlow.git
   cd DataGenFlow
   ```
3. **Set up development environment**:
   ```bash
   make setup
   make dev
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
   Tip: Click "Create a new branch" on GitHub when making a PR to have a good branch name.

## Development Workflow

### Running the application
```bash
# development mode (both servers with hot reload)
make run-dev          # starts backend (:8000) and frontend (:5173)

# or run separately in different terminals
make dev-backend      # backend on :8000 with auto-reload
make dev-ui           # frontend on :5173 with hot reload

# production mode
make run              # builds frontend and runs backend
```

### Code quality
Before submitting a PR, ensure:
```bash
make format     # format code with ruff
make lint       # check for issues
make typecheck  # run mypy
make test       # run all tests
```

All checks must pass before merging.

## Pull Request Conventions

We use icons and prefixes to make PRs easy to scan and understand at a glance.

### Using PR Templates

When creating a pull request, GitHub will prompt you to choose a template:
- **🚀 Feature** - For new functionality
- **🧩 Fix** - For bug fixes
- **📐 Refactor** - For code improvements
- **📚 Docs** - For documentation updates

Select the appropriate template to get a pre-filled PR description with the right sections.

### PR Title Format

```bash
<icon> <type>: <short description>
```

### PR Types

| Type | Icon | Description | Example |
|------|------|-------------|---------|
| **Feature** | 🚀 | New functionality or capability | 🚀 feat: add JSON validation block |
| **Fix** | 🧩 | Bug fixes or corrections | 🧩 Fix: block configuration not visible in edit mode |
| **Epic** | 🛸 | Large feature requiring multiple PRs | 🛸 EPIC: complex workflow and branching support |
| **Refactor** | 📐 | Code improvements without behavior change | 📐 Refactor: simplify block renderer logic |
| **Docs** | 📚 | Documentation updates | 📚 Docs: add block creation guide |

### PR Description Guidelines

Every PR should include:

1. **Description**: What does this PR do?
2. **Proposed solution**: Why is this change needed?
3. **Testing**: How was this tested?

#### For Fix PRs, also include:
4. **Reproduction steps**: How to reproduce the bug
5. **Expected vs Actual**: What should happen vs what happens

### Example PR (Fix)

```markdown
Title: 🧩 Fix: block configuration not visible in edit mode

### Description
Fixed issue where block configuration panel doesn't appear when editing existing pipelines.


### Reproduction Steps
1. Create a new pipeline with a TextGenerator block
2. Configure the block with a custom system prompt
3. Save the pipeline
4. Click "Edit" on the saved pipeline
5. Click on the TextGenerator block
6. **Bug**: Configuration panel doesn't appear

### Expected vs Actual
- **Expected**: Configuration panel should appear on the right side
- **Actual**: Nothing happens when clicking the block

### Proposed Solution
- Updated `Pipelines.tsx` to properly load block config when entering edit mode
- Fixed state initialization in `useEffect` hook
- Added null check for block config before rendering

## Testing
- Manually tested edit flow with all block types
- Added test case in `test_api.py` for pipeline update endpoint
- All existing tests passing
```

### Example PR (Feature)

```markdown
Title: 🚀 Feat: add retry logic to TextGenerator block

### Description
Added configurable retry logic to TextGenerator for handling transient API failures. LLM API calls can fail due to rate limits, network issues, or temporary outages. Without retries, entire pipeline executions fail, wasting compute and time.

## Proposed Solution
- Added `max_retries` and `retry_delay` config options to TextGenerator
- Implemented exponential backoff strategy
- Updated TextGenerator schema and validation
- Added tests for retry behavior

## Testing
- Unit tests for retry logic with mocked failures
- Integration test with actual API (using test endpoint)
- Tested with rate-limited endpoint to verify backoff
```

## Code Style

- Follow existing code patterns
- Write comments that explain **why**, not **what**
- Use lowercase for comments
- Return early instead of nested `else` statements
- Create minimal number of functions
- Code should be self-explanatory

### Example:

```python
# ❌ Bad
def process_data(data):
    # Process the data
    if data is not None:
        result = data.upper()
        return result
    else:
        return None

# ✅ Good
def process_data(data):
    # early return avoids unnecessary nesting
    if data is None:
        return None

    return data.upper()
```

## Commit Messages

- Keep commits focused and atomic
- Write clear, descriptive commit messages
- Squash WIP commits before merging

## Questions?

Feel free to open an issue or reach out to maintainers if you have questions about contributing.


