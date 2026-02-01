---
name: creating-pipeline-templates
description: Use when creating new pipeline templates (YAML + seed files) for DataGenFlow. Guides through block selection, YAML authoring, seed file creation, and validation. Use for any task involving lib/templates/ directory, adding new template use cases, or creating seed files that match pipeline variables.
---

# Creating Pipeline Templates

Templates are YAML definitions + seed files in `lib/templates/`. Auto-discovered on startup by `TemplateRegistry` (`lib/templates/__init__.py`).

- Template ID = filename without `.yaml`
- Seed file: `seed_<template_id>.json` or `seed_<template_id>.md`

## Template YAML Format

```yaml
name: Template Display Name
description: What this template generates
blocks:
  - type: BlockClassName       # must match class name exactly
    config:
      param1: value1           # must match __init__ parameter names exactly
      user_prompt: "{{ var }}" # Jinja2 references to seed metadata
  - type: AnotherBlock
    config:
      field_name: generated
```

## Seed File Format

**JSON** (most templates):
```json
[
  {"repetitions": 3, "metadata": {"content": "input text here"}}
]
```

**Markdown** (only for `MarkdownMultiplierBlock` as first block):
- File: `seed_<template_id>.md`
- Registry auto-wraps as `[{"repetitions": 1, "metadata": {"file_content": "<content>"}}]`

## Available Blocks

| Block | Category | Key Outputs | Notes |
|-------|----------|-------------|-------|
| `TextGenerator` | generators | assistant, system, user | free-text via LLM |
| `StructuredGenerator` | generators | generated | JSON via LLM with schema |
| `SemanticInfiller` | generators | dynamic | complete skeleton records |
| `StructureSampler` | seeders | skeletons, _seed_samples | multiplier, must be first |
| `MarkdownMultiplierBlock` | seeders | content | multiplier, must be first |
| `ValidatorBlock` | validators | text, valid, assistant | text rules |
| `JSONValidatorBlock` | validators | valid, parsed_json | JSON parse + validate |
| `DuplicateRemover` | validators | generated_samples | embedding similarity |
| `DiversityScore` | metrics | diversity_score | lexical diversity |
| `CoherenceScore` | metrics | coherence_score | text coherence |
| `RougeScore` | metrics | rouge_score | ROUGE comparison |
| `RagasMetrics` | metrics | ragas_scores | RAGAS QA evaluation |
| `FieldMapper` | utilities | dynamic | Jinja2 field expressions |
| `LangfuseBlock` | observability | langfuse_trace_url | trace logging |

## Common Pipeline Patterns

```
# simple generation + validation
StructuredGenerator → JSONValidatorBlock

# document processing (multiplier first)
MarkdownMultiplierBlock → TextGenerator → StructuredGenerator → JSONValidatorBlock

# data augmentation
StructureSampler → SemanticInfiller → DuplicateRemover

# generation + metrics
StructuredGenerator → FieldMapper → RagasMetrics
```

## Step-by-Step Workflow

1. **Define use case** — what data to generate, what fields in output, what seed input needed
2. **Choose blocks** — pick from table above, wire outputs to inputs
3. **Write YAML** — `lib/templates/<template_id>.yaml`
4. **Write seed file** — match `{{ variables }}` in YAML to metadata keys
5. **Validate template loads:**
   ```bash
   uv run python -c "
   from lib.templates import template_registry
   for t in template_registry.list_templates():
       print(f'{t[\"id\"]}: {t[\"name\"]}')
   "
   ```
6. **Check block params** (if unsure about config keys):
   ```bash
   uv run python -c "
   from lib.blocks.registry import BlockRegistry
   registry = BlockRegistry()
   for name, cls in registry._blocks.items():
       schema = cls.get_schema()
       print(f'{name}: {list(schema.get(\"config_schema\", {}).get(\"properties\", {}).keys())}')
   "
   ```
7. **Test single execution:**
   ```bash
   # create pipeline from template
   curl -s -X POST http://localhost:8000/api/pipelines/from_template/<template_id> | python -m json.tool
   # execute with seed
   curl -s -X POST http://localhost:8000/api/pipelines/<id>/execute \
     -H 'Content-Type: application/json' \
     -d '{"content": "test input"}' | python -m json.tool
   ```

## Reference Templates

| Template | File | Pattern |
|----------|------|---------|
| JSON Generation | `json_generation.yaml` | StructuredGenerator → JSONValidator |
| Text Classification | `text_classification.yaml` | StructuredGenerator → JSONValidator |
| Q&A Generation | `qa_generation.yaml` | Multiplier → Text → Structured → JSONValidator |
| Data Augmentation | `data_augmentation.yaml` | Sampler → Infiller → DuplicateRemover |
| RAGAS Evaluation | `ragas_evaluation.yaml` | Structured → FieldMapper → RagasMetrics |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Block `type` doesn't match class name | Check `lib/blocks/builtin/` for exact class names |
| Config key doesn't match `__init__` param | Read block source, match parameter names |
| Missing seed variable referenced in prompt | Add the variable to seed metadata |
| MarkdownMultiplierBlock not first | Multiplier blocks must always be first |
| Seed file not named `seed_<template_id>.*` | Template ID must match: `foo.yaml` → `seed_foo.json` |

## Checklist

- [ ] YAML in `lib/templates/` with correct block types and config keys
- [ ] Seed file matching template ID with all referenced variables
- [ ] Template loads via TemplateRegistry
- [ ] Single execution produces expected output fields
- [ ] Trace shows all blocks executed successfully
- [ ] Seed file has 2-3 diverse examples

## Related Skills

- `implementing-datagenflow-blocks` — creating new block types
- `debugging-pipelines` — troubleshooting template execution
- `testing-pipeline-templates` — thorough end-to-end testing
