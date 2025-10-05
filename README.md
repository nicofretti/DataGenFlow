# QADataGen

Q&A dataset generation tool with block-based pipeline system.

## Quick Start

```bash
# setup
make setup
make dev

# open browser
# http://localhost:8000
```

## Features

- **Block-based pipelines**: compose workflows from reusable blocks
- **Execution tracing**: debug pipelines with full state history
- **Pipeline output**: flexible visualization control
- **Built-in blocks**: llm, transformer, validator, formatter
- **Custom blocks**: easy extension with auto-discovery
- **Web UI**: react frontend for pipeline building and review

## Configuration

copy `.env.example` to `.env`:

```bash
LLM_ENDPOINT=http://localhost:11434/v1  # ollama, openai, etc
LLM_API_KEY=optional
LLM_MODEL=llama3.2
DATABASE_PATH=data/records.db
```

## Architecture

```
lib/blocks/
  builtin/      # stable blocks (llm, transformer, validator, formatter)
  custom/       # experimental blocks
  base.py       # baseblock interface
  registry.py   # auto-discovery

frontend/       # react + primer ui
  src/pages/
    Builder.tsx     # visual pipeline builder
    Pipelines.tsx   # pipeline manager
    Generator.tsx   # dataset generation
    Review.tsx      # review records

tests/          # pytest
```

## Creating Custom Blocks

create file in `lib/blocks/custom/` or `user_blocks/`:

```python
from lib.blocks.base import BaseBlock
from typing import Any

class MyBlock(BaseBlock):
    name = "my block"
    description = "does something"
    inputs = ["text"]
    outputs = ["result"]

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        return {"result": data["text"].upper()}
```

auto-discovered on startup, available in ui immediately.

## Testing

```bash
# run all tests
make test

# run specific tests
uv run pytest tests/blocks/ -v
uv run pytest tests/test_api.py -v
```

## Development

```bash
# backend
make run

# frontend dev
cd frontend && yarn dev

# type checking
make typecheck

# linting
make lint
```
