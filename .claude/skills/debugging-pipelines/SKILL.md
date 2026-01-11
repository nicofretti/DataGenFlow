---
name: debugging-pipelines
description: Use when pipelines fail, produce unexpected output, or need systematic troubleshooting
---

# Debugging DataGenFlow Pipelines

## Overview

Systematic debugging workflow for any DataGenFlow pipeline failure or unexpected output. This skill provides a structured four-phase process to identify and fix root causes rather than guessing at solutions.

**Core Principle:** Find the root cause before attempting fixes. Random fixes waste time and create new bugs.

## When to Use

Use this skill when:
- Pipeline execution fails with unclear errors
- Pipeline produces "bad data" or unexpected output
- Need to isolate which block is causing issues
- LLM generates duplicates or poor quality content
- Output has unexpected fields (metadata pollution)
- Results are missing expected fields
- Performance issues or slow execution
- Integration test failures

## When NOT to Use

Skip this skill for:
- Simple configuration errors (typos in config)
- Documentation lookup (how to use a specific block)
- Feature requests (adding new functionality)
- Questions about architecture (use codebase exploration instead)

## The Four-Phase Debugging Process

### Phase 1: Observe & Gather Evidence

**Goal:** Understand what's wrong and collect data

**Steps:**
1. **Run the pipeline and capture full output**
   - Use pytest for tests: `pytest tests/integration/test_X.py -v -s`
   - For API, check logs and response data
   - Save the complete error message and stack trace

2. **Identify what makes output "bad"**
   - Missing fields? (expected `price` but not in output)
   - Wrong values? (all prices are 0)
   - Extra fields? (input metadata leaking: `samples`, `target_count`)
   - Duplicates? (similarity_score = 1.0, exact copies)
   - Type errors? (expected dict, got list)

3. **Check recent changes**
   - Run `git diff` to see what changed
   - Review recent commits that might affect this pipeline
   - Check if tests passed before the change

4. **Review error messages completely**
   - Read the full stack trace, not just the last line
   - Note file paths, line numbers, and error types
   - Check for validation errors with detail context

**Red Flags to Stop:**
- "I think I know the problem" (without evidence)
- "Let me try changing X" (before tracing data flow)
- Skipping logs because "error is obvious"

### Phase 2: Trace Data Flow

**Goal:** Understand how data transforms through the pipeline

**Steps:**
1. **Identify which blocks touch the problematic data**
   - Check pipeline definition (YAML or dict)
   - List all blocks in execution order
   - Note which blocks read/write the affected fields

2. **Read block implementations**
   - Open `lib/blocks/builtin/[block_name].py`
   - Review the `execute()` method
   - Check what inputs it expects and outputs it returns
   - Look for data transformations or filtering logic

3. **Trace data transformation between blocks**
   - Check `lib/workflow.py:_process_single_seed()` for multiplier pipelines
   - See how `accumulated_state` merges block outputs
   - Identify where data gets added, modified, or removed

4. **Check workflow execution flow**
   - Normal pipeline: `lib/workflow.py:85-224`
   - Multiplier pipeline: `lib/workflow.py:305-449`
   - Understand seed processing vs result filtering

**Key Files to Check:**
- `lib/workflow.py` - Pipeline execution engine
- `lib/blocks/builtin/` - All block implementations
- `lib/entities/block_execution_context.py` - Context passed between blocks

### Phase 3: Root Cause Analysis

**Goal:** Form a specific, testable hypothesis

**Steps:**
1. **Form specific hypothesis**
   - Format: "I think X causes Y because Z"
   - Example: "I think input metadata leaks to output because workflow.py line 323 merges all initial_data without filtering"
   - Be specific, not vague

2. **Don't assume - verify with evidence**
   - Read the actual code at the suspected line
   - Check logs or traces confirming the behavior
   - Look for similar patterns in other files

3. **Use logs, traces, and execution results**
   - Check test output for actual vs expected values
   - Review trace data showing block inputs/outputs
   - Examine execution_time for performance issues

**Red Flags:**
- "It's probably just..." (guessing)
- "This usually means..." (pattern matching without verification)
- Proposing fixes before understanding the cause

### Phase 4: Fix & Verify

**Goal:** Implement minimal fix targeting the root cause

**Steps:**
1. **Make minimal fix**
   - Change only what's necessary to fix the root cause
   - Don't refactor or "improve" surrounding code
   - One logical change at a time

2. **Run tests to verify fix**
   - Run the specific failing test
   - Check for test passing
   - Run related tests to catch regressions

3. **Check for side effects**
   - Did the fix break other tests?
   - Are there related features that might be affected?
   - Review the change for unintended consequences

4. **If fix doesn't work**
   - Count: How many fixes have you tried?
   - If < 3: Return to Phase 1, re-analyze with new information
   - If ≥ 3: Question the architecture - might need design discussion

**Success Criteria:**
- Tests pass
- Root cause addressed (not just symptoms)
- No new bugs introduced
- Code follows project guidelines (KISS, minimal changes)

## Common Pipeline Issues

| Issue Pattern | Where to Look | Typical Root Causes | Fix Pattern |
|--------------|---------------|---------------------|-------------|
| Output has unexpected fields | `lib/workflow.py` data merging | Input metadata leaking to output | Filter `initial_data_keys` before returning results |
| Block returns wrong data type | Block's `execute()` method | Incorrect return type (dict vs list) | Fix block to return declared type |
| LLM generates poor quality | Block's prompt building | Unclear instructions, low temperature, copying examples | Improve prompt, add diversity instructions |
| LLM copying examples verbatim | SemanticInfiller prompt | Prompt doesn't emphasize creating NEW content | Add "do NOT copy" instruction to prompt |
| Pipeline crashes on specific input | Block's validation logic | Missing input validation or type checking | Add validation in block's execute() |
| Results missing fields | Block's output filtering or merging | Overly aggressive filtering or incorrect merge | Check field filtering logic |
| All duplicates flagged | DuplicateRemover threshold | Threshold too low or embedding model issues | Check similarity_threshold config |
| Metadata pollution | Workflow seed processing | Initial seed data not filtered from output | Use `_filter_output_data()` helper |

## Critical Files Reference

**Pipeline Execution:**
- `lib/workflow.py:85-224` - Normal pipeline execution flow
- `lib/workflow.py:305-449` - Multiplier pipeline (1→N expansion) with seed processing
- `lib/workflow.py:275-284` - `_filter_output_data()` helper (filters metadata from results)

**Built-in Blocks:**
- `lib/blocks/builtin/structure_sampler.py` - Statistical sampling (multiplier block)
- `lib/blocks/builtin/semantic_infiller.py:59-109` - LLM prompt building
- `lib/blocks/builtin/semantic_infiller.py:146-165` - Metadata filtering in SemanticInfiller
- `lib/blocks/builtin/duplicate_remover.py` - Embedding-based similarity detection

**Core Infrastructure:**
- `lib/entities/block_execution_context.py` - Context passed between blocks
- `lib/blocks/base.py` - BaseBlock interface all blocks inherit from
- `lib/entities/pipeline.py` - ExecutionResult, Usage models
- `lib/template_renderer.py` - Jinja2 template rendering

**Tests:**
- `tests/integration/` - Integration tests for end-to-end verification
- `tests/blocks/` - Unit tests for individual blocks

## Debugging Checklist

Use this checklist to ensure systematic debugging:

```
Phase 1: Observe & Gather Evidence
□ Run pipeline and capture full output
□ Identify specific problem (what's wrong?)
□ Read error messages completely (full stack trace)
□ Check recent git changes (git diff, git log)

Phase 2: Trace Data Flow
□ Check which blocks are in the pipeline
□ Read those block implementations (execute methods)
□ Trace data flow through blocks (accumulated_state)
□ Understand workflow execution (normal vs multiplier)

Phase 3: Root Cause Analysis
□ Form specific hypothesis ("X causes Y because Z")
□ Verify hypothesis with evidence (code, logs, traces)
□ Don't assume - read actual code
□ Check for similar patterns elsewhere

Phase 4: Fix & Verify
□ Make minimal fix targeting root cause
□ Run tests to verify fix works
□ Check for unintended side effects
□ Follow project guidelines (KISS, simplicity)
```

## Real-World Example: Data Augmentation Metadata Pollution

**Problem Observed:**
Pipeline output contained input configuration fields (`samples`, `target_count`, `categorical_fields`) mixed with generated data.

**Phase 1 - Evidence:**
```json
// Expected output:
{"category": "electronics", "price": 449, "description": "...", "is_duplicate": false}

// Actual output:
{"category": "electronics", "price": 449, "description": "...",
 "samples": [...], "target_count": 10, "categorical_fields": [...]}  // ❌ Bad!
```

**Phase 2 - Trace:**
- Traced workflow.py seed processing
- Found `merged_state = {**initial_data, **seed_data}` at line 323
- Merged state flows through all blocks
- No filtering before returning results

**Phase 3 - Root Cause:**
Hypothesis: "Input metadata leaks to output because workflow.py merges all initial_data into accumulated_state without filtering configuration fields before returning results"

**Phase 4 - Fix:**
1. Added `_filter_output_data()` helper method
2. Track `initial_data_keys` at merge time
3. Filter those keys before returning `ExecutionResult`
4. Tests passed, metadata removed from output

**Lessons:**
- Data flow tracing revealed the merge point
- Minimal fix (filter helper) solved the root cause
- No refactoring needed - targeted change only

## Tips for Effective Debugging

1. **Start with the simplest explanation**
   - Don't assume complex bugs when simple causes are more likely
   - Check configuration before code logic

2. **Use the scientific method**
   - Observe → Hypothesize → Test → Verify
   - One variable at a time

3. **Trust but verify**
   - Don't trust assumptions about what code does
   - Read the actual implementation

4. **Leverage existing patterns**
   - Look for similar working code in the codebase
   - Compare broken vs working implementations

5. **Document as you go**
   - Keep notes on what you've checked
   - Record hypotheses and test results
   - Helps if you need to ask for help

## Related Skills

- `implementing-datagenflow-blocks` - For understanding block structure and creation
- `address-pr-review` - For evaluating whether debugging revealed design issues
