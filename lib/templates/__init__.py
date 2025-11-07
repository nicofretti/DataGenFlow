"""
Pipeline templates for quick onboarding and testing
"""

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


class TemplateRegistry:
    """Registry for pipeline templates"""

    def __init__(self, templates_dir: Path | None = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent
        self.templates_dir = templates_dir
        self.seeds_dir = templates_dir / "seeds"
        self._templates: dict[str, dict[str, Any]] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """load all template yaml files from templates directory"""
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
            except Exception:
                pass

    def list_templates(self) -> list[dict[str, Any]]:
        """List all available templates"""
        return [
            {
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "example_seed": template.get("example_seed"),
            }
            for template_id, template in self._templates.items()
        ]

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        """Get template definition by ID"""
        return self._templates.get(template_id)


# Singleton instance
template_registry = TemplateRegistry()
