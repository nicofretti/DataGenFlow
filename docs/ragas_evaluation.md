# RAGAS Evaluation Guide

## Overview

RAGAS (Retrieval Augmented Generation Assessment) is a framework for evaluating the quality of RAG-generated answers. The **RagasMetrics** block evaluates a single QA pair against multiple quality metrics.

## Metrics

### 1. Answer Relevancy
**What it measures**: How relevant the answer is to the question.

**Range**: 0.0 - 1.0 (higher is better)

**Requires**:
- question
- answer
- embeddings (configured via embedding model)

**Example**:
- Question: "What is the capital of France?"
- Answer: "Paris is the capital of France" -> High score (0.9+)
- Answer: "France is a European country" -> Low score (0.3-)

### 2. Faithfulness
**What it measures**: Whether the answer is factually consistent with the provided context.

**Range**: 0.0 - 1.0 (higher is better)

**Requires**:
- question
- answer
- contexts

**Example**:
- Context: "The Eiffel Tower is 330 meters tall"
- Answer: "The Eiffel Tower is 330 meters tall" -> High score (0.9+)
- Answer: "The Eiffel Tower is 500 meters tall" -> Low score (0.3-)

### 3. Context Precision
**What it measures**: Whether the relevant context chunks appear earlier in the context list.

**Range**: 0.0 - 1.0 (higher is better)

**Requires**:
- question
- contexts
- ground_truth

**Example**:
If the most relevant context appears first in the list -> High score
If relevant context is buried at the end -> Low score

### 4. Context Recall
**What it measures**: Whether all information needed to answer the question is present in the contexts.

**Range**: 0.0 - 1.0 (higher is better)

**Requires**:
- question
- contexts
- ground_truth

**Example**:
- Ground truth: "Paris is the capital of France, located on the Seine river"
- Context includes both facts -> High score (1.0)
- Context only includes capital fact -> Lower score (0.5)

## Configuration

### Field References

The block uses field references to locate data in the pipeline state:
- **question_field**: Field containing the question
- **answer_field**: Field containing the answer
- **contexts_field**: Field containing contexts (list of strings)
- **ground_truth_field**: Field containing expected answer

These are dropdowns populated from available pipeline fields, you can use the **FieldMapper** block to rename or create fields as needed (eg. extract fields from nasted structures).

### Selecting Metrics

Use the **metrics** multi-select to choose which metrics to compute:
- Check all metrics you want to evaluate
- Uncheck metrics you don't need
- Note: `answer_relevancy` requires an embedding model

### Score Threshold

The field **score_threshold** is the minimum value for each metric to be considered passing. The block outputs a boolean `passed` indicating if all selected metrics meet or exceed this threshold.


### Model Configuration

- **model**: LLM model for evaluation (leave empty for pipeline default)
- **embedding_model**: Embedding model for answer_relevancy (leave empty for default)

## Output Format

The block outputs a single `ragas_scores` object:

```json
{
  ...
  "ragas_scores": {
    "answer_relevancy": 0.92,
    "faithfulness": 0.88,
    "context_precision": 0.95,
    "context_recall": 0.85,
    "passed": true
  },
}
```
