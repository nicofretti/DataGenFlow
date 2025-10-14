# Pipeline Templates

Pre-configured pipeline templates for common use cases.

## Available Templates

### complete_qa_generation.yaml
Full QA generation pipeline with LLM, validation, and conditional formatting.
- **Blocks:** LLMBlock → ValidatorBlock → OutputBlock
- **Use case:** General Q&A generation with text validation
- **Input:** system, user prompts with variables

### json_generation.yaml
Generate structured JSON from a topic with validation.
- **Blocks:** LLMBlock → JSONValidatorBlock → OutputBlock
- **Use case:** Structured data generation from topics
- **Input:** topic variable, system prompt instructs JSON format
- **Output:** Validated JSON or error message
- **JSONValidator config:** `field_name: "assistant"` - validates the LLM output

### structured_data_generation.yaml
Advanced JSON generation with required field validation and formatted output.
- **Blocks:** LLMBlock → JSONValidatorBlock → OutputBlock
- **Use case:** Complex structured data with field requirements
- **Required fields:** title, description, key_points, category
- **JSONValidator config:** `field_name: "assistant"`, `required_fields: [...]`
- **Output:** Formatted markdown with parsed fields or validation error

### text_generation.yaml
Simple text generation using LLM.
- **Blocks:** LLMBlock
- **Use case:** Basic text generation without validation

### validated_generation.yaml
Text generation with content validation.
- **Blocks:** LLMBlock → ValidatorBlock
- **Use case:** Text generation with length constraints

### text_transformation.yaml
Text transformation pipeline for cleaning and formatting.
- **Blocks:** TransformerBlock (strip → lowercase → trim)
- **Use case:** Text preprocessing and normalization

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
      field_name: "assistant"  # or any field from accumulated state
      required_fields: ["title", "description"]
      strict: false

  - type: OutputBlock
    config:
      format_template: |
        Jinja2 template with {{ variables }}
        {% if condition %}...{% endif %}
```

## Creating Custom Templates

1. Create a new `.yaml` file in this directory
2. Define name, description, and blocks
3. Use Jinja2 syntax in format_template for dynamic output
4. Template will be auto-discovered on server restart

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

## Jinja2 Features in Templates

Templates support full Jinja2 syntax:

- **Variables:** `{{ variable }}`
- **Conditionals:** `{% if valid %}...{% else %}...{% endif %}`
- **Loops:** `{% for item in list %}{{ item }}{% endfor %}`
- **Filters:** `{{ data | tojson }}`, `{{ text | truncate(100) }}`
- **Nested access:** `{{ parsed_json.field.nested }}`

### Example: Conditional Output Based on Validation

```yaml
format_template: |
  {% if valid %}
  ✓ Success: {{ parsed_json.title }}
  {{ parsed_json | tojson }}
  {% else %}
  ✗ Validation failed
  {{ assistant }}
  {% endif %}
```
