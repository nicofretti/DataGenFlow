"""
File watcher for hot reload of extensions.

Monitors user_blocks/ and user_templates/ for changes
and triggers registry reload when files are added, modified, or deleted.
"""

import logging
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from lib.constants import DEFAULT_BLOCKS_PATH, DEFAULT_TEMPLATES_PATH

if TYPE_CHECKING:
    from lib.blocks.registry import BlockRegistry
    from lib.templates import TemplateRegistry

logger = logging.getLogger(__name__)


class DebouncedHandler(FileSystemEventHandler):
    """file event handler with debouncing to prevent rapid reloads"""

    def __init__(
        self,
        callback: Callable[[Path, str], None],
        debounce_ms: int = 500,
    ):
        self.callback = callback
        self.debounce_ms = debounce_ms
        self._pending: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _schedule_callback(self, path: Path, event_type: str) -> None:
        key = str(path)

        with self._lock:
            if key in self._pending:
                self._pending[key].cancel()

            timer = threading.Timer(
                self.debounce_ms / 1000,
                self._execute_callback,
                args=(path, event_type),
            )
            self._pending[key] = timer
            timer.start()

    def cancel_pending(self) -> None:
        with self._lock:
            for timer in self._pending.values():
                timer.cancel()
            self._pending.clear()

    def _execute_callback(self, path: Path, event_type: str) -> None:
        with self._lock:
            self._pending.pop(str(path), None)

        try:
            self.callback(path, event_type)
        except Exception:
            logger.exception("error in file watcher callback")

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule_callback(Path(os.fsdecode(event.src_path)), "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule_callback(Path(os.fsdecode(event.src_path)), "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule_callback(Path(os.fsdecode(event.src_path)), "deleted")


class BlockFileHandler(DebouncedHandler):
    """handler for block file changes — triggers registry rediscovery"""

    def __init__(self, registry: "BlockRegistry", debounce_ms: int = 500):
        self.registry = registry
        super().__init__(self._handle_change, debounce_ms)

    def _handle_change(self, path: Path, event_type: str) -> None:
        if path.suffix != ".py" or path.name.startswith("_"):
            return

        logger.info("block file %s: %s", event_type, path)
        self.registry.reload()


class TemplateFileHandler(DebouncedHandler):
    """handler for template file changes"""

    def __init__(self, registry: "TemplateRegistry", user_dir: Path, debounce_ms: int = 500):
        self.registry = registry
        self.user_dir = user_dir
        super().__init__(self._handle_change, debounce_ms)

    def _handle_change(self, path: Path, event_type: str) -> None:
        if path.suffix not in (".yaml", ".yml"):
            return

        logger.info("template file %s: %s", event_type, path)
        # full reload is safe — uses atomic swap internally
        self.registry.reload()


class ExtensionFileWatcher:
    """watches extension directories for changes"""

    def __init__(
        self,
        block_registry: "BlockRegistry",
        template_registry: "TemplateRegistry",
        blocks_path: Path | None = None,
        templates_path: Path | None = None,
    ):
        self.block_registry = block_registry
        self.template_registry = template_registry
        self.blocks_path = (
            blocks_path or Path(os.getenv("DATAGENFLOW_BLOCKS_PATH", DEFAULT_BLOCKS_PATH)).resolve()
        )
        self.templates_path = (
            templates_path
            or Path(os.getenv("DATAGENFLOW_TEMPLATES_PATH", DEFAULT_TEMPLATES_PATH)).resolve()
        )
        self._observer: Any = None  # watchdog.Observer, no stubs available
        self._handlers: list[DebouncedHandler] = []

    @property
    def is_running(self) -> bool:
        return self._observer is not None

    def start(self) -> None:
        hot_reload = os.getenv("DATAGENFLOW_HOT_RELOAD", "true").lower() == "true"
        if not hot_reload:
            logger.info("hot reload disabled")
            return

        self._observer = Observer()
        self._handlers = []
        debounce_ms = int(os.getenv("DATAGENFLOW_HOT_RELOAD_DEBOUNCE_MS", "500"))

        if self.blocks_path.exists():
            block_handler = BlockFileHandler(self.block_registry, debounce_ms)
            self._observer.schedule(block_handler, str(self.blocks_path), recursive=False)
            self._handlers.append(block_handler)
            logger.info("watching %s for block changes", self.blocks_path)

        if self.templates_path.exists():
            template_handler = TemplateFileHandler(
                self.template_registry, self.templates_path, debounce_ms
            )
            self._observer.schedule(template_handler, str(self.templates_path), recursive=False)
            self._handlers.append(template_handler)
            logger.info("watching %s for template changes", self.templates_path)

        self._observer.start()
        logger.info("extension file watcher started")

    def stop(self) -> None:
        if self._observer:
            for handler in self._handlers:
                handler.cancel_pending()
            self._handlers = []
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("extension file watcher stopped")
