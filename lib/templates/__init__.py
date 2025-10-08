"""
Pipeline templates for quick onboarding and testing
"""
import yaml
from pathlib import Path
from typing import Any


class TemplateRegistry:
    """Registry for pipeline templates"""

    def __init__(self, templates_dir: Path | None = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent
        self.templates_dir = templates_dir
        self._templates: dict[str, dict[str, Any]] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """load all template yaml files from templates directory"""
        for template_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(template_file, "r") as f:
                    template_data = yaml.safe_load(f)
                    template_id = template_file.stem
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
            }
            for template_id, template in self._templates.items()
        ]

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        """Get template definition by ID"""
        return self._templates.get(template_id)


# Singleton instance
template_registry = TemplateRegistry()
