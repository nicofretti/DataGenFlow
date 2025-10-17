# How to Use DataGenFlow

This guide walks you through using DataGenFlow to create datasets powered by LLMs.

## Overview

DataGenFlow uses a three-phase workflow:

1. **Build**: Create pipelines by connecting blocks
2. **Generate**: Run pipelines on seed data to produce records
3. **Review**: Validate, edit, and export results

## Prerequisites

- LLM endpoint configured (Ollama, OpenAI, etc.)
- Application running at http://localhost:8000
- Seed data file prepared (JSON format)

## Phase 1: Building Pipelines

### What is a Pipeline?

A pipeline is a sequence of blocks that process data. Each block:
- Takes inputs (text, data, etc.)
- Performs an operation (LLM generation, validation, formatting)
- Outputs results for the next block

### Creating Your First Pipeline

1. **Navigate to Builder tab**
   - Open http://localhost:8000
   - Click "Builder" in navigation

2. **Add blocks**
   - Click "Add Block" button
   - Select block type (e.g., "LLM")
   - Block appears in the canvas

3. **Configure blocks**
   - Click on a block to select it
   - Configuration panel appears on the right
   - Fill in required fields

4. **Connect blocks** (if using multiple blocks)
   - Blocks automatically chain outputs to inputs
   - Data flows top to bottom

5. **Save pipeline**
   - Click "Save Pipeline"
   - Give it a descriptive name
   - Pipeline is now ready to use

### Example: Simple Q&A Pipeline

**Goal**: Generate question-answer pairs using an LLM

**Blocks needed**:
1. **LLMBlock** - Generates the Q&A
2. **ValidatorBlock** - Ensures output meets quality standards
3. **OutputBlock** - Formats the final result

**Configuration**:

**Block 1: LLMBlock**
- Name: "Q&A Generator"
- System prompt: `You are a helpful assistant that generates high-quality question-answer pairs.`
- User prompt: `Generate a Q&A pair about {{ topic }}`

**Block 2: ValidatorBlock**
- Name: "Length Validator"
- Min length: 50
- Max length: 500
- Forbidden words: (empty)

**Block 3: OutputBlock**
- Name: "Final Output"
- Format template: `{{ assistant }}`

## Phase 2: Generating Records

### Preparing Seed Data

Seed files define the variables used in your pipeline templates.

**Format**:
```json
{
  "repetitions": 2,
  "metadata": {
    "topic": "Python programming",
    "difficulty": "beginner"
  }
}
```

Or multiple seeds:
```json
[
  {
    "repetitions": 1,
    "metadata": {
      "topic": "Python lists",
      "difficulty": "beginner"
    }
  },
  {
    "repetitions": 1,
    "metadata": {
      "topic": "Python dictionaries",
      "difficulty": "intermediate"
    }
  }
]
```

**Fields**:
- `repetitions`: How many times to run the pipeline with this seed
- `metadata`: Variables accessible in block templates via `{{ variable_name }}`

### Running Generation

1. **Navigate to Generator tab**
2. **Upload seed file**
   - Click "Choose File"
   - Select your JSON seed file
3. **Select pipeline**
   - Choose from saved pipelines
4. **Click "Generate"**
   - Progress indicator shows status
   - Errors are displayed if validation fails
5. **Wait for completion**
   - Records are saved automatically
   - Navigate to Review tab when done

## Phase 3: Reviewing Results

### Review Interface

The Review tab shows all generated records with:
- **Output**: The final pipeline result
- **Metadata**: Input variables used
- **Trace**: Execution history (click "View Trace")
- **Actions**: Accept, Reject, Edit

### Reviewing Records

1. **Navigate to Review tab**
2. **Filter by status** (optional)
   - Pending: Not yet reviewed
   - Accepted: Approved records
   - Rejected: Discarded records
   - Edited: Modified records

3. **Review each record**:
   - Read the output
   - Check if it meets your quality standards

4. **Take action**:
   - **Accept**: Mark as approved (click ✅)
   - **Reject**: Mark as discarded (click ❌)
   - **Edit**: Modify the output
     - Click "Edit" button
     - Modify text in editor
     - Click "Save"

### Using Execution Traces

Traces help debug issues by showing:
- Which blocks executed
- How long each took
- What data passed between blocks
- Any errors that occurred

**To view trace**:
1. Click "View Trace" on a record
2. Expand to see block-by-block execution
3. Check `accumulated_state` to see data flow

### Exporting Results

1. **Filter to Accepted records** (optional)
2. **Click "Export" button**
3. **Choose format**:
   - JSONL (recommended for ML training)
   - JSON
4. **Download file**

**Export format**:
```jsonl
{"id": 1, "output": "...", "metadata": {...}, "status": "accepted"}
{"id": 2, "output": "...", "metadata": {...}, "status": "accepted"}
```

## Tips and Best Practices

### Pipeline Design
- **Start simple**: Begin with one LLM block, add validation later
- **Use templates**: Load from templates as starting points
- **Test with small batches**: Use `repetitions: 1` while developing

### Seed Data
- **Use descriptive variable names**: `{{ topic }}` not `{{ t }}`
- **Include variety**: Different seeds produce diverse outputs
- **Validate JSON**: Use a JSON validator before uploading

### Quality Control
- **Check traces for failures**: View trace if output looks wrong
- **Edit instead of reject**: Save good records that need minor fixes
- **Use validation blocks**: Catch issues early in the pipeline

### Debugging
- **Enable debug mode**: Set `DEBUG=true` in `.env`
- **Check backend logs**: Look for trace IDs and timing info
- **Review block configurations**: Ensure templates render correctly

## Common Issues

### "Invalid JSON format" error
- **Cause**: Seed file is not valid JSON
- **Fix**: Use https://jsonlint.com to validate your file

### Generation hangs or times out
- **Cause**: LLM endpoint is slow or unreachable
- **Fix**: Check LLM_ENDPOINT in `.env`, test endpoint separately

### Empty outputs
- **Cause**: OutputBlock template doesn't match available variables
- **Fix**: Check trace to see what variables are available, update template

### Validation always fails
- **Cause**: Validator rules too strict
- **Fix**: Check ValidatorBlock config, adjust min/max length

## Next Steps

- Learn to create custom blocks: [how_to_create_blocks.md](how_to_create_blocks.md)
- Explore API endpoints: [README.md](../README.md#advanced-usage)
- Check architecture: [architecture.md](architecture.md)
