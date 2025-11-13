---
title: Pipeline Templates
---

# Pipeline Templates

Templates provide pre-configured pipelines for common data generation tasks with simplified, content-based seeds.

## Seed Structure

Most templates use a simplified seed format with a `content` field:

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

**Note:** Templates using the Markdown Chunker (like Q&A Generation) use `file_content` instead of `content` to process markdown documents.

## Available Templates

### JSON Extraction

📘 **[Complete Guide](template_json_extraction)** | [View Template](../lib/templates/json_generation.yaml)

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

📘 **[Complete Guide](template_text_classification)** | [View Template](../lib/templates/text_classification.yaml)

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

📘 **[Complete Guide](template_qa_generation)** | [View Template](../lib/templates/qa_generation.yaml)

**Purpose:** Generate question-answer pairs from markdown documents. Automatically chunks long documents by structure and generates Q&A pairs for each section.

**Blocks:**
1. Markdown Chunker: Splits markdown by structure with size constraints (512 tokens, 50 overlap)
2. TextGenerator: Generates 3-5 questions per chunk
3. StructuredGenerator: Answers questions based on chunk content
4. JSONValidator: Validates Q&A structure

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
  "file_content": "# Photosynthesis\n\nPhotosynthesis is how plants convert sunlight into energy using chlorophyll.\n\n## The Process\n\nLight energy is absorbed by chlorophyll in the leaves. This triggers chemical reactions that produce glucose and oxygen."
}

// Generated output (per chunk)
{
  "qa_pairs": [
    {
      "question": "What is photosynthesis?",
      "answer": "Photosynthesis is how plants convert sunlight into energy using chlorophyll."
    },
    {
      "question": "What role does chlorophyll play?",
      "answer": "Chlorophyll absorbs light energy in the leaves to trigger chemical reactions."
    },
    {
      "question": "What does photosynthesis produce?",
      "answer": "Photosynthesis produces glucose and oxygen."
    }
  ]
}
```

**Use Cases:**
- Convert documentation into training datasets
- Generate educational Q&A from textbooks/tutorials
- Create comprehension tests from long markdown articles
- Process multi-section documents efficiently

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

## Template Guides

Detailed guides for each template:

- 📘 **[JSON Extraction Template](template_json_extraction)** - Complete guide with examples and customization
- 📘 **[Text Classification Template](template_text_classification)** - Full configuration reference and use cases
- 📘 **[Q&A Generation Template](template_qa_generation)** - Advanced usage with markdown file upload

## Related Documentation

- [How to Use](how_to_use) - Learn about running pipelines
- [Create Custom Blocks](how_to_create_blocks) - Build your own blocks
