"""
Template registry regression tests — lock current TemplateRegistry behavior.
"""
from lib.entities.extensions import TemplateInfo
from lib.templates import TemplateRegistry, template_registry


def test_singleton_has_builtin_templates():
    templates = template_registry.list_templates()
    ids = {t.id for t in templates}
    assert "json_generation" in ids
    assert "text_classification" in ids
    assert "qa_generation" in ids
    assert "ragas_evaluation" in ids


def test_get_template_returns_dict():
    t = template_registry.get_template("json_generation")
    assert t is not None
    assert "name" in t
    assert "blocks" in t


def test_get_template_returns_none_for_unknown():
    assert template_registry.get_template("nonexistent") is None


def test_list_templates_shape():
    templates = template_registry.list_templates()
    for t in templates:
        assert isinstance(t, TemplateInfo)
        assert t.id
        assert t.name
        assert t.description


def test_template_blocks_reference_valid_types():
    """all block types in templates must exist in the block registry"""
    from lib.blocks.registry import BlockRegistry

    reg = BlockRegistry()
    available = {b.type for b in reg.list_blocks()}

    for t in template_registry.list_templates():
        full = template_registry.get_template(t.id)
        assert full is not None, f"Template '{t.id}' returned None"
        for block in full["blocks"]:
            assert block["type"] in available, (
                f"Template '{t.id}' references unknown block type '{block['type']}'"
            )


def test_template_registry_custom_dir(tmp_path):
    """TemplateRegistry with empty dir returns no templates"""
    reg = TemplateRegistry(templates_dir=tmp_path)
    assert reg.list_templates() == []
