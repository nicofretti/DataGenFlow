---
title: Claude Code Skills
description: Built-in skills that guide Claude Code through common DataGenFlow workflows
---

# Claude Code Skills

DataGenFlow includes built-in [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills) that provide step-by-step guidance for common workflows. Skills activate automatically when Claude Code detects a matching task.

## Table of Contents
- [Available Skills](#available-skills)
- [How Skills Work](#how-skills-work)
- [Skill Reference](#skill-reference)
  - [Creating Pipeline Templates](#creating-pipeline-templates)
  - [Testing Pipeline Templates](#testing-pipeline-templates)
  - [Configuring Models](#configuring-models)
  - [Implementing Blocks](#implementing-blocks)
  - [Debugging Pipelines](#debugging-pipelines)
  - [Writing E2E Tests](#writing-e2e-tests)

## Available Skills

| Skill | Triggers When You... |
|-------|---------------------|
| `creating-pipeline-templates` | Create or modify YAML templates and seed files in `lib/templates/` |
| `testing-pipeline-templates` | Test a pipeline end-to-end, analyze results, or iterate on quality |
| `configuring-models` | Set up LLM or embedding models (OpenAI, Anthropic, Gemini, Ollama) |
| `implementing-datagenflow-blocks` | Create or modify pipeline blocks in `lib/blocks/builtin/` |
| `debugging-pipelines` | Troubleshoot pipeline failures or unexpected output |
| `writing-e2e-tests` | Write Playwright e2e tests for the UI |

## How Skills Work

Skills live in `.claude/skills/` as `SKILL.md` files. When you describe a task in Claude Code, the matching skill loads automatically and guides the session with:

- **Workflows** — step-by-step procedures for the task
- **Code patterns** — correct usage of DataGenFlow APIs and conventions
- **Checklists** — verification steps before considering the task done
- **Common mistakes** — known pitfalls and their fixes

No manual activation needed. Just describe what you want to do.

## Skill Reference

### Creating Pipeline Templates

**Location:** `.claude/skills/creating-pipeline-templates/`

Guides through creating YAML pipeline definitions and seed files. Covers:

- Template YAML format and block configuration
- Available blocks (14 total) with inputs/outputs
- Common pipeline patterns (generation, validation, augmentation)
- Seed file format (JSON and Markdown)
- Validation via TemplateRegistry

**Example trigger:** "Create a pipeline template for generating product reviews"

### Testing Pipeline Templates

**Location:** `.claude/skills/testing-pipeline-templates/`

Three-phase testing process for pipelines:

1. **Dry run** — single-seed execution, trace analysis
2. **Small batch** — 3-5 seeds, consistency and diversity check
3. **Quality iteration** — identify weak blocks, adjust prompts/config, re-test

**Example trigger:** "Test the json_generation template end to end"

### Configuring Models

**Location:** `.claude/skills/configuring-models/`

Provider-specific setup for LLM and embedding models:

- **OpenAI** — no endpoint needed, `sk-...` API key
- **Anthropic** — no endpoint needed, `sk-ant-...` API key, no embeddings
- **Gemini** — no endpoint needed, API key from AI Studio
- **Ollama** — endpoint required (`http://localhost:11434`), no API key

Includes connection testing, model resolution order, and troubleshooting.

**Example trigger:** "Set up Ollama as my LLM provider"

### Implementing Blocks

**Location:** `.claude/skills/implementing-datagenflow-blocks/`

Complete reference for creating pipeline blocks:

- Block structure (`BaseBlock`, `BaseMultiplierBlock`)
- UI integration patterns (model dropdowns, enum selectors, template editors)
- LLM and embedding integration via `llm_config_manager`
- State management and trace_id-keyed caching
- Unit testing patterns

**Example trigger:** "Create a new block that summarizes text"

### Debugging Pipelines

**Location:** `.claude/skills/debugging-pipelines/`

Four-phase systematic debugging:

1. **Observe** — gather evidence, read full errors
2. **Trace** — follow data flow through blocks
3. **Analyze** — form testable hypothesis
4. **Fix** — minimal targeted change, verify

**Example trigger:** "My pipeline output has unexpected fields"

### Writing E2E Tests

**Location:** `.claude/skills/writing-e2e-tests/`

Playwright test patterns for the DataGenFlow UI:

- Test file template with sync API and cleanup fixtures
- Navigation, file upload, and modal interaction patterns
- Common UI selectors for all pages
- Integration with `run_all_tests.sh`

**Example trigger:** "Write e2e tests for the settings page"
