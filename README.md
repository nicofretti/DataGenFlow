# QADataGen

Minimal CLI tool to generate and validate Q&A datasets in JSONL format.

## Quick Start

```bash
# setup
make setup
make dev

# run mock llm (terminal 1)
make mock-llm

# generate records (terminal 2)
python3 cli.py generate example_seed.json

# list records
python3 cli.py list

# update record status
python3 cli.py update 1 accepted

# export to jsonl
python3 cli.py export output.jsonl --status accepted
```

## CLI Commands

### Generate
```bash
python3 cli.py generate <seed_file> [options]
  --model MODEL          LLM model name
  --endpoint URL         LLM endpoint
  --temperature FLOAT    Temperature (default: 0.7)
  --max-tokens INT       Max tokens
```

### List
```bash
python3 cli.py list [options]
  --status STATUS        Filter by status (pending/accepted/rejected/edited)
  --limit INT            Max records (default: 10)
  --offset INT           Offset (default: 0)
```

### Update
```bash
python3 cli.py update <record_id> <status>
  status: accepted/rejected/edited
```

### Export
```bash
python3 cli.py export <output_file> [options]
  --status STATUS        Filter by status
```

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
