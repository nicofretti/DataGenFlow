# How to Use DataGenFlow

This guide walks you through using DataGenFlow to create datasets powered by LLMs.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Phase 1: Building Pipelines](#phase-1-building-pipelines)
  - [What is a Pipeline?](#what-is-a-pipeline)
  - [Creating Your First Pipeline](#creating-your-first-pipeline)
  - [Example: Simple Q&A Pipeline](#example-simple-qa-pipeline)
- [Phase 2: Generating Records](#phase-2-generating-records)
  - [Preparing Seed Data](#preparing-seed-data)
  - [Running Generation](#running-generation)
- [Phase 3: Reviewing Results](#phase-3-reviewing-results)
  - [Review Interface](#review-interface)
  - [Reviewing Records](#reviewing-records)
  - [Using Execution Traces](#using-execution-traces)
  - [Exporting Results](#exporting-results)
- [Tips and Best Practices](#tips-and-best-practices)
- [Common Issues](#common-issues)
- [Next Steps](#next-steps)

## Overview

DataGenFlow uses a three-phase workflow:

1. **Build**: Create pipelines by connecting blocks
2. **Generate**: Run pipelines on seed data to produce records
3. **Review**: Validate, edit, and export results

## Quick Start with Templates

DataGenFlow includes pre-configured templates for common tasks. See [Pipeline Templates](templates.md) for:
- **JSON Extraction** - Extract structured information from text
- **Text Classification** - Classify text into categories with confidence scores
- **Q&A Generation** - Generate question-answer pairs from content

Templates use simplified seeds with just a `content` field in metadata.

## Prerequisites

- LLM endpoint configured (Ollama, OpenAI, etc.)
- Application running at http://localhost:8000
- Seed data file prepared (JSON format)

## Phase 1: Building Pipelines

### What is a Pipeline?

A pipeline is a sequence of blocks that process data. Each block:
- Takes inputs from accumulated state (previous blocks' outputs + seed data)
- Performs an operation (LLM generation, validation, formatting)
- Outputs results that get added to accumulated state for next blocks

**Key concept**: All block outputs accumulate, so later blocks can access any data from earlier blocks.

### Creating Your First Pipeline

**Step 1**: Navigate to Pipelines page
   - Open http://localhost:8000
   - Click "Pipelines" in navigation

**Step 2**: Choose creation method
   - From template: Click a template card to create pre-configured pipeline
   - From scratch: Click "+ New Pipeline" to use visual editor

**Step 3**: Visual Pipeline Editor (if creating from scratch)
   - Start/End blocks: Automatically added (circular nodes, cannot be deleted)
   - Add blocks: Drag blocks from left palette onto canvas
   - Connect blocks: Drag from output handle to input handle
   - Configure blocks: Click gear icon on block to open config panel
   - See accumulated state: Each block shows available fields at that point

**Step 4**: Configure blocks
- Click gear icon (⚙️) on any block
- Configuration panel opens on right
- Fill in required parameters
- Red "Not Configured" badge shows missing fields
- Yellow "Not Connected" badge shows disconnected blocks

**Step 5**: Save pipeline
- Enter pipeline name at top
- Click "Save Pipeline" button
- Pipeline validation runs (checks all blocks configured and connected)
- Pipeline appears in list

### Example: JSON Generation Pipeline

This example comes from the built-in "JSON Generation with Validation" template.

**Goal**: Generate structured JSON objects about topics with automatic validation

**Pipeline Blocks**:
1. **LLMBlock** - Generates JSON from topic
2. **JSONValidatorBlock** - Validates and parses JSON structure
3. **OutputBlock** - Formats validated output

**Block Configurations**:

**Block 1**: LLMBlock
- Temperature: `0.7`
- Max tokens: `2048`
- System prompt: Uses `{{ system }}` from seed (defines JSON structure and examples)
- User prompt: Uses `{{ user }}` from seed (the topic)

**Block 2**: JSONValidatorBlock
- Field name: `assistant` (validates LLM output)
- Required fields: `[]` (accepts any valid JSON)
- Strict mode: `false` (allows flexible structure)

**Block 3**: OutputBlock
- Format template:
  ```jinja2
  {% if valid %}{{ parsed_json | tojson }}
  {% else %}Raw output: {{ assistant }}{% endif %}
  ```

**Example Seed Data**:
```json
{
  "repetitions": 3,
  "metadata": {
    "system": "Generate a JSON object with the fields: title and description about the given user topic.\nExamples:\nuser: AI\noutput: { \"title\": \"Introduction to AI\", \"description\": \"A comprehensive overview...\" }\n\nDo not include any other text, just return a json object with title and description.",
    "user": "Cleaning Your Laptop Screen"
  }
}
```

**What Happens**:
1. LLM receives system prompt (JSON structure) and user topic
2. LLM generates: `{ "title": "...", "description": "..." }`
3. JSONValidatorBlock parses and validates the JSON
4. OutputBlock returns formatted JSON if valid, or raw output if invalid
5. Result is saved for review with full execution trace

## Phase 2: Generating Records

### Preparing Seed Data

Seed files define the variables used in your pipeline templates.

**Simple content-based format (for templates)**:
```json
[
  {
    "repetitions": 3,
    "metadata": {
      "content": "Electric cars reduce emissions but require charging infrastructure."
    }
  },
  {
    "repetitions": 2,
    "metadata": {
      "content": "Machine learning helps doctors diagnose diseases more accurately."
    }
  }
]
```

**Custom variables format (for custom pipelines)**:
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
- For templates, use `content` field; for custom pipelines, use any variable names

### Running Generation

1. **Navigate to Generator page**
2. **Upload seed file**
   - Click "Choose File"
   - Select your JSON seed file
3. **Select pipeline**
   - Choose from saved pipelines in dropdown
4. **Click "Generate"**
   - Job starts in background
   - Can only run one job at a time
5. **Monitor progress**:
   - **Global indicator**: Top-right corner shows active job
   - **Detailed progress**: Generator page shows:
     - Progress bar with percentage
     - Current step (e.g., "Processing seed 5/10")
     - Current block being executed
     - Success/failure counts
     - Elapsed time
   - Progress updates every 2 seconds
6. **Cancel job** (optional):
   - Click "Cancel Job" to stop generation
7. **Wait for completion**:
   - Records saved automatically as generated
   - Navigate to Review page when done
   - Job appears in job selector

## Phase 3: Reviewing Results

### Review Interface

The Review page shows generated records with a clean card-based layout:
- **Job selector**: Filter records by generation job (required)
- **Status filter**: View Pending, Accepted, or Rejected records
- **Record cards**: Each shows output, metadata, and actions
- **Trace viewer**: Collapsible execution history with timing

### Reviewing Records

**Step 1**: Navigate to Review page

**Step 2**: Select a job (required)
   - Choose from dropdown of recent jobs
   - Only shows jobs that generated records
   - Stats update when switching jobs

**Step 3**: Filter by status
   - **Pending**: Not yet reviewed (default view)
   - **Accepted**: Approved records
   - **Rejected**: Discarded records

**Step 4**: Review each record*
   - Read the output in card format
   - Click "View Trace" to see execution details
   - Check metadata (seed variables used)

**Step 5**: Take action
   - **Accept** (A key): Mark as approved
   - **Reject** (R key): Mark as discarded
   - **Edit** (E key): Modify the output
     - Opens edit modal
     - Make changes to output text
     - Click "Save" to update record

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

Export is scoped to the currently selected job:

1. **Select job** from dropdown
2. **Filter by status** (optional - export all or just accepted/rejected)
3. **Click "Export JSONL" button**
4. **File downloads** automatically with job-scoped records

**Export format**:
```jsonl
{"id": 1, "output": "...", "metadata": {...}, "status": "accepted", "trace": [...]}
{"id": 2, "output": "...", "metadata": {...}, "status": "accepted", "trace": [...]}
```

**Deleting Records**:
- "Delete All" button removes all records for selected job
- Also deletes the job itself
- Job disappears from selector after deletion

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

- **Create custom blocks**: Extend DataGenFlow with your own logic - [Custom Blocks Guide](how_to_create_blocks)
- **Developer guide**: Deep dive into architecture and API - [DEVELOPERS.md](DEVELOPERS)
- **Contribute**: Share improvements and ideas - [CONTRIBUTING.md](CONTRIBUTING)
