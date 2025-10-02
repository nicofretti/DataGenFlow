# Testing Guide

## Quick Start with Mock LLM

### 1. Setup
```bash
make setup  # creates .env and data/ directory
make dev    # install dependencies
```

### 2. Start Mock LLM Server (Terminal 1)
```bash
make mock-llm
```
Mock server runs on `http://localhost:11434` and responds to any prompt with a simple test response.

### 3. Start QADataGen Server (Terminal 2)
```bash
make run
```
Server runs on `http://localhost:8000`

### 4. Test via Web UI
1. Open browser: `http://localhost:8000`
2. Go to "Generator" tab
3. Upload `example_seed.json`
4. Click "Generate"
5. Go to "Reviewer" tab to see generated records
6. Accept/Reject/Edit records
7. Go to "Exporter" tab to download JSONL

### 5. Test via API
```bash
# generate records
curl -X POST http://localhost:8000/generate \
  -F "file=@example_seed.json"

# list records
curl http://localhost:8000/records

# get single record
curl http://localhost:8000/records/1

# update record status
curl -X PUT http://localhost:8000/records/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "accepted"}'

# export jsonl
curl http://localhost:8000/export?status=accepted
```

## Testing with Real LLM

### Ollama
1. Install and start Ollama: `ollama serve`
2. Pull model: `ollama pull llama3`
3. Update `.env`:
   ```
   LLM_ENDPOINT=http://localhost:11434/api/generate
   LLM_MODEL=llama3
   ```
4. Run: `make run`

### OpenAI
1. Get API key from OpenAI
2. Update `.env`:
   ```
   LLM_ENDPOINT=https://api.openai.com/v1/chat/completions
   LLM_API_KEY=sk-...
   LLM_MODEL=gpt-4
   ```
3. Run: `make run`

## Testing Validation Rules

Create custom validator:
```python
from lib.validator import Validator, min_length, no_forbidden_words

validator = Validator()
validator.add_rule(min_length("assistant", 50))
validator.add_rule(no_forbidden_words("assistant", ["sorry", "cannot"]))

# use in pipeline
pipeline = Pipeline(storage, validator=validator)
```

## Expected Behavior

### Successful Generation
- Mock server returns: "this is a mock response to: {user_question}"
- Records saved with status "pending"
- Can review in UI
- Can export as JSONL

### Generation Stats
For `example_seed.json`:
- Seed 1: 2 samples (physics/gravity)
- Seed 2: 3 samples (machine learning)
- Total: 5 records generated

## Troubleshooting

### Mock server not responding
- Check port 11434 is free: `lsof -i :11434`
- Try different port in mock_llm.py and .env

### No records generated
- Check logs in terminal running `make run`
- Verify .env has correct LLM_ENDPOINT
- Test mock server: `curl http://localhost:11434/api/generate -d '{"model":"test","prompt":"hello","stream":false}'`

### Database errors
- Delete and recreate: `make clean && make setup`
- Check data/ directory permissions

## Code Quality Checks

```bash
make format    # format code with ruff
make lint      # check linting
make typecheck # run mypy
```
