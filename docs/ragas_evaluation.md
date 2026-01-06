# RAGAS Evaluation Guide

## Overview

RAGAS (Retrieval Augmented Generation Assessment) is a framework for evaluating the quality of generated QA pairs. The **Ragas Batch Metrics** block automatically assesses your QA datasets using multiple quality metrics.

## Metrics

### 1. Answer Relevancy
**What it measures**: How relevant the answer is to the question.

**Range**: 0.0 - 1.0 (higher is better)

**Requires**:
- question
- answer
- embeddings (automatically configured based on your LLM provider)

**Example**:
- Question: "What is the capital of France?"
- Answer: "Paris is the capital of France" → High score (0.9+)
- Answer: "France is a European country" → Low score (0.3-)

### 2. Faithfulness
**What it measures**: Whether the answer is factually consistent with the provided context.

**Range**: 0.0 - 1.0 (higher is better)

**Requires**:
- question
- answer
- contexts

**Example**:
- Context: "The Eiffel Tower is 330 meters tall"
- Answer: "The Eiffel Tower is 330 meters tall" → High score (0.9+)
- Answer: "The Eiffel Tower is 500 meters tall" → Low score (0.3-)

### 3. Context Precision
**What it measures**: Whether the relevant context chunks appear earlier in the context list.

**Range**: 0.0 - 1.0 (higher is better)

**Requires**:
- question
- contexts
- ground_truth

**Example**:
If the most relevant context appears first in the list → High score
If relevant context is buried at the end → Low score

### 4. Context Recall
**What it measures**: Whether all information needed to answer the question is present in the contexts.

**Range**: 0.0 - 1.0 (higher is better)

**Requires**:
- question
- contexts
- ground_truth

**Example**:
- Ground truth: "Paris is the capital of France, located on the Seine river"
- Context includes both facts → High score (1.0)
- Context only includes capital fact → Lower score (0.5)

## Configuration

### Basic Setup

1. Add the **Ragas Batch Metrics** block to your pipeline
2. Connect it after your QA pair generation/extraction blocks
3. Input field: `parsed_json` (expects a dict with `qa_pairs` array)

### Selecting Metrics

Use the **metrics** multi-select to choose which metrics to compute:
- Check all metrics you want to evaluate
- Uncheck metrics you don't need
- Note: `answer_relevancy` requires embeddings

### Quality Flagging

Enable automatic quality detection:

1. **flag_low_scores**: Check this to enable flagging
2. **score_threshold**: Set minimum acceptable score (0.0-1.0)
   - Default: 0.5
   - Recommended: 0.7 for production datasets

When enabled, each QA pair gets:
- `low_quality` (boolean): True if ANY score is below threshold
- `below_threshold` (object): Shows which specific metrics failed

### Provider Support

The block automatically works with any LLM provider configured in Settings:

**Gemini**:
- LLM: ✅ Gemini models
- Embeddings: ✅ Google embeddings (models/embedding-001)

**OpenAI**:
- LLM: ✅ OpenAI models
- Embeddings: ✅ OpenAI embeddings

**Ollama**:
- LLM: ✅ Local models
- Embeddings: ✅ Local embeddings (nomic-embed-text)

**Anthropic**:
- LLM: ✅ Claude models
- Embeddings: ⚠️ Requires OPENAI_API_KEY env var

## Output Format

```json
{
  "qa_pairs_with_scores": [
    {
      "question": "What is photosynthesis?",
      "answer": "Photosynthesis is the process by which plants convert light into energy.",
      "ground_truth": "Photosynthesis converts sunlight to chemical energy.",
      "contexts": [
        "Plants use photosynthesis to create glucose from sunlight."
      ],
      "scores": {
        "answer_relevancy_score": 0.92,
        "faithfulness_score": 0.88,
        "context_precision_score": 0.95,
        "context_recall_score": 0.85
      },
      "low_quality": false,
      "below_threshold": {
        "answer_relevancy_score": false,
        "faithfulness_score": false,
        "context_precision_score": false,
        "context_recall_score": false
      }
    }
  ]
}
```

## Interpreting Scores

### Score Ranges

- **0.9 - 1.0**: Excellent quality
- **0.7 - 0.9**: Good quality
- **0.5 - 0.7**: Acceptable (may need review)
- **0.3 - 0.5**: Poor quality (needs improvement)
- **0.0 - 0.3**: Very poor quality (regenerate recommended)

### Recommended Thresholds

- **Production datasets**: 0.7+
- **Development/testing**: 0.5+
- **Research/experimental**: 0.3+

## Usage Examples

### Example 1: Basic Evaluation

**Configuration**:
- Metrics: All 4 checked
- flag_low_scores: Unchecked
- score_threshold: 0.5

**Use case**: Evaluate all QA pairs and review scores manually

### Example 2: Quality Filtering

**Configuration**:
- Metrics: faithfulness, answer_relevancy
- flag_low_scores: Checked
- score_threshold: 0.7

**Use case**: Automatically flag low-quality pairs for regeneration

### Example 3: Context Quality Only

**Configuration**:
- Metrics: context_precision, context_recall
- flag_low_scores: Checked
- score_threshold: 0.8

**Use case**: Evaluate retrieval quality without checking answers

## Troubleshooting

### "unknown metric type: answer_relevancy"

**Cause**: No embeddings available for your provider

**Solution**:
- Use Gemini, OpenAI, or Ollama provider
- Or set OPENAI_API_KEY for Anthropic

### All scores are 0.0

**Cause**: Missing required fields in QA pairs

**Solution**: Check that your QA pairs include:
- question
- answer
- contexts (array)
- ground_truth

### "JSON parsing error"

**Cause**: LLM returning invalid JSON format

**Solution**: Already handled by CleanJSONLLM wrapper - restart backend if persists

### Slow evaluation

**Cause**: Processing many QA pairs with multiple metrics

**Solution**:
- Reduce number of metrics selected
- Use faster LLM provider (Gemini is fastest)
- Process smaller batches

## Best Practices

1. **Start with faithfulness**: Most important metric for factual accuracy
2. **Use all 4 metrics**: For comprehensive quality assessment
3. **Set appropriate thresholds**: Lower for development, higher for production
4. **Review flagged items**: Don't auto-delete, manually verify first
5. **Track metrics over time**: Monitor quality across pipeline runs
6. **Use faster models**: Gemini 2.0 Flash is recommended for speed/cost

## Integration with Pipeline

Typical pipeline flow:

1. **Markdown Chunker** - Split document into chunks
2. **Structured Generator** - Generate QA pairs from each chunk
3. **JSON Field Extractor** - Extract and structure QA pairs
4. **Ragas Batch Metrics** - Evaluate all QA pairs ← Add here
5. **Review** - Manual review of results

The evaluation scores are added to each QA pair without modifying the original data.
