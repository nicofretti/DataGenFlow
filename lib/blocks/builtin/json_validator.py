import json
import re
from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError
from lib.template_renderer import render_template


class JSONValidatorBlock(BaseBlock):
    name = "JSON Validator"
    description = "Parse and validate JSON from any field in accumulated state"
    category = "validators"
    inputs = ["*"]
    outputs = ["valid", "parsed_json"]

    _field_references = ["field_name"]

    _config_descriptions = {
        "required_fields": (
            'JSON array or Jinja template. Examples: ["name", "email"] or '
            "{{ required_fields | tojson }} (leave empty for none)"
        )
    }

    _config_formats = {
        "required_fields": "json-or-template",
    }

    def __init__(
        self,
        field_name: str = "assistant",
        required_fields: str | list[str] = "",
        strict: bool = False,
    ) -> None:
        """
        validate JSON structure from specified field

        args:
            field_name: name of field in accumulated state to validate
            required_fields: JSON array or Jinja template of field names that must be present
            strict: if true, fail on parse errors; if false, mark as invalid but continue
        """
        self.field_name = field_name
        # handle both string (from UI/templates with jinja) and list (from static YAML)
        if isinstance(required_fields, list):
            self.required_fields_template = json.dumps(required_fields)
        else:
            self.required_fields_template = required_fields if required_fields else ""
        self.strict = strict

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        # parse required_fields from template (optional)
        required_fields: list[str] = []
        if self.required_fields_template:
            fields_rendered = render_template(
                self.required_fields_template, context.accumulated_state
            )
            try:
                fields_list = json.loads(fields_rendered)
                if not isinstance(fields_list, list):
                    raise BlockExecutionError(
                        "required_fields must be a JSON array",
                        detail={"rendered_value": fields_rendered},
                    )
                if not all(isinstance(f, str) for f in fields_list):
                    raise BlockExecutionError(
                        "All items in required_fields must be strings",
                        detail={"required_fields": fields_list},
                    )
                required_fields = fields_list
            except json.JSONDecodeError as e:
                raise BlockExecutionError(
                    f"required_fields must be valid JSON: {str(e)}",
                    detail={
                        "template": self.required_fields_template,
                        "rendered": fields_rendered,
                    },
                )

        field_output = context.get_state(self.field_name, "")

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
        if required_fields:
            missing_fields = [field for field in required_fields if field not in parsed]
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
