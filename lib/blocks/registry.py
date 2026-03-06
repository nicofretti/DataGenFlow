import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from lib.blocks.base import BaseBlock, BaseMultiplierBlock
from lib.entities.extensions import BlockInfo

logger = logging.getLogger(__name__)

# resolve builtin/custom paths relative to this file so they work regardless of cwd
_BLOCKS_DIR = Path(__file__).resolve().parent

# maps (path, module_prefix) to source label
_SOURCE_MAP = {
    (_BLOCKS_DIR / "builtin", "lib.blocks.builtin"): "builtin",
    (_BLOCKS_DIR / "custom", "lib.blocks.custom"): "custom",
    (Path("user_blocks"), "user_blocks"): "user",
}


class BlockEntry(BaseModel):
    """internal registry entry — wraps a block class with extensibility metadata"""

    block_class: Any | None = None  # type[BaseBlock]; None when import failed
    type_name: str = ""  # used as fallback type when block_class is None
    source: str = "builtin"
    available: bool = True
    error: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    def to_block_info(self) -> BlockInfo:
        if self.block_class is None:
            return BlockInfo(
                type=self.type_name,
                name=self.type_name,
                description="",
                category="",
                inputs=[],
                outputs=[],
                config_schema={},
                source=self.source,
                available=False,
                error=self.error,
            )
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
        self._entries = self._discover_blocks()

    def _discover_blocks(self) -> dict[str, BlockEntry]:
        """scan all block directories and return a fresh entries dict"""
        entries: dict[str, BlockEntry] = {}
        for (blocks_path, module_prefix), source in _SOURCE_MAP.items():
            if not blocks_path.exists():
                continue

            for py_file in blocks_path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                module_name = f"{module_prefix}.{py_file.stem}"
                try:
                    # reload already-imported modules so file changes are picked up
                    module = (
                        importlib.reload(sys.modules[module_name])
                        if module_name in sys.modules
                        else importlib.import_module(module_name)
                    )
                    for _name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, BaseBlock)
                            and obj not in (BaseBlock, BaseMultiplierBlock)
                            and obj.__module__ == module.__name__
                        ):
                            entries[obj.__name__] = BlockEntry(block_class=obj, source=source)
                except Exception as e:
                    logger.warning(f"failed to load block module {module_name}: {e}")
                    # register as unavailable so the UI can surface the failure
                    entries[py_file.stem] = BlockEntry(
                        type_name=py_file.stem,
                        source=source,
                        available=False,
                        error=str(e),
                    )
        return entries

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

    def reload(self) -> None:
        """re-scan all block directories and refresh the registry.
        uses atomic swap so concurrent readers never see an empty registry."""
        self._entries = self._discover_blocks()

    def unregister(self, block_type: str) -> None:
        self._entries.pop(block_type, None)

    def get_block_class(self, block_type: str) -> type[BaseBlock] | None:
        entry = self._entries.get(block_type)
        return entry.block_class if entry else None

    def list_block_types(self) -> list[str]:
        return list(self._entries.keys())

    def get_entry(self, block_type: str) -> BlockEntry | None:
        return self._entries.get(block_type)

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
