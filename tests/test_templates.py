import pytest
from lib.templates import TemplateRegistry


def test_customer_service_template_exists():
    registry = TemplateRegistry()
    template = registry.get_template("customer_service_conversations")

    assert template is not None
    assert template["name"] == "Customer Service Conversations"
    assert len(template["blocks"]) == 5  # Persona, Dialogue, BackTranslation, Validator, Metrics


def test_customer_service_template_has_blocks_with_configs():
    registry = TemplateRegistry()
    template = registry.get_template("customer_service_conversations")

    blocks = template["blocks"]
    assert blocks[0]["type"] == "PersonaGeneratorBlock"
    assert "config" in blocks[0]
    assert blocks[1]["type"] == "DialogueGeneratorBlock"


def test_template_registry_lists_templates():
    registry = TemplateRegistry()
    templates = registry.list_templates()

    assert len(templates) > 0
    template_ids = [t["id"] for t in templates]
    assert "customer_service_conversations" in template_ids
