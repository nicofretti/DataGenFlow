# builtin blocks

stable, tested blocks included with datagenflow.

## available blocks

- **llmblock**: generate text using llm with jinja2 template rendering
- **validatorblock**: validate text content (length, forbidden words)
- **jsonvalidatorblock**: parse and validate JSON from any field in accumulated state
  - config: `field_name` (which field to validate), `required_fields` (list), `strict` (bool)
  - inputs: * (all accumulated state)
  - outputs: valid (bool), parsed_json (object/null)
- **outputblock**: define final pipeline output using jinja2 templates for the review system

## usage

blocks are auto-discovered by the registry. create pipelines using block types in the ui or api.

## adding new builtin blocks

1. create new file in this directory
2. inherit from baseblock
3. define name, description, inputs, outputs
4. implement execute method
5. add tests in tests/blocks/
