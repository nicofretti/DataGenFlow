# QADataGen

Minimal library to generate and validate Q&A datasets in JSONL format.

## Quick Start

```bash
# setup
make setup
make dev

# run mock llm (terminal 1)
make mock-llm

# run server (terminal 2)
make run

# open browser
http://localhost:8000
```

## Usage

1. Upload JSON seed file with templates
2. Generate Q&A records via LLM
3. Review and validate records
4. Export to JSONL

## Configuration

Copy `.env.example` to `.env` and configure:
- `LLM_ENDPOINT` - API endpoint (Ollama, OpenAI, etc.)
- `LLM_API_KEY` - API key (optional)
- `LLM_MODEL` - Model name

## Example Seed File

```json
[
  {
    "system": "You are a {role}.",
    "user": "Explain {topic}.",
    "metadata": {
      "role": "teacher",
      "topic": "gravity",
      "num_samples": 3
    }
  }
]
```

See `example_seed.json` for more examples.

## Documentation

- `TESTING.md` - Testing guide
- `plan.md` - Implementation plan
- `point.md` - Project status
