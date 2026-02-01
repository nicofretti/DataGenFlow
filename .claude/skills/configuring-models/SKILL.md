---
name: configuring-models
description: Use when setting up LLM or embedding models in DataGenFlow via Settings page or API. Guides through provider-specific configuration for OpenAI, Anthropic, Gemini, and Ollama. Use for first-time setup, adding new providers, troubleshooting connection failures, or migrating from .env fallback to proper model configs.
---

# Configuring Models in DataGenFlow

DataGenFlow uses LiteLLM under the hood. Models configured via Settings UI or REST API.

## Model Config Fields

**LLM:** `name`, `provider` (openai|anthropic|gemini|ollama), `model_name`, `endpoint`, `api_key`
**Embedding:** same + `dimensions` (0 = provider default)

**Critical:** `model_name` is the raw model name WITHOUT provider prefix. LiteLLM adds prefixes automatically.

## Provider Setup

### OpenAI

```bash
# LLM
curl -X POST http://localhost:8000/api/llm-models -H 'Content-Type: application/json' -d '{
  "name": "default", "provider": "openai",
  "model_name": "gpt-4o-mini", "api_key": "sk-..."
}'

# Embedding
curl -X POST http://localhost:8000/api/embedding-models -H 'Content-Type: application/json' -d '{
  "name": "default", "provider": "openai",
  "model_name": "text-embedding-3-small", "api_key": "sk-...", "dimensions": 1536
}'
```

- No endpoint needed. LiteLLM passes model name as-is.
- LLMs: `gpt-4o`, `gpt-4o-mini`
- Embeddings: `text-embedding-3-small` (1536d), `text-embedding-3-large` (3072d)

### Anthropic

```bash
# LLM only — Anthropic has NO embedding models
curl -X POST http://localhost:8000/api/llm-models -H 'Content-Type: application/json' -d '{
  "name": "default", "provider": "anthropic",
  "model_name": "claude-sonnet-4-20250514", "api_key": "sk-ant-..."
}'
```

- No endpoint needed. LiteLLM adds `anthropic/` prefix.
- LLMs: `claude-sonnet-4-20250514`, `claude-opus-4-20250514`
- **No embedding models** — use OpenAI or Ollama for embeddings.

### Gemini

```bash
# LLM
curl -X POST http://localhost:8000/api/llm-models -H 'Content-Type: application/json' -d '{
  "name": "default", "provider": "gemini",
  "model_name": "gemini-2.0-flash", "api_key": "AIza..."
}'

# Embedding
curl -X POST http://localhost:8000/api/embedding-models -H 'Content-Type: application/json' -d '{
  "name": "default", "provider": "gemini",
  "model_name": "text-embedding-004", "api_key": "AIza...", "dimensions": 768
}'
```

- No endpoint needed. API key from Google AI Studio. LiteLLM adds `gemini/` prefix.
- LLMs: `gemini-2.0-flash`, `gemini-1.5-pro`

### Ollama

```bash
# LLM
curl -X POST http://localhost:8000/api/llm-models -H 'Content-Type: application/json' -d '{
  "name": "default", "provider": "ollama",
  "model_name": "llama3.2", "endpoint": "http://localhost:11434"
}'

# Embedding
curl -X POST http://localhost:8000/api/embedding-models -H 'Content-Type: application/json' -d '{
  "name": "default", "provider": "ollama",
  "model_name": "nomic-embed-text", "endpoint": "http://localhost:11434", "dimensions": 768
}'
```

- **Endpoint required.** No API key.
- LiteLLM adds `ollama/` prefix, strips `/v1/*` from endpoint.
- Pull models first: `ollama pull llama3.2`
- LLMs: `llama3.2`, `mistral`, `codellama`
- Embeddings: `nomic-embed-text`, `mxbai-embed-large`

## Testing Connections

```bash
# test LLM (sends "Say hello", max_tokens=10, timeout=10s)
curl -X POST http://localhost:8000/api/llm-models/test -H 'Content-Type: application/json' -d '{
  "name": "test", "provider": "openai", "model_name": "gpt-4o-mini", "api_key": "sk-..."
}'

# test embedding (sends "test" string)
curl -X POST http://localhost:8000/api/embedding-models/test -H 'Content-Type: application/json' -d '{
  "name": "test", "provider": "openai", "model_name": "text-embedding-3-small", "api_key": "sk-...", "dimensions": 1536
}'
```

**Via UI:** Settings page → click **Test** button next to any model.

## Model Resolution Order

When a block doesn't specify a model:
1. Named model (block config `model: "my-model"`)
2. Model named `"default"`
3. First model in DB
4. `.env` fallback: `LLM_ENDPOINT` + `LLM_MODEL` + `LLM_API_KEY` (LLM only)

**Recommendation:** always create a model named `"default"`.

## Minimum Setup

- **1 LLM model** — required for any pipeline
- **1 embedding model** — recommended (needed by DuplicateRemover block)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Missing endpoint for Ollama | Set `endpoint` to `http://localhost:11434` |
| Adding provider prefix to model name | Use `gpt-4o` not `openai/gpt-4o` — LiteLLM adds prefixes |
| Wrong API key format | OpenAI: `sk-...`, Anthropic: `sk-ant-...`, Gemini: `AIza...` |
| Ollama model not pulled | Run `ollama pull <model>` before configuring |
| No default model | Name at least one model `"default"` |
| Using Anthropic for embeddings | Anthropic has no embedding API — use OpenAI or Ollama |

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| Connection refused | Ollama not running or wrong endpoint | `ollama serve`, verify port |
| 401 / auth error | Invalid or expired API key | Check key format and provider match |
| Model not found | Wrong name or not pulled (Ollama) | Verify spelling, `ollama pull` if local |
| Timeout | Slow network or model loading | Retry; Ollama first request loads model into memory |

## API Reference

| Method | Endpoint |
|--------|----------|
| GET | `/api/llm-models` |
| POST | `/api/llm-models` |
| PUT | `/api/llm-models/{name}` |
| DELETE | `/api/llm-models/{name}` |
| POST | `/api/llm-models/test` |
| GET | `/api/embedding-models` |
| POST | `/api/embedding-models` |
| PUT | `/api/embedding-models/{name}` |
| DELETE | `/api/embedding-models/{name}` |
| POST | `/api/embedding-models/test` |

## Related Skills

- `implementing-datagenflow-blocks` — LLM/embedding integration patterns in blocks
- `creating-pipeline-templates` — templates that use configured models
