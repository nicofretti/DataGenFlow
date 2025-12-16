<div align="center">
  <img src="images/logo/banner.png" alt="DataGenFlow Logo"/>
  <p>
    <a href="#quick-start">Quick Start</a> •
    <a href="#how-it-works">How It Works</a> •
    <a href="#documentation">Documentation</a>
  </p>

  [![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
  [![GitHub stars](https://img.shields.io/github/stars/nicofretti/DataGenFlow.svg?style=social&label=Star)](https://github.com/nicofretti/DataGenFlow)
</div>

<div align="center">

https://github.com/user-attachments/assets/7ca7a319-e2c1-4e24-a4c7-2b098d692aa1

**Define seeds → Build pipeline → Review results → Export data**

[Watch full demo](images/video/full_video.mp4)

</div>

## Why DataGenFlow 🌱

DataGenFlow is minimal tool to help you generate and validate data from seed/documents with full visibility.

### Key Benefits

- Easy to Extend: Add custom blocks in minutes with auto-discovery
- Faster Development: Visual pipeline builder eliminates boilerplate code
- Simple to Use: Intuitive drag-and-drop interface, no training required
- Full Transparency: Complete execution traces for debugging

## Quick Start

Get started in under 2 minutes:

```bash
# Install dependencies
make setup
make dev

# Launch application (backend + frontend), make sure to have .env configured
make run-dev

# Open http://localhost:8000
```

**That's it!** No complex configuration, no external services required beyond your LLM endpoint.

## How It Works

### TL;DR - Visual Overview

Example of JSON extraction pipeline from text:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. SEED DATA (JSON)                                                     │
│    { "repetitions": 2, "metadata": {"content": "Python is a..."} }      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. PIPELINE (Visual Drag & Drop)                                        │
│                                                                         │
│         ┌──────────────────┐           ┌──────────────────┐             │
│         │   Structured     │    ───►   │       JSON       │             │
│         │    Generator     │           │    Validator     │             │
│         └──────────────────┘           └──────────────────┘             │
│                                                                         │
│    Accumulated State Flow:                                              │
│    content  ─►  + generated (title, description)  ─►  + valid, parsed   │
│                                                                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. GENERATION & REVIEW                                                  │
│    + Execute pipeline for each seed × repetitions                       │
│    + Review results with keyboard shortcuts (A/R/E)                     │
│    + View full execution trace for debugging                            │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. EXPORT                                                               │
│    Download as JSONL ─► Ready for training/integration                  │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Concept:** Each block adds data to the **accumulated state**, so subsequent blocks automatically have access to all previous outputs-no manual wiring needed!

---

### 1. Define Your Seed Data

Start by creating a JSON seed file with the variables your pipeline will use. Seeds define what data you want to generate.

Single seed:
```json
{
  "repetitions": 2,
  "metadata": {
    "topic": "Python programming",
    "difficulty": "beginner"
  }
}
```

Multiple seeds (generate different variations):
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

Fields:
- `repetitions`: How many times to run the pipeline with this seed
- `metadata`: Variables accessible in your blocks via `{{ variable_name }}`

### 2. Build Your Pipeline Visually

Design your data generation workflow using drag-and-drop blocks. Each block processes data and passes it to the next one. Currenlty there are 3 types of blocks:
- Generators: Create new content
- Validators: Validate or parse existing content
- Metrics: Calculate quality metrics on content

Here are some example blocks available out of the box:
- [Generator] Text Generator: Generate text using LLM with configurable parameters
- [Generator] Structured Generator: Generate structured JSON with schema validation
- [Validators] Validator: Validate text (length, forbidden words, patterns)
- [Validators] JSON Validator: Parse and validate JSON structures
- [Metrics] Coherence Score: Calculate text coherence metrics
- [Metrics] Diversity Score: Measure lexical diversity
- [Metrics] Rouge Score: Calculate ROUGE similarity scores
- [Seeders] Markdown Chunker: Split markdown documents into chunks for processing
- ... other blocks will be added over time, you can contribute new ones too!

#### Extend with Custom Blocks

The real power of DataGenFlow is creating your own blocks. Add domain-specific logic in minutes with automatic discovery:

```python
from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext
from typing import Any

class SentimentAnalyzerBlock(BaseBlock):
    name = "Sentiment Analyzer"
    description = "Analyzes text sentiment"
    category = "validators"  # generators, validators, metrics, seeders, general
    inputs = ["text"]  # what this block needs from accumulated state
    outputs = ["sentiment", "confidence"]  # what it adds to accumulated state

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        text = context.get_state("text", "")  # access from accumulated state
        sentiment = analyze_sentiment(text)

        # return values are added to accumulated state automatically
        return {
            "sentiment": sentiment.label,
            "confidence": sentiment.score
        }
```

Drop your file in `user_blocks/` and it's automatically discovered on restart-no configuration needed.

Why this matters:
- Adapt to your specific domain or workflow instantly
- Integrate proprietary validation logic or data sources
- Build reusable components for your team
- Share blocks as Python files-simple as copy/paste

**Debugging Custom Blocks**

Need to debug your custom block? Use the included `debug_pipeline.py` script with VS Code debugger. See [Developer Documentation](DEVELOPERS#debugging-custom-blocks) for details.

📚 Complete guide: [Custom Block Development](docs/how_to_create_blocks.md)

#### Accumulated State

Data flows automatically through your pipeline. Each block adds its outputs to an accumulated state that every subsequent block can access-no manual wiring:

```
┌─────────────────────┐
│ Structured Generator│ → outputs: {"generated": {"title": "...", "description": "..."}}
└─────────────────────┘
    │
    ▼ (state: content, generated)
┌─────────────────────┐
│   JSON Validator    │ → outputs: {"valid": true, "parsed_json": {...}}
└─────────────────────┘
    │
    ▼ (state: content, generated, valid, parsed_json)
    All subsequent blocks can access all fields
```

This makes building complex pipelines incredibly simple-connect blocks and they automatically share data.

### 3. Review and Refine

Review your results with keyboard shortcuts (Accept: A, Reject: R, Edit: E) and full execution traces to see how each result was generated.

### 4. Export Your Data

Export your data in JSONL format, filtered by status (accepted, rejected, pending).

## Configuration

Create `.env` file (or copy from `.env.example`):

```bash
# LLM Configuration
LLM_ENDPOINT=http://localhost:11434/v1/chat/completions  # Ollama, OpenAI, etc.
LLM_API_KEY=                            # Optional for some endpoints
LLM_MODEL=llama3.2

# Database
DATABASE_PATH=data/qa_records.db

# Server
HOST=0.0.0.0
PORT=8000

# Debug mode (optional)
DEBUG=false  # set to true for detailed logging
```

## Documentation

📖 Comprehensive Guides
- [How to Use DataGenFlow](docs/how_to_use.md) - Complete user guide
- [Custom Block Development](docs/how_to_create_blocks.md) - Extend functionality
- [Developer Documentation](DEVELOPERS.md) - Technical reference for developers

## Contributing

Contributions are welcome and appreciated. Before submitting a contribution, please review the guidelines below.

Prerequisites:
- Read the [Contributing Guidelines](CONTRIBUTING.md) thoroughly
- Check existing issues and pull requests to avoid duplication
- Follow the project's commit conventions and code style standards

Areas for Contribution:
- New processing blocks and pipeline templates
- Documentation improvements and examples
- Bug fixes and performance optimizations
- Test coverage expansion
- Integration examples and use cases

For detailed technical requirements and development setup, refer to the [Developer Documentation](DEVELOPERS.md).

<div align="center">

[Get Started](#quick-start) • [View Documentation](#documentation)

Happy Data Generating! 🌱

</div>