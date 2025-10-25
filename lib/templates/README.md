# Pipeline Templates

Pre-configured pipeline templates for common use cases.

## Available Templates

### qa_generation.yaml
Generate question-answer pairs from source text content.
- **Blocks:** TextGenerator → StructuredGenerator → JSONValidatorBlock
- **Use case:** Create comprehension questions and answers from text
- **Input:** content variable with source text
- **Output:** JSON with qa_pairs array

### json_generation.yaml
Extract structured information from text as JSON.
- **Blocks:** StructuredGenerator → JSONValidatorBlock
- **Use case:** Structure unstructured text into JSON format
- **Input:** content variable
- **Output:** Validated JSON with title and description

### text_classification.yaml
Classify text into predefined categories with confidence scores.
- **Blocks:** StructuredGenerator → JSONValidatorBlock
- **Use case:** Categorize text into environment, technology, health, finance, or sports
- **Input:** content variable
- **Output:** JSON with category and confidence score

## Using Templates

### From UI
1. Go to Pipelines page
2. Click on a template card
3. Pipeline is created automatically

### From API
```bash
curl -X POST http://localhost:8000/api/pipelines/from_template/json_generation
```

### With Seed Files

Example seed file for JSON generation (`example_json_seed.json`):
```json
[
  {
    "repetitions": 1,
    "metadata": {
      "system": "You are a JSON generator. Generate valid JSON with structure: {\"title\": \"...\", \"description\": \"...\", \"key_points\": [...], \"category\": \"...\"}",
      "user": "Generate JSON about: {{ topic }}",
      "topic": "machine learning"
    }
  }
]
```

## Template Format

Templates use YAML format:

```yaml
name: Template Name
description: What this template does
blocks:
  - type: BlockType
    config:
      param1: value1
      param2: value2

  - type: JSONValidatorBlock
    config:
      field_name: "generated"  # or any field from accumulated state
      required_fields: ["title", "description"]
      strict: false
```

## Creating Custom Templates

1. Create a new `.yaml` file in this directory
2. Define name, description, and blocks
3. Template will be auto-discovered on server restart

## Pipeline Output

The `pipeline_output` field is automatically set by the workflow:
- If the last block outputs `assistant`, `pipeline_output` defaults to `assistant`
- Otherwise, it defaults to the first output field of the last block
- This is what gets displayed in the review system

## JSONValidatorBlock Usage

The JSONValidatorBlock can validate JSON from any field in the accumulated state:

```yaml
# Validate LLM output
- type: JSONValidatorBlock
  config:
    field_name: "assistant"
    required_fields: ["title", "description"]

# Validate transformed text
- type: JSONValidatorBlock
  config:
    field_name: "transformed_text"
    required_fields: ["data"]

# Validate any custom field
- type: JSONValidatorBlock
  config:
    field_name: "my_custom_output"
    required_fields: []
    strict: true  # fail pipeline on invalid JSON
```

## Jinja2 Features in Block Prompts

TextGenerator and StructuredGenerator blocks support Jinja2 templates in their prompts:

- **Variables:** `{{ variable }}`
- **Conditionals:** `{% if valid %}...{% else %}...{% endif %}`
- **Loops:** `{% for item in list %}{{ item }}{% endfor %}`
- **Nested access:** `{{ metadata.field }}`

Example:
```yaml
- type: TextGenerator
  config:
    user_prompt: "Generate text about {{ topic }}"
```
