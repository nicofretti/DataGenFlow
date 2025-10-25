---
title: Pipeline Templates
---

# Pipeline Templates

Templates provide pre-configured pipelines for common data generation tasks with simplified, content-based seeds.

## Seed Structure

All templates use a simplified seed format with only a `content` field:

```json
[
  {
    "repetitions": 3,
    "metadata": {
      "content": "Your text content here..."
    }
  }
]
```

## Available Templates

### JSON Extraction

**Purpose:** Extract structured information from text content as JSON.

**Blocks:**
- StructuredGenerator: Extracts title and description
- JSONValidator: Validates output structure

**Output Schema:**
```json
{
  "title": "string - concise title",
  "description": "string - detailed description"
}
```

**Example:**
```json
// Input seed
{
  "content": "Electric cars reduce emissions but require charging infrastructure."
}

// Generated output
{
  "title": "Electric Vehicle Basics",
  "description": "Electric cars provide environmental benefits through reduced emissions, though they face infrastructure challenges."
}
```

### Text Classification

**Purpose:** Classify text into predefined categories with confidence scores.

**Blocks:**
- StructuredGenerator: Classifies with schema enforcement
- JSONValidator: Validates category and confidence

**Output Schema:**
```json
{
  "category": "enum - one of [environment, technology, health, finance, sports]",
  "confidence": "number - range [0-1]"
}
```

**Example:**
```json
// Input seed
{
  "content": "Solar panels convert sunlight into electricity for homes."
}

// Generated output
{
  "category": "environment",
  "confidence": 0.92
}
```

**Use Cases:**
- Sentiment analysis
- Topic categorization
- Content tagging

### Q&A Generation

**Purpose:** Generate question-answer pairs from source content using a two-step pipeline.

**Blocks:**
1. TextGenerator: Generates 3-5 questions (unstructured text)
2. StructuredGenerator: Answers questions based on original content
3. JSONValidator: Validates Q&A structure

**Output Schema:**
```json
{
  "qa_pairs": [
    {
      "question": "string - comprehension question",
      "answer": "string - answer from content"
    }
  ]
}
```

**Example:**
```json
// Input seed
{
  "content": "Photosynthesis is how plants convert sunlight into energy using chlorophyll."
}

// Generated output
{
  "qa_pairs": [
    {
      "question": "What is photosynthesis?",
      "answer": "Photosynthesis is how plants convert sunlight into energy."
    },
    {
      "question": "What substance do plants use for photosynthesis?",
      "answer": "Plants use chlorophyll for photosynthesis."
    }
  ]
}
```

**Use Cases:**
- Training dataset generation
- Educational content creation
- Comprehension test generation

## Customizing Templates

Templates are YAML files in `lib/templates/`. You can customize:

1. **Prompts:** Modify instructions and few-shot examples
2. **JSON Schema:** Change output structure and fields
3. **Categories:** Edit classification categories
4. **Block Parameters:** Adjust temperature, max_tokens, etc.

**Example customization:**

```yaml
blocks:
  - type: StructuredGenerator
    config:
      prompt: "Classify sentiment: {{ content }}"
      json_schema:
        properties:
          sentiment: {type: string, enum: ["positive", "negative", "neutral"]}
```

## Related Documentation

- [How to Use](how_to_use) - Learn about running pipelines
- [Create Custom Blocks](how_to_create_blocks) - Build your own blocks
