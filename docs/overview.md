---
title: Overview
description: Transform complex data generation workflows into intuitive visual pipelines
---

# Overview

DataGenFlow transforms complex data generation workflows into intuitive visual pipelines. A minimal tool designed to help you generate, validate, and export quality data with full transparency.

## Table of Contents
- [Why DataGenFlow](#why-datagenflow)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Key Features](#key-features)
- [Next Steps](#next-steps)

## Why DataGenFlow

### The Problem

Creating quality datasets for LLM training, testing, or validation often involves:
- Writing repetitive boilerplate code
- Managing complex orchestration logic
- Debugging opaque generation failures
- Manual review of thousands of records
- Difficulty extending or customizing workflows

### The Solution

DataGenFlow provides:
- **Visual Pipeline Builder**: Drag-and-drop blocks instead of writing orchestration code
- **Auto-Discovery**: Custom blocks appear automatically - no configuration needed
- **Full Transparency**: Complete execution traces show exactly how each result was generated
- **Accumulated State**: Data flows automatically between blocks - no manual wiring
- **Easy Extension**: Add domain-specific logic in minutes with simple Python classes

## Quick Start

Get DataGenFlow running in under 2 minutes:

```bash
# Install dependencies
make setup
make dev

# Launch application
make run-dev

# Open http://localhost:8000
```

That's it! No complex configuration or external services required beyond your LLM endpoint.

> **Note:** DataGenFlow works with any OpenAI-compatible LLM endpoint (Ollama, OpenAI, etc.). Configure your endpoint in `.env` file.

## Core Concepts

### Pipelines

A **pipeline** is a sequence of blocks that process data. Think of it as a visual workflow where:
- Data enters from seed files (JSON)
- Each block transforms or validates the data
- Results accumulate and flow to the next block
- Final output is ready for review and export

### Blocks

**Blocks** are reusable processing units. Each block:
- Declares what inputs it needs
- Declares what outputs it produces
- Executes asynchronously
- Adds its outputs to accumulated state

**Built-in blocks:**
- **TextGenerator**: Generate text using LLM with Jinja2 templates
- **StructuredGenerator**: Generate structured JSON with schema validation
- **ValidatorBlock**: Check text quality (length, patterns, forbidden words)
- **JSONValidatorBlock**: Parse and validate JSON structures
- **RougeScore**: Calculate ROUGE similarity between texts
- **DiversityScore**: Measure lexical diversity
- **CoherenceScore**: Calculate coherence metrics
- **Markdown Chunker**: Split markdown into processable chunks

**Custom blocks:** Create your own in minutes - just inherit from `BaseBlock` and implement `execute()`.

### Accumulated State

One of DataGenFlow's most powerful features: **data automatically flows between blocks**.

```text
Seed Data: {"content": "Python programming language"}
    ↓
StructuredGenerator outputs: {"generated": {"title": "...", "description": "..."}}
    ↓ (state: content, generated)
JSONValidatorBlock outputs: {"valid": true, "parsed_json": {...}}
    ↓ (state: content, generated, valid, parsed_json)
Any subsequent block can access: ALL accumulated data
```

No manual wiring needed - every block sees all previous outputs plus the original seed data.

### Jobs & Review

**Jobs** track batch generation:
- Run pipelines on multiple seeds
- Monitor progress in real-time
- Track success/failure counts
- Review results by job

**Review workflow:**
- Filter records by job
- Accept (A), Reject (R), or Edit (E) records
- View execution traces for debugging
- Export approved records as JSONL

## Key Features

### Visual Pipeline Builder

- **ReactFlow-based editor** with drag-and-drop blocks
- **Accumulated state visualization** shows available data at each step
- **Block status indicators** (Not Configured, Not Connected)
- **Template pipelines** for quick start
- **Pipeline validation** before save

### Real-Time Progress Tracking

- **Global indicator** in header shows active jobs
- **Detailed progress view** with:
  - Progress bar and percentage
  - Current block being executed
  - Success/failure counts
  - Elapsed time
- **Immediate job cancellation** - stops at next checkpoint (before next block or seed)

### Complete Execution Traces

Every record includes full trace:
- Block-by-block execution history
- Input/output for each block
- Accumulated state at each step
- Execution timing per block
- Error context if failures occur

### Job-Scoped Operations

- **Filter by job** to review specific generation runs
- **Export by job** for organized datasets
- **Delete by job** to clean up experiments
- Only 1 concurrent job allowed (prevents resource conflicts)

### Jinja2 Template Support

Use powerful template syntax in generator blocks:

```jinja2
System: You are a {{ role }} expert in {{ domain }}.
User: Explain {{ topic }} at {{ level }} level.

{% if include_examples %}
Include practical examples.
{% endif %}

Output: {{ assistant | truncate(500) }}
```

Variables come from:
- Seed data metadata
- Previous block outputs
- Accumulated state

## Next Steps

Ready to dive deeper?

- **[How to Use](how_to_use)**: Complete walkthrough of building pipelines, generating data, and reviewing results
- **[Create Custom Blocks](how_to_create_blocks)**: Extend DataGenFlow with your own processing logic
- **[Developer Guide](DEVELOPERS)**: Technical architecture, API reference, and debugging tools
- **[Contributing](CONTRIBUTING)**: Share improvements and join the community

---

**Happy data generating!** 🌱
