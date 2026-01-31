"""
File watcher for hot reload of extensions.

Monitors user_blocks/ and user_templates/ for changes
and triggers registry reload when files are added, modified, or deleted.
"""

import logging
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

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

    def _execute_callback(self, path: Path, event_type: str) -> None:
        with self._lock:
            self._pending.pop(str(path), None)

        try:
            self.callback(path, event_type)
        except Exception as e:
            logger.exception(f"error in file watcher callback: {e}")

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule_callback(Path(event.src_path), "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule_callback(Path(event.src_path), "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule_callback(Path(event.src_path), "deleted")


class BlockFileHandler(DebouncedHandler):
    """handler for block file changes — triggers registry rediscovery"""

    def __init__(self, registry: "BlockRegistry", debounce_ms: int = 500):
        self.registry = registry
        super().__init__(self._handle_change, debounce_ms)

    def _handle_change(self, path: Path, event_type: str) -> None:
        if path.suffix != ".py" or path.name.startswith("_"):
            return

        logger.info(f"block file {event_type}: {path}")
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

        logger.info(f"template file {event_type}: {path}")

        if event_type == "deleted":
            self.registry.unregister(path.stem)
        else:
            self.registry._load_user_templates(self.user_dir)


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
        self.blocks_path = blocks_path or Path(
            os.getenv("DATAGENFLOW_BLOCKS_PATH", "user_blocks")
        )
        self.templates_path = templates_path or Path(
            os.getenv("DATAGENFLOW_TEMPLATES_PATH", "user_templates")
        )
        self._observer: Observer | None = None

    @property
    def is_running(self) -> bool:
        return self._observer is not None

    def start(self) -> None:
        hot_reload = os.getenv("DATAGENFLOW_HOT_RELOAD", "true").lower() == "true"
        if not hot_reload:
            logger.info("hot reload disabled")
            return

        self._observer = Observer()
        debounce_ms = int(os.getenv("DATAGENFLOW_HOT_RELOAD_DEBOUNCE_MS", "500"))

        if self.blocks_path.exists():
            self._observer.schedule(
                BlockFileHandler(self.block_registry, debounce_ms),
                str(self.blocks_path),
                recursive=False,
            )
            logger.info(f"watching {self.blocks_path} for block changes")

        if self.templates_path.exists():
            self._observer.schedule(
                TemplateFileHandler(self.template_registry, self.templates_path, debounce_ms),
                str(self.templates_path),
                recursive=False,
            )
            logger.info(f"watching {self.templates_path} for template changes")

        self._observer.start()
        logger.info("extension file watcher started")

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("extension file watcher stopped")
