import logging
from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext

logger = logging.getLogger(__name__)


class JSONFieldExtractorBlock(BaseBlock):
    name = "JSON Field Extractor"
    description = "Extract fields from nested JSON structures into flat top-level fields"
    category = "utilities"
    inputs = []
    outputs = []  # dynamic based on mappings

    _field_references = ["source_field"]

    _config_descriptions = {
        "source_field": "Field containing the nested JSON structure",
        "mappings": (
            "List of field mappings. Each mapping has 'from' (nested path like "
            "'qa_pairs.0.question') and 'to' (output field name like 'question')"
        ),
    }

    def __init__(
        self,
        source_field: str = "parsed_json",
        mappings: list[dict[str, str]] | dict[str, Any] | str | None = None,
    ):
        """
        Args:
            source_field: Field containing the nested structure
            mappings: List of mappings [{"from": "path.to.field", "to": "output_name"}]
                     Can be a list, dict (UI quirk), or JSON string
        """
        import json

        # declare types for instance variables
        self.source_field: str
        self.mappings: list[dict[str, str]]

        # handle UI quirk: mappings might be double-nested
        if isinstance(mappings, dict) and "mappings" in mappings:
            # UI sent: {"source_field": "...", "mappings": [...]}
            self.source_field = str(mappings.get("source_field", source_field))
            raw_mappings = mappings.get("mappings", [])
            self.mappings = raw_mappings if isinstance(raw_mappings, list) else []
        else:
            self.source_field = source_field
            # handle mappings as string (JSON) or list
            if isinstance(mappings, str):
                try:
                    parsed = json.loads(mappings)
                    self.mappings = parsed if isinstance(parsed, list) else []
                except json.JSONDecodeError:
                    logger.error(f"failed to parse mappings as json: {mappings}")
                    self.mappings = []
            elif isinstance(mappings, list):
                self.mappings = mappings
            else:
                self.mappings = []

        # validate mappings is a list
        if not isinstance(self.mappings, list):
            logger.error(f"mappings must be a list, got {type(self.mappings).__name__}")
            self.mappings = []

        # set dynamic outputs based on mappings
        if self.mappings:
            self.outputs = [
                m.get("to", "") for m in self.mappings if isinstance(m, dict) and "to" in m
            ]

    def _resolve_path(self, data: Any, path: str) -> Any:
        """resolve nested path like 'qa_pairs.0.question' in data structure"""
        if not path:
            return data

        parts = path.split(".")
        current = data

        for part in parts:
            if current is None:
                return None

            # handle array index (e.g., "0", "1")
            if isinstance(current, list):
                try:
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        logger.warning(
                            f"index {index} out of bounds for array (length: {len(current)})"
                        )
                        return None
                except ValueError:
                    logger.warning(f"invalid array index: {part}")
                    return None
            # handle dict key
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                logger.warning(f"cannot access '{part}' on type {type(current).__name__}")
                return None

        return current

    def _extract_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        """extract fields based on mappings configuration"""
        result: dict[str, Any] = {}

        # get source data
        source_data = data.get(self.source_field)
        if source_data is None:
            logger.error(
                f"source field '{self.source_field}' not found. "
                f"Available fields: {list(data.keys())}"
            )
            return {m["to"]: "" for m in self.mappings if "to" in m}

        # handle string json (parse it)
        if isinstance(source_data, str):
            import json

            try:
                source_data = json.loads(source_data)
            except json.JSONDecodeError:
                logger.warning(f"failed to parse source field '{self.source_field}' as json")
                return {m["to"]: "" for m in self.mappings if "to" in m}

        # extract each mapped field
        for mapping in self.mappings:
            from_path = mapping.get("from", "")
            to_field = mapping.get("to", "")

            if not from_path or not to_field:
                logger.warning(f"invalid mapping: {mapping}")
                continue

            value = self._resolve_path(source_data, from_path)

            logger.info(
                f"Extracted '{from_path}' -> '{to_field}': "
                f"value={value if value else 'EMPTY'} (type={type(value).__name__})"
            )

            # convert to string if not already
            if value is None:
                result[to_field] = ""
            elif isinstance(value, (dict, list)):
                # keep complex structures as-is
                result[to_field] = value
            else:
                result[to_field] = str(value)

        logger.info(f"JSON Field Extractor final output: {result}")
        return result

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        if not self.mappings:
            logger.warning("no mappings configured, returning empty result")
            return {}

        return self._extract_fields(context.accumulated_state)
