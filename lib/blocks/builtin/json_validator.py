import json
import re
from typing import Any

from lib.blocks.base import BaseBlock


class JSONValidatorBlock(BaseBlock):
    name = "JSON Validator"
    description = "Parse and validate JSON from any field in accumulated state"
    category = "validators"
    inputs = ["*"]
    outputs = ["valid", "parsed_json"]

    _field_references = ["field_name"]

    def __init__(
        self,
        field_name: str = "assistant",
        required_fields: list[str] | None = None,
        strict: bool = False,
    ) -> None:
        """
        validate JSON structure from specified field

        args:
            field_name: name of field in accumulated state to validate
            required_fields: list of field names that must be present in the JSON
            strict: if true, fail on parse errors; if false, mark as invalid but continue
        """
        self.field_name = field_name
        self.required_fields = required_fields or []
        self.strict = strict

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        field_output = data.get(self.field_name, "")

        # if already parsed (e.g., from StructuredGenerator), use it directly
        if isinstance(field_output, dict) or isinstance(field_output, list):
            parsed = field_output
        else:
            # remove the ```json ... ``` if needed
            field_output = re.sub(
                r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", r"\1", field_output, flags=re.DOTALL
            ).strip()

            try:
                # try to parse JSON from specified field
                parsed = json.loads(field_output)
            except json.JSONDecodeError as e:
                if self.strict:
                    raise ValueError(f"invalid JSON: {str(e)}")

                # not strict mode, mark as invalid but continue
                return {
                    "valid": False,
                    "parsed_json": None,
                }

        # validate parsed JSON
        # check if required fields are present
        if self.required_fields:
            missing_fields = [field for field in self.required_fields if field not in parsed]
            if missing_fields:
                return {
                    "valid": False,
                    "parsed_json": None,
                }

        # validation passed
        return {
            "valid": True,
            "parsed_json": parsed,
        }
