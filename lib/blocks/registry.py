import importlib
import inspect
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from lib.blocks.base import BaseBlock, BaseMultiplierBlock
from lib.entities.extensions import BlockInfo

logger = logging.getLogger(__name__)

# maps directory prefixes to source labels
_SOURCE_MAP = {
    "lib/blocks/builtin": "builtin",
    "lib/blocks/custom": "custom",
    "user_blocks": "user",
}


class BlockEntry(BaseModel):
    """internal registry entry — wraps a block class with extensibility metadata"""

    block_class: Any  # type[BaseBlock], but pydantic can't validate arbitrary classes
    source: str = "builtin"
    available: bool = True
    error: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    def to_block_info(self) -> BlockInfo:
        schema = self.block_class.get_schema()
        return BlockInfo(
            source=self.source,
            available=self.available,
            error=self.error,
            **schema,
        )


class BlockRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, BlockEntry] = {}
        self._discover_blocks()

    def _discover_blocks(self) -> None:
        for blocks_dir, source in _SOURCE_MAP.items():
            blocks_path = Path(blocks_dir)
            if not blocks_path.exists():
                continue

            for py_file in blocks_path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                module_name = f"{blocks_dir.replace('/', '.')}.{py_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    for _name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BaseBlock) and obj not in (
                            BaseBlock,
                            BaseMultiplierBlock,
                        ):
                            self._entries[obj.__name__] = BlockEntry(
                                block_class=obj, source=source
                            )
                except Exception as e:
                    logger.warning(f"failed to load block module {module_name}: {e}")
                    continue

    def register(
        self,
        block_class: type[BaseBlock],
        source: str = "user",
        available: bool = True,
        error: str | None = None,
    ) -> None:
        self._entries[block_class.__name__] = BlockEntry(
            block_class=block_class,
            source=source,
            available=available,
            error=error,
        )

    def unregister(self, block_type: str) -> None:
        self._entries.pop(block_type, None)

    def get_block_class(self, block_type: str) -> type[BaseBlock] | None:
        entry = self._entries.get(block_type)
        return entry.block_class if entry else None

    def list_block_types(self) -> list[str]:
        return list(self._entries.keys())

    def get_block_source(self, block_type: str) -> str | None:
        entry = self._entries.get(block_type)
        return entry.source if entry else None

    def list_blocks(self) -> list[BlockInfo]:
        return [entry.to_block_info() for entry in self._entries.values()]

    def compute_accumulated_state_schema(self, blocks: list[dict[str, Any]]) -> list[str]:
        """
        returns list of field names that will be in accumulated state
        by examining block outputs from registry
        """
        fields: set[str] = set()

        for block_def in blocks:
            block_type = block_def["type"]
            block_class = self.get_block_class(block_type)

            if block_class and hasattr(block_class, "outputs"):
                fields.update(block_class.outputs)

        return sorted(list(fields))


# singleton instance
registry = BlockRegistry()
