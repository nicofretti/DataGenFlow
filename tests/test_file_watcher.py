"""
Tests for file watcher module: debouncing, start/stop, reload on file changes.
"""
import time
from pathlib import Path

from lib.blocks.registry import BlockRegistry
from lib.templates import TemplateRegistry


class TestDebouncedHandler:
    def test_debounce_multiple_events(self):
        """multiple rapid events result in single callback"""
        from lib.file_watcher import DebouncedHandler

        call_count = 0

        def callback(path: Path, event_type: str):
            nonlocal call_count
            call_count += 1

        handler = DebouncedHandler(callback, debounce_ms=50)

        test_path = Path("/tmp/test.py")
        handler._schedule_callback(test_path, "modified")
        handler._schedule_callback(test_path, "modified")
        handler._schedule_callback(test_path, "modified")

        time.sleep(0.15)
        assert call_count == 1

    def test_different_paths_not_debounced(self):
        """events for different paths fire independently"""
        from lib.file_watcher import DebouncedHandler

        paths_seen: list[str] = []

        def callback(path: Path, event_type: str):
            paths_seen.append(str(path))

        handler = DebouncedHandler(callback, debounce_ms=50)

        handler._schedule_callback(Path("/tmp/a.py"), "modified")
        handler._schedule_callback(Path("/tmp/b.py"), "modified")

        time.sleep(0.15)
        assert len(paths_seen) == 2


class TestExtensionFileWatcher:
    def test_watcher_starts_and_stops(self, tmp_path):
        from lib.file_watcher import ExtensionFileWatcher

        blocks_dir = tmp_path / "user_blocks"
        blocks_dir.mkdir()
        templates_dir = tmp_path / "user_templates"
        templates_dir.mkdir()

        watcher = ExtensionFileWatcher(
            block_registry=BlockRegistry(),
            template_registry=TemplateRegistry(),
            blocks_path=blocks_dir,
            templates_path=templates_dir,
        )

        watcher.start()
        assert watcher.is_running

        watcher.stop()
        assert not watcher.is_running

    def test_watcher_noop_when_disabled(self, tmp_path, monkeypatch):
        from lib.file_watcher import ExtensionFileWatcher

        monkeypatch.setenv("DATAGENFLOW_HOT_RELOAD", "false")

        blocks_dir = tmp_path / "user_blocks"
        blocks_dir.mkdir()
        templates_dir = tmp_path / "user_templates"
        templates_dir.mkdir()

        watcher = ExtensionFileWatcher(
            block_registry=BlockRegistry(),
            template_registry=TemplateRegistry(),
            blocks_path=blocks_dir,
            templates_path=templates_dir,
        )

        watcher.start()
        assert not watcher.is_running

    def test_stop_when_not_started_is_noop(self):
        from lib.file_watcher import ExtensionFileWatcher

        watcher = ExtensionFileWatcher(
            block_registry=BlockRegistry(),
            template_registry=TemplateRegistry(),
        )
        watcher.stop()  # should not raise
        assert not watcher.is_running
