---
title: Extensibility System
description: Use DataGenFlow without cloning it — add custom blocks and templates from your own repo
---

# Extensibility System

DataGenFlow's extensibility system lets engineers consume DataGenFlow as a Docker image and maintain custom blocks and templates in their own repositories.

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Writing Custom Blocks](#writing-custom-blocks)
  - [Block with Dependencies](#block-with-dependencies)
  - [Block Discovery](#block-discovery)
- [Writing Custom Templates](#writing-custom-templates)
- [CLI Reference](#cli-reference)
  - [Status](#status)
  - [Blocks Commands](#blocks-commands)
  - [Templates Commands](#templates-commands)
  - [Image Commands](#image-commands)
  - [Configuration](#configuration)
- [Hot Reload](#hot-reload)
- [Extensions API](#extensions-api)
- [Extensions Page](#extensions-page)
- [Docker Setup](#docker-setup)
- [Building Custom Images](#building-custom-images)
- [Troubleshooting](#troubleshooting)

## Overview

Instead of cloning the DataGenFlow repository, engineers:

1. Pull the official Docker image
2. Mount custom `user_blocks/` and `user_templates/` directories
3. Manage extensions with the `dgf` CLI or the Extensions UI page

```text
your-repo/
  user_blocks/
    sentiment_analyzer.py
    translator.py
  user_templates/
    my_qa_pipeline.yaml
  docker-compose.yml
  .env
```

The system provides:
- **Block registry** with source tracking (`builtin`, `custom`, `user`)
- **Dependency declaration** via class attribute on blocks
- **Hot reload** via file watcher (watchdog) with 500ms debounce
- **CLI tool** (`dgf`) for managing blocks, templates, and images
- **Extensions page** in the frontend showing all blocks and templates with status

## Quick Start

```bash
# 1. start DataGenFlow with mounted directories
docker-compose up -d

# 2. scaffold a block
dgf blocks scaffold SentimentAnalyzer -c validators

# 3. move it to user_blocks (hot reload picks it up)
mv sentiment_analyzer.py user_blocks/

# 4. check it's registered
dgf blocks list

# 5. open the Extensions page in the UI
open http://localhost:8000
```

## Writing Custom Blocks

Custom blocks follow the same `BaseBlock` interface as builtin blocks. See [How to Create Custom Blocks](how_to_create_blocks) for the full guide.

### Block with Dependencies

Blocks can declare pip dependencies via a `dependencies` class attribute. Missing dependencies are detected at registration time, and the block appears as "unavailable" in the UI with an actionable error.

```python
from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext
from typing import Any


class SentimentAnalyzer(BaseBlock):
    name = "Sentiment Analyzer"
    description = "Analyze text sentiment using transformers"
    category = "validators"
    inputs = ["text"]
    outputs = ["sentiment", "confidence"]

    # declare pip dependencies
    dependencies = ["transformers>=4.30.0", "torch>=2.0.0"]

    def __init__(self, model: str = "distilbert-base-uncased"):
        self.model = model
        self._pipeline = None

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        if self._pipeline is None:
            from transformers import pipeline
            self._pipeline = pipeline("sentiment-analysis", model=self.model)

        text = context.get_state("text", "")
        result = self._pipeline(text)[0]

        return {
            "sentiment": result["label"],
            "confidence": result["score"],
        }
```

Install missing dependencies via CLI or the Extensions page:

```bash
dgf blocks list                                    # see which blocks are unavailable
# POST /api/extensions/blocks/SentimentAnalyzer/install-deps
```

### Block Discovery

Blocks are discovered from three directories:

| Directory | Source Label | Purpose |
|-----------|-------------|---------|
| `lib/blocks/builtin/` | `builtin` | Ships with DataGenFlow |
| `lib/blocks/custom/` | `custom` | Project-specific blocks |
| `user_blocks/` | `user` | User-mounted blocks (extensibility) |

Any `.py` file (not starting with `_`) containing a `BaseBlock` subclass is auto-discovered. The `user_blocks/` path is configurable via the `DATAGENFLOW_BLOCKS_PATH` environment variable.

## Writing Custom Templates

Templates are YAML files that define pre-configured pipelines.

```yaml
name: "My QA Pipeline"
description: "Generate question-answer pairs from content"

blocks:
  - type: TextGenerator
    config:
      model: "gpt-4o-mini"
      user_prompt: |
        Generate a question-answer pair from:
        {{ content }}
```

Place templates in `user_templates/` (or the path set by `DATAGENFLOW_TEMPLATES_PATH`). They appear in the Templates section of the UI and CLI.

> **Note:** If a user template has the same ID (filename stem) as a builtin template, the builtin takes precedence and the user template is skipped.

## CLI Reference

The `dgf` CLI communicates with a running DataGenFlow instance over HTTP. Install it with:

```bash
pip install datagenflow  # includes the dgf CLI
```

### Status

```bash
dgf status
```

Shows server health, block counts, template counts, and hot reload status.

### Blocks Commands

```bash
dgf blocks list                          # list all blocks with status and source
dgf blocks validate ./my_block.py        # check syntax and find block classes
dgf blocks scaffold MyBlock -c general   # generate a starter block file
```

### Templates Commands

```bash
dgf templates list                       # list all templates with source
dgf templates validate ./flow.yaml       # check YAML structure and required fields
dgf templates scaffold "My Flow"         # generate a starter template YAML
```

### Image Commands

```bash
dgf image scaffold --blocks-dir ./user_blocks  # generate Dockerfile with deps
dgf image build -t my-datagenflow:latest       # build custom Docker image
```

The scaffold command parses `dependencies` attributes from block files and generates a `Dockerfile.custom` with the right `uv pip install` commands.

### Configuration

```bash
dgf configure --show                     # show current endpoint
dgf configure --endpoint https://my-server:8000
```

Configuration resolution order:
1. `DATAGENFLOW_ENDPOINT` environment variable (highest priority)
2. `.env` file in current directory
3. Default: `http://localhost:8000`

## Hot Reload

The file watcher monitors `user_blocks/` and `user_templates/` for changes. When a file is created, modified, or deleted:

- **Blocks**: The block registry re-scans all directories
- **Templates**: The specific template is registered or unregistered

Events are debounced at 500ms (configurable via `DATAGENFLOW_HOT_RELOAD_DEBOUNCE_MS`) to handle rapid saves.

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DATAGENFLOW_HOT_RELOAD` | `true` | Enable/disable file watching |
| `DATAGENFLOW_HOT_RELOAD_DEBOUNCE_MS` | `500` | Debounce interval in milliseconds |

> **Tip:** Set `DATAGENFLOW_HOT_RELOAD=false` in production to avoid unnecessary file system overhead.

## Extensions API

All extension endpoints live under `/api/extensions/`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/extensions/status` | Block/template counts, hot reload status |
| `GET` | `/api/extensions/blocks` | List all blocks with source and availability |
| `GET` | `/api/extensions/templates` | List all templates with source |
| `POST` | `/api/extensions/reload` | Trigger manual reload of all extensions |
| `POST` | `/api/extensions/blocks/{name}/validate` | Validate block availability and dependencies |
| `GET` | `/api/extensions/blocks/{name}/dependencies` | Get dependency info for a block |
| `POST` | `/api/extensions/blocks/{name}/install-deps` | Install missing dependencies via uv |

**Example response** — `GET /api/extensions/status`:

```json
{
  "blocks": {
    "total": 14,
    "builtin_blocks": 12,
    "custom_blocks": 0,
    "user_blocks": 2,
    "available": 13,
    "unavailable": 1
  },
  "templates": {
    "total": 6,
    "builtin_templates": 4,
    "user_templates": 2
  }
}
```

## Extensions Page

The Extensions page (`/extensions`) in the frontend shows:

- **Status cards** with block and template counts by source
- **Block list** with availability status, source badges, and dependency info
- **Template list** with source badges
- **Reload button** to trigger a manual re-scan of all extension directories

Unavailable blocks are highlighted with a red border and display the error message (e.g., "Missing dependencies: torch").

## Docker Setup

Minimal `docker-compose.yml` for using DataGenFlow with extensions:

```yaml
services:
  datagenflow:
    image: datagenflow/datagenflow:latest
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
```

**Environment variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `DATAGENFLOW_ENDPOINT` | `http://localhost:8000` | API endpoint (for CLI) |
| `DATAGENFLOW_BLOCKS_PATH` | `user_blocks` | Path to user blocks directory |
| `DATAGENFLOW_TEMPLATES_PATH` | `user_templates` | Path to user templates directory |
| `DATAGENFLOW_HOT_RELOAD` | `true` | Enable file watching |

## Building Custom Images

For production, pre-bake dependencies into the image to avoid runtime installs:

```bash
# 1. generate Dockerfile with dependencies from your blocks
dgf image scaffold --blocks-dir ./user_blocks

# 2. build the image
dgf image build -t my-datagenflow:latest

# 3. use it in docker-compose
# image: my-datagenflow:latest
```

The generated `Dockerfile.custom` extends the base image and runs `uv pip install` for all declared dependencies.

## Troubleshooting

### Block not appearing in UI

- **Cause**: File not in a discovered directory, or class doesn't inherit from `BaseBlock`
- **Fix**: Verify the file is in `user_blocks/`, the filename doesn't start with `_`, and the class inherits from `BaseBlock`

### Block shows as unavailable

- **Cause**: Missing pip dependencies declared in `dependencies` attribute
- **Fix**: Install via `POST /api/extensions/blocks/{name}/install-deps` or build a custom image with pre-baked dependencies

### Hot reload not working

- **Cause**: `DATAGENFLOW_HOT_RELOAD=false` or directory doesn't exist at startup
- **Fix**: Check the environment variable and ensure `user_blocks/` and `user_templates/` exist before the server starts

### CLI cannot connect

- **Cause**: Wrong endpoint or server not running
- **Fix**: Run `dgf configure --show` to check the endpoint, then `dgf status` to test connectivity

### User template ignored

- **Cause**: Template ID (filename stem) conflicts with a builtin template
- **Fix**: Rename the template file to avoid the collision. Check server logs for "skipped: conflicts with builtin" warnings.
