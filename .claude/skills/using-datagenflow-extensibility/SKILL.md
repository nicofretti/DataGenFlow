---
name: using-datagenflow-extensibility
description: Use when creating data generation pipelines with DataGenFlow's extensibility system — user_templates, user_blocks, docker-compose setup, and dgf CLI. Use for any task involving generating synthetic data, building custom pipelines, or extending DataGenFlow from an external project without modifying its source.
---

# Using DataGenFlow Extensibility

Build data generation pipelines from your own repo using DataGenFlow as a Docker image. Custom blocks and templates live in your project — no DataGenFlow source modifications needed.

## Project Structure

```
your-project/
  user_blocks/          # custom Python blocks (auto-discovered)
  user_templates/       # custom YAML pipelines (auto-discovered)
  data/                 # persisted output data
  docker-compose.yml    # mounts volumes into DataGenFlow container
  .env                  # API keys + config
```

## Quick Setup

```bash
# 1. Create project structure
mkdir -p user_blocks user_templates data

# 2. Create .env with at least one LLM provider
echo "OPENAI_API_KEY=sk-..." > .env

# 3. Create docker-compose.yml (see Docker section)

# 4. Start DataGenFlow
docker-compose up -d

# 5. Verify
curl http://localhost:8000/health
```

## docker-compose.yml

```yaml
services:
  datagenflow:
    image: datagenflow:local
    ports:
      - "8000:8000"
    volumes:
      - ./user_blocks:/app/user_blocks
      - ./user_templates:/app/user_templates
      - ./data:/app/data
    env_file:
      - .env
    environment:
      - DATAGENFLOW_HOT_RELOAD=true
    restart: unless-stopped
```

Build the image first from DataGenFlow repo: `docker build -f docker/Dockerfile -t datagenflow:local .`

## Writing Templates

Templates are YAML files in `user_templates/`. Template ID = filename stem.

### YAML Format

```yaml
name: "Display Name"
description: "What this pipeline generates"
blocks:
  - type: BlockClassName        # exact class name
    config:
      param: value              # exact __init__ parameter names
      user_prompt: "{{ var }}"  # Jinja2 refs to seed metadata
```

### Seed Files

Place next to template: `user_templates/seed_<template_id>.json`

```json
[
  {"repetitions": 3, "metadata": {"content": "input text here"}},
  {"repetitions": 2, "metadata": {"content": "another input"}}
]
```

For `MarkdownMultiplierBlock` as first block, use `seed_<template_id>.md` instead.

### Variable Flow

Seed `metadata` keys become `{{ key }}` in first block's prompt. Each block's outputs become available to subsequent blocks via `{{ output_name }}`.

Key output names by block:
- `TextGenerator` outputs: `assistant`, `system`, `user`
- `StructuredGenerator` outputs: `generated`
- `JSONValidatorBlock` outputs: `valid`, `parsed_json`
- `FieldMapper` outputs: dynamic (whatever you map)

## Available Blocks — Quick Reference

| Block | Config Params | Use For |
|-------|--------------|---------|
| `TextGenerator` | `model`, `temperature`, `max_tokens`, `system_prompt`, `user_prompt` | Free-text generation |
| `StructuredGenerator` | `model`, `temperature`, `max_tokens`, `user_prompt`, `json_schema` | JSON generation with schema |
| `JSONValidatorBlock` | `field_name`, `required_fields`, `strict` | Validate JSON output |
| `FieldMapper` | `mappings` | Rename/transform fields between blocks |
| `MarkdownMultiplierBlock` | `parser_type`, `chunk_size`, `chunk_overlap` | Split documents (must be first) |
| `StructureSampler` | _(see source)_ | Sample from structure (must be first) |
| `ValidatorBlock` | _(see source)_ | Text rule validation |
| `DuplicateRemover` | _(see source)_ | Embedding-based dedup |
| `DiversityScore` | _(see source)_ | Lexical diversity metric |
| `CoherenceScore` | _(see source)_ | Text coherence metric |
| `RagasMetrics` | _(see source)_ | RAGAS QA evaluation |
| `LangfuseBlock` | _(see source)_ | Observability tracing |

## Common Pipeline Patterns

```
# Simple: generate structured JSON + validate
StructuredGenerator → JSONValidatorBlock

# Document processing: chunk → generate text → structure → validate
MarkdownMultiplierBlock → TextGenerator → StructuredGenerator → JSONValidatorBlock

# Augmentation: sample → fill → deduplicate
StructureSampler → SemanticInfiller → DuplicateRemover

# With metrics: generate → map fields → evaluate
StructuredGenerator → FieldMapper → RagasMetrics
```

## Writing Custom Blocks

Place `.py` files in `user_blocks/`. Auto-discovered if class inherits `BaseBlock`.

```python
from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext
from typing import Any


class MyCustomBlock(BaseBlock):
    name = "My Custom Block"
    description = "What it does"
    category = "validators"           # generators, validators, metrics, utilities, seeders, observability
    inputs = ["text"]
    outputs = ["result"]

    # optional: pip deps auto-detected
    dependencies = ["some-package>=1.0"]

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        text = context.get_state("text", "")
        return {"result": f"processed: {text}"}
```

Scaffold with: `dgf blocks scaffold MyBlock -c validators`

## dgf CLI Commands

```bash
# Status
dgf status                              # server health + counts

# Blocks
dgf blocks list                         # all blocks with source/status
dgf blocks validate ./my_block.py       # check syntax
dgf blocks scaffold MyBlock -c general  # generate starter

# Templates
dgf templates list                      # all templates with source
dgf templates validate ./flow.yaml      # check YAML structure
dgf templates scaffold "My Flow"        # generate starter

# Image (production)
dgf image scaffold --blocks-dir ./user_blocks  # Dockerfile with deps
dgf image build -t my-datagenflow:latest       # build custom image
```

Run from DataGenFlow repo: `cd /path/to/DataGenFlow && uv run dgf <command>`

## Testing a Template

```bash
# 1. Validate YAML
uv run dgf templates validate ./user_templates/my_template.yaml

# 2. Check it's discovered
uv run dgf templates list

# 3. Create pipeline from template
curl -s -X POST http://localhost:8000/api/pipelines/from_template/my_template | python -m json.tool

# 4. Execute with seed
curl -s -X POST http://localhost:8000/api/pipelines/<pipeline_id>/execute \
  -H 'Content-Type: application/json' \
  -d '{"content": "test input"}' | python -m json.tool
```

Or use the UI at `http://localhost:8000` — templates appear in the pipeline creation flow.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATAGENFLOW_ENDPOINT` | `http://localhost:8000` | API endpoint (for CLI) |
| `DATAGENFLOW_BLOCKS_PATH` | `user_blocks` | Path to user blocks dir |
| `DATAGENFLOW_TEMPLATES_PATH` | `user_templates` | Path to user templates dir |
| `DATAGENFLOW_HOT_RELOAD` | `true` | Enable file watching |
| `DATAGENFLOW_HOT_RELOAD_DEBOUNCE_MS` | `500` | Debounce interval |

## Step-by-Step Workflow

1. **Define the use case** — what data to generate, what schema, what seed inputs
2. **Choose blocks** — pick from table, wire outputs → inputs
3. **Write YAML** in `user_templates/<template_id>.yaml`
4. **Write seed file** — `user_templates/seed_<template_id>.json` with all `{{ vars }}` as metadata keys
5. **Validate** — `dgf templates validate` + `dgf templates list`
6. **Test single execution** — create pipeline from template, run with seed
7. **Iterate** — adjust prompts, schema, temperature based on output quality
8. **Scale** — increase seed repetitions, add more seed examples

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Template ID conflicts with builtin | Rename your file — builtins take precedence |
| Block `type` doesn't match class name | Use exact class name (e.g., `JSONValidatorBlock` not `JSONValidator`) |
| Config key doesn't match `__init__` param | Read block source or use `dgf blocks list` |
| Seed variable missing from metadata | Every `{{ var }}` in prompts needs a matching metadata key |
| Multiplier block not first | `MarkdownMultiplierBlock` and `StructureSampler` must be first |
| Hot reload not picking up changes | Check `DATAGENFLOW_HOT_RELOAD=true` and dirs exist before startup |
| Block shows unavailable | Missing deps — install via API or build custom image |

## Checklist

- [ ] Project structure created (user_blocks/, user_templates/, data/, docker-compose.yml, .env)
- [ ] DataGenFlow running and healthy (`curl /health`)
- [ ] Template YAML with correct block types and config keys
- [ ] Seed file named `seed_<template_id>.json` with all referenced variables
- [ ] Template appears in `dgf templates list`
- [ ] Single execution produces expected output fields
- [ ] Seed file has 2-3 diverse examples for quality testing
- [ ] Custom blocks (if any) appear in `dgf blocks list` as source "user"

## Related DataGenFlow Skills

- `creating-pipeline-templates` — reference for builtin template patterns
- `implementing-datagenflow-blocks` — deep dive on block internals
- `debugging-pipelines` — troubleshooting execution failures
- `testing-pipeline-templates` — thorough end-to-end testing
- `configuring-models` — LLM provider setup
