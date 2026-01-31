"""
Pipeline templates for quick onboarding and testing
"""

import json
import logging
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from lib.entities.extensions import TemplateInfo

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """Registry for pipeline templates with builtin and user template support"""

    def __init__(
        self,
        templates_dir: Path | None = None,
        user_templates_dir: Path | None = None,
    ):
        if templates_dir is None:
            templates_dir = Path(__file__).parent
        self.templates_dir = templates_dir
        self.seeds_dir = templates_dir / "seeds"
        self._templates: dict[str, dict[str, Any]] = {}
        self._sources: dict[str, str] = {}
        self._load_templates()

        if user_templates_dir and user_templates_dir.exists():
            self._load_user_templates(user_templates_dir)

    def _load_templates(self) -> None:
        """load all template yaml files from builtin templates directory"""
        for template_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(template_file, "r") as f:
                    template_data = yaml.safe_load(f)
                    template_id = template_file.stem

                    # load example seed if it exists (json or markdown)
                    seed_json = self.seeds_dir / f"seed_{template_id}.json"
                    seed_md = self.seeds_dir / f"seed_{template_id}.md"

                    if seed_json.exists():
                        with open(seed_json, "r") as sf:
                            template_data["example_seed"] = json.load(sf)
                    elif seed_md.exists():
                        with open(seed_md, "r") as sf:
                            # markdown seed is wrapped in json format for file_content
                            template_data["example_seed"] = [
                                {"repetitions": 1, "metadata": {"file_content": sf.read()}}
                            ]

                    self._templates[template_id] = template_data
                    self._sources[template_id] = "builtin"
            except Exception:
                pass

    def _load_user_templates(self, user_dir: Path) -> None:
        """load user templates, skipping ids that already exist as builtin"""
        for template_file in user_dir.glob("*.yaml"):
            try:
                with open(template_file, "r") as f:
                    template_data = yaml.safe_load(f)
                    template_id = template_file.stem

                    # builtin takes precedence
                    if template_id in self._templates:
                        logger.warning(
                            f"user template '{template_id}' skipped: conflicts with builtin"
                        )
                        continue

                    self._templates[template_id] = template_data
                    self._sources[template_id] = "user"
            except Exception:
                logger.warning(f"failed to load user template {template_file}")

    def register(
        self,
        template_id: str,
        template_data: dict[str, Any],
        source: str = "user",
    ) -> None:
        self._templates[template_id] = template_data
        self._sources[template_id] = source

    def unregister(self, template_id: str) -> None:
        self._templates.pop(template_id, None)
        self._sources.pop(template_id, None)

    def list_templates(self) -> list[TemplateInfo]:
        """List all available templates"""
        return [
            TemplateInfo(
                id=template_id,
                name=template["name"],
                description=template["description"],
                example_seed=template.get("example_seed"),
                source=self._sources.get(template_id, "builtin"),
            )
            for template_id, template in self._templates.items()
        ]

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        """Get template definition by ID"""
        return self._templates.get(template_id)

    def get_template_source(self, template_id: str) -> str | None:
        return self._sources.get(template_id)


# Singleton instance
template_registry = TemplateRegistry()
