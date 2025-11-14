---
title: JSON Extraction Template
description: Extract structured information from unstructured text
---

# JSON Extraction Template

## Table of Contents
- [Overview](#overview)
- [Pipeline Architecture](#pipeline-architecture)
- [Seed Format](#seed-format)
- [Output Format](#output-format)
- [Use Cases](#use-cases)
- [Customization](#customization)
- [Related Documentation](#related-documentation)

## Overview

**Complexity:** Simple (2 blocks)
**Use Case:** Extract structured information from unstructured text as JSON

This template converts free-form text into structured JSON with title and description fields. Perfect for creating structured datasets from raw text content.

## Pipeline Architecture

```
┌──────────────────┐     ┌──────────────────┐
│   Structured     │ ──► │       JSON       │
│    Generator     │     │    Validator     │
└──────────────────┘     └──────────────────┘

Input: content
  ↓
+ generated (title, description)
  ↓
+ valid, parsed_json
```

**Blocks:**
1. **StructuredGenerator** - Extracts key information as structured JSON
2. **JSONValidatorBlock** - Validates the JSON structure and required fields

## Seed Format

Use the simplified `content` field in metadata:

```json
{
  "repetitions": 3,
  "metadata": {
    "content": "Python is a high-level programming language known for readability and versatility. It's widely used in web development, data science, and automation."
  }
}
```

**Multiple seeds example:**
```json
[
  {
    "repetitions": 2,
    "metadata": {
      "content": "Electric cars reduce emissions but require charging infrastructure."
    }
  },
  {
    "repetitions": 1,
    "metadata": {
      "content": "Machine learning algorithms learn patterns from data without explicit programming."
    }
  }
]
```

## Output Format

**Schema:**
```json
{
  "title": "string - concise title summarizing the content",
  "description": "string - detailed description of the content"
}
```

**Example output:**
```json
{
  "title": "Introduction to Python",
  "description": "Python is a high-level programming language known for its readability and versatility, widely used in web development, data science, and automation."
}
```

## Use Cases

**Perfect for:**
- Creating structured datasets from raw text
- Converting blog posts/articles to metadata
- Extracting key information from descriptions
- Building content catalogs with titles and summaries

**Not ideal for:**
- Complex multi-field extraction (use custom blocks)
- Binary classification tasks (use Text Classification template)
- Question-answer pairs (use Q&A Generation template)

## Customization

You can modify the template in `lib/templates/json_generation.yaml`:

**Change output fields:**
```yaml
json_schema:
  type: object
  properties:
    headline: {type: string}
    summary: {type: string}
    category: {type: string}
  required: ["headline", "summary"]
```

**Adjust LLM parameters:**
```yaml
config:
  temperature: 0.5  # Lower = more deterministic
  max_tokens: 512   # Limit response length
```

**Customize the prompt:**
```yaml
user_prompt: "Extract the main topic and a brief summary from: {{ content }}"
```

## Related Documentation

- [Templates Overview](templates) - All available templates
- [How to Use](how_to_use) - Running pipelines with templates
- [Custom Blocks](how_to_create_blocks) - Creating your own blocks
