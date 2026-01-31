"""
Tests for enhanced TemplateRegistry: user templates dir, source tracking, register/unregister.
"""
import yaml

from lib.entities.extensions import TemplateInfo
from lib.templates import TemplateRegistry


def _write_template(path, name="Test Template", desc="A test", blocks=None):
    blocks = blocks or [{"type": "TextGenerator", "config": {"temperature": 0.5}}]
    data = {"name": name, "description": desc, "blocks": blocks}
    path.write_text(yaml.dump(data))


# --- source tracking ---


def test_builtin_templates_have_source():
    reg = TemplateRegistry()
    templates = reg.list_templates()
    for t in templates:
        assert isinstance(t, TemplateInfo)
        assert t.source == "builtin"


# --- user templates dir ---


def test_loads_user_templates(tmp_path):
    user_dir = tmp_path / "user_templates"
    user_dir.mkdir()
    _write_template(user_dir / "my_custom.yaml", name="My Custom")

    reg = TemplateRegistry(user_templates_dir=user_dir)
    templates = reg.list_templates()
    ids = {t.id for t in templates}
    assert "my_custom" in ids

    custom = next(t for t in templates if t.id == "my_custom")
    assert custom.source == "user"
    assert custom.name == "My Custom"


def test_user_templates_dont_override_builtin(tmp_path):
    """if user template has same id as builtin, builtin wins"""
    user_dir = tmp_path / "user_templates"
    user_dir.mkdir()
    _write_template(user_dir / "json_generation.yaml", name="Hijacked")

    reg = TemplateRegistry(user_templates_dir=user_dir)
    t = reg.get_template("json_generation")
    assert t is not None
    assert t["name"] != "Hijacked"


# --- register / unregister ---


def test_register_user_template():
    reg = TemplateRegistry()
    initial = len(reg.list_templates())
    reg.register(
        "my_new",
        {"name": "My New", "description": "New template", "blocks": []},
        source="user",
    )
    assert len(reg.list_templates()) == initial + 1
    t = reg.get_template("my_new")
    assert t is not None
    assert t["name"] == "My New"


def test_unregister_template():
    reg = TemplateRegistry()
    reg.register("to_remove", {"name": "Remove Me", "description": "...", "blocks": []}, source="user")
    assert reg.get_template("to_remove") is not None

    reg.unregister("to_remove")
    assert reg.get_template("to_remove") is None


def test_unregister_nonexistent_is_noop():
    reg = TemplateRegistry()
    reg.unregister("does_not_exist")  # should not raise


def test_get_template_source():
    reg = TemplateRegistry()
    reg.register("user_t", {"name": "U", "description": "...", "blocks": []}, source="user")
    assert reg.get_template_source("json_generation") == "builtin"
    assert reg.get_template_source("user_t") == "user"
    assert reg.get_template_source("nonexistent") is None
