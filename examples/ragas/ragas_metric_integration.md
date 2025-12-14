# Example Pipelines

This directory contains sample pipeline configurations demonstrating common workflows.

## QA Generation with RAGAS Evaluation

**File**: `ragas-qa-evaluation-pipeline.json`

**Description**: Complete pipeline for generating high-quality QA pairs from documents with automatic quality evaluation.

**What it does**:
1. Splits documents into chunks
2. Generates QA pairs for each chunk
3. Extracts and structures the QA data
4. Evaluates quality using RAGAS metrics
5. Flags low-quality pairs below threshold

**Use case**: Creating production-ready QA datasets for:
- RAG system evaluation
- LLM fine-tuning
- Chatbot training
- Knowledge base testing

**Expected input**:
```json
{
  "text": "Your document text here..."
}
```

**Output format**:
```json
{
  "qa_pairs_with_scores": [
    {
      "question": "...",
      "answer": "...",
      "ground_truth": "...",
      "contexts": [...],
      "scores": {
        "answer_relevancy_score": 0.92,
        "faithfulness_score": 0.88,
        "context_precision_score": 0.95,
        "context_recall_score": 0.85
      },
      "low_quality": false,
      "below_threshold": {...}
    }
  ]
}
```

**Configuration tips**:
- Adjust `chunk_size` (500) based on document structure
- Increase `max_tokens` (8192) if generating more QA pairs
- Set `score_threshold` (0.7) based on quality requirements
- Disable specific metrics if not needed

**LLM requirements**:
- Provider: Gemini, OpenAI, or Ollama (for embeddings)
- Recommended: Gemini 2.0 Flash (fast + cheap)
- Alternative: GPT-4 Turbo (higher quality)

## Importing Sample Pipelines

### Option 1: Via UI
1. Copy the JSON content
2. Go to Pipelines page
3. Click "Import Pipeline"
4. Paste the JSON
5. Save and configure

### Option 2: Via API
```bash
curl -X POST http://localhost:8000/api/pipelines \
  -H "Content-Type: application/json" \
  -d @examples/ragas-qa-evaluation-pipeline.json
```

### Option 3: Direct File Copy
```bash
# Copy to your pipelines directory
cp examples/ragas-qa-evaluation-pipeline.json ~/.datagenflow/pipelines/
```

## Running the Sample Pipeline

1. **Import the pipeline** (see above)
2. **Configure LLM model** in Settings (Gemini recommended)
3. **Configure embedding model** in Settings (if using answer_relevancy)
4. **Create a seed** with your input text
5. **Run the pipeline**
6. **Review results** with quality scores

## Customization Ideas

### High-Volume Processing
- Remove answer_relevancy metric (no embeddings needed)
- Use Gemini 2.0 Flash for speed
- Increase chunk_size to reduce chunks

### Maximum Quality
- Use all 4 metrics
- Set score_threshold to 0.8+
- Use GPT-4 or Claude Sonnet
- Lower chunk_size for focused context

### Cost Optimization
- Use Ollama (free, local)
- Reduce metrics to faithfulness only
- Increase chunk_size
- Lower max_tokens

## Next Steps

After running the sample pipeline:
1. Review the quality scores
2. Adjust threshold based on results
3. Regenerate flagged low-quality pairs
4. Export high-quality pairs for production use
5. Track metrics across multiple runs

For more information, see the [RAGAS Evaluation Guide](../docs/ragas-evaluation.md).
