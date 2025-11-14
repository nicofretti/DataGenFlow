import importlib
import inspect
import logging
from pathlib import Path
from typing import Any

from lib.blocks.base import BaseBlock, BaseMultiplierBlock

logger = logging.getLogger(__name__)


class BlockRegistry:
    def __init__(self) -> None:
        self._blocks: dict[str, type[BaseBlock]] = {}
        self._discover_blocks()

    def _discover_blocks(self) -> None:
        # scan lib/blocks/builtin/, lib/blocks/custom/, and user_blocks/ for block classes
        scan_dirs = [
            "lib/blocks/builtin",
            "lib/blocks/custom",
            "user_blocks",
        ]

        for blocks_dir in scan_dirs:
            blocks_path = Path(blocks_dir)
            if not blocks_path.exists():
                continue

            for py_file in blocks_path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                module_name = f"{blocks_dir.replace('/', '.')}.{py_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # only register classes inheriting from BaseBlock, excluding base classes
                        if issubclass(obj, BaseBlock) and obj not in (
                            BaseBlock,
                            BaseMultiplierBlock,
                        ):
                            self._blocks[obj.__name__] = obj
                except Exception as e:
                    logger.warning(f"failed to load block module {module_name}: {e}")
                    continue

    def get_block_class(self, block_type: str) -> type[BaseBlock] | None:
        return self._blocks.get(block_type)

    def list_blocks(self) -> list[dict[str, Any]]:
        return [block_class.get_schema() for block_class in self._blocks.values()]


# singleton instance
registry = BlockRegistry()
