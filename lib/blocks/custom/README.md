# custom blocks

experimental or project-specific blocks.

## purpose

custom blocks are for:
- experimental features
- project-specific logic
- testing new ideas before promoting to builtin

## creating custom blocks

1. create python file in this directory
2. inherit from baseblock
3. define required properties:
   - name: display name
   - description: what it does
   - inputs: list of required input fields
   - outputs: list of output fields

example:

```python
from lib.blocks.base import BaseBlock
from typing import Any

class MyCustomBlock(BaseBlock):
    name = "my custom block"
    description = "does something custom"
    inputs = ["text"]
    outputs = ["result"]

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # your logic here
        return {"result": data["text"].upper()}
```

## notes

- custom blocks are auto-discovered on startup
- no need to register manually
- outputs must match declared schema
- use async/await for all execute methods
