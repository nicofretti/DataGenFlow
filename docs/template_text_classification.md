---
title: Text Classification Template
description: Classify text into predefined categories with confidence scores
---

# Text Classification Template

## Table of Contents
- [Overview](#overview)
- [Pipeline Architecture](#pipeline-architecture)
- [Seed Format](#seed-format)
- [Output Format](#output-format)
- [Default Categories](#default-categories)
- [Use Cases](#use-cases)
- [Customization](#customization)
- [Common Use Case Examples](#common-use-case-examples)
- [Related Documentation](#related-documentation)

## Overview

**Complexity:** Simple (2 blocks)
**Use Case:** Classify text into predefined categories with confidence scores

This template automatically categorizes text content into one of five predefined categories: environment, technology, health, finance, or sports. Each classification includes a confidence score.

## Pipeline Architecture

```
┌──────────────────┐     ┌──────────────────┐
│   Structured     │ ──► │       JSON       │
│    Generator     │     │    Validator     │
└──────────────────┘     └──────────────────┘

Input: content
  ↓
+ generated (category, confidence)
  ↓
+ valid, parsed_json
```

**Blocks:**
1. **StructuredGenerator** - Classifies text with schema enforcement
2. **JSONValidatorBlock** - Validates category enum and confidence range

## Seed Format

Use the simplified `content` field in metadata:

```json
{
  "repetitions": 2,
  "metadata": {
    "content": "Solar panels convert sunlight into electricity for homes and businesses."
  }
}
```

**Multiple seeds example:**
```json
[
  {
    "repetitions": 1,
    "metadata": {
      "content": "The stock market reached record highs today as investors responded positively."
    }
  },
  {
    "repetitions": 1,
    "metadata": {
      "content": "New breakthrough in cancer treatment shows promising results in clinical trials."
    }
  }
]
```

## Output Format

**Schema:**
```json
{
  "category": "enum [environment, technology, health, finance, sports]",
  "confidence": "number (0-1)"
}
```

**Example outputs:**
```json
{
  "category": "environment",
  "confidence": 0.95
}
```

```json
{
  "category": "health",
  "confidence": 0.88
}
```

## Default Categories

The template includes 5 predefined categories:

1. **environment** - Climate, sustainability, nature, energy
2. **technology** - Software, hardware, AI, innovation
3. **health** - Medicine, fitness, wellness, treatment
4. **finance** - Markets, economy, banking, investment
5. **sports** - Athletics, competitions, teams, games

## Use Cases

**Perfect for:**
- Content categorization for blogs or news sites
- Automated tagging systems
- Dataset labeling for training models
- Organizing unstructured text collections

**Not ideal for:**
- Binary yes/no classification (customize categories)
- Sentiment analysis (customize to positive/negative/neutral)
- Multi-label classification (requires custom block)

## Customization

Modify the template in `lib/templates/text_classification.yaml`:

**Change categories (e.g., for sentiment analysis):**
```yaml
json_schema:
  properties:
    category:
      type: string
      enum: ["positive", "negative", "neutral"]
    confidence:
      type: number
      minimum: 0
      maximum: 1
```

**Add more categories:**
```yaml
enum: ["environment", "technology", "health", "finance", "sports", "education", "entertainment"]
```

**Adjust temperature for more/less deterministic results:**
```yaml
temperature: 0.1  # Very deterministic
temperature: 0.7  # More creative/varied
```

**Customize the prompt:**
```yaml
user_prompt: "Classify the sentiment of this customer review as positive, negative, or neutral. Review: {{ content }}"
```

## Common Use Case Examples

**Sentiment Analysis:**
```yaml
# Categories: positive, negative, neutral
# Use for: Customer reviews, feedback, social media
```

**Support Ticket Routing:**
```yaml
# Categories: billing, technical, account, general
# Use for: Automated ticket classification
```

**Content Moderation:**
```yaml
# Categories: safe, questionable, inappropriate
# Use for: User-generated content filtering
```

## Related Documentation

- [Templates Overview](templates) - All available templates
- [How to Use](how_to_use) - Running pipelines with templates
- [Custom Blocks](how_to_create_blocks) - Creating your own blocks
