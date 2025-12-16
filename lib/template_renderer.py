import json
import logging
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """jinja2-based template renderer with custom filters and safe error handling"""

    def __init__(self) -> None:
        self.env = Environment(
            undefined=StrictUndefined,
            autoescape=False,
        )
        self._register_custom_filters()

    def _register_custom_filters(self) -> None:
        """register custom jinja2 filters"""
        # add json filter for pretty-printing dicts/lists
        self.env.filters["tojson"] = lambda obj: json.dumps(obj, indent=2)

        # add truncate filter
        self.env.filters["truncate"] = (
            lambda s, length=100: s[:length] + "..." if len(s) > length else s
        )

    def render(self, template_str: str, context: dict[str, Any]) -> str:
        """
        render a jinja2 template with the given context

        supports:
        - variables: {{ variable }}
        - conditionals: {% if condition %} ... {% endif %}
        - loops: {% for item in list %} ... {% endfor %}
        - filters: {{ variable | upper }}, {{ dict | tojson }}
        - nested access: {{ state.field.nested }}
        """
        try:
            template = self.env.from_string(template_str)
            return template.render(**context)
        except TemplateSyntaxError as e:
            raise ValueError(f"template syntax error at line {e.lineno}: {e.message}")
        except UndefinedError as e:
            raise ValueError(f"undefined variable in template: {e.message}")
        except Exception as e:
            logger.exception("template rendering error")
            raise ValueError(f"template rendering error: {str(e)}") from e


# singleton instance
_renderer = TemplateRenderer()


def render_template(template_str: str, context: dict[str, Any]) -> str:
    """convenience function to render a template using the global renderer"""
    return _renderer.render(template_str, context)
