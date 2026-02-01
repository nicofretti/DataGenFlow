---
name: testing-pipeline-templates
description: Use when testing pipelines end-to-end - running single-seed dry runs, batch generation, result analysis, and iterating on prompt quality. Use after creating a pipeline template, when validating output quality, or when improving generation results. Not for debugging crashes (use debugging-pipelines instead).
---

# Testing Pipeline Templates

Three-phase process: dry run → batch → quality iteration.

## Phase 1: Dry Run (Single Seed)

Verify the pipeline executes and produces structurally correct output.

```bash
# list pipelines
curl -s http://localhost:8000/api/pipelines | python -m json.tool

# validate seeds against pipeline
curl -s -X POST http://localhost:8000/api/seeds/validate \
  -H 'Content-Type: application/json' \
  -d '{"pipeline_id": <ID>, "seeds": [{"repetitions": 1, "metadata": {"content": "test"}}]}' \
  | python -m json.tool

# execute single seed
curl -s -X POST http://localhost:8000/api/pipelines/<ID>/execute \
  -H 'Content-Type: application/json' \
  -d '{"content": "test input"}' | python -m json.tool
```

**Analyze the response:**
- `result` — expected output fields present?
- `trace` — each entry has `block_type`, `execution_time`, `output`
- `accumulated_state` — data flowing correctly between blocks?

**Red flags:** missing fields, metadata pollution (extra fields like `samples`, `target_count`), execution_time >30s, empty/null generator outputs.

## Phase 2: Small Batch

Check output consistency and diversity across multiple seeds.

```bash
# prepare diverse seed file (3-5 seeds)
cat > test_seeds.json << 'EOF'
[
  {"repetitions": 2, "metadata": {"content": "topic A"}},
  {"repetitions": 2, "metadata": {"content": "topic B"}},
  {"repetitions": 1, "metadata": {"content": "edge case"}}
]
EOF

# start batch job
curl -s -X POST http://localhost:8000/api/generate \
  -F "pipeline_id=<ID>" -F "file=@test_seeds.json" | python -m json.tool

# monitor (poll until status=completed)
curl -s http://localhost:8000/api/jobs/<JOB_ID> | python -m json.tool

# review all records
curl -s "http://localhost:8000/api/records?job_id=<JOB_ID>" | python -m json.tool
```

**Analyze patterns:** output diversity, consistent field structure, validation pass/fail rates, common failure patterns.

## Phase 3: Quality Iteration

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| Outputs too similar | Low temperature or repetitive prompt | Increase temperature (0.8-1.0), add diversity instruction |
| Missing JSON fields | Schema not enforced | Add `required` in JSON schema, use `strict: true` |
| Outputs too short | max_tokens too low or vague prompt | Increase max_tokens, add length guidance |
| Outputs off-topic | Prompt too vague | Add specific constraints and examples |
| Validation always fails | Rules too strict | Relax min_length, check forbidden_words |
| LLM ignoring schema | Model doesn't support structured output | Try different model, simplify schema |

**Iteration loop:**
1. Identify weakest block from traces
2. Adjust ONE thing (prompt, temperature, schema, or validation rules)
3. Re-run single seed → verify improvement
4. Re-run small batch → confirm consistency
5. Repeat

**Prompt tips:**
- Be specific: "Generate a 2-3 sentence description" not "Generate a description"
- Add examples in system prompt for few-shot guidance
- Use constraints: "Do not include personal opinions"
- Reference state: "Based on: {{ content }}"

## Cleanup

```bash
curl -s -X DELETE "http://localhost:8000/api/records?job_id=<JOB_ID>"
curl -s -X DELETE http://localhost:8000/api/pipelines/<ID>
```

## Key Endpoints

| Action | Method | Endpoint |
|--------|--------|----------|
| List pipelines | GET | `/api/pipelines` |
| Execute single | POST | `/api/pipelines/{id}/execute` |
| Validate seeds | POST | `/api/seeds/validate` |
| Start batch | POST | `/api/generate` |
| Job status | GET | `/api/jobs/{id}` |
| List records | GET | `/api/records?job_id={id}` |
| Delete records | DELETE | `/api/records?job_id={id}` |
| Export JSONL | GET | `/api/export?job_id={id}` |

## Related Skills

- `creating-pipeline-templates` — build the template first
- `debugging-pipelines` — when execution fails with errors
- `configuring-models` — set up LLM/embedding providers
