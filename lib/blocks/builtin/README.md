# builtin blocks

stable, tested blocks included with qadatagen.

## available blocks

- **llmblock**: generate text using llm
- **transformerblock**: text transformations (uppercase, lowercase, trim, strip)
- **validatorblock**: validate text content (length, forbidden words)
- **formatterblock**: custom output formatting

## usage

blocks are auto-discovered by the registry. create pipelines using block types in the ui or api.

## adding new builtin blocks

1. create new file in this directory
2. inherit from baseblock
3. define name, description, inputs, outputs
4. implement execute method
5. add tests in tests/blocks/
