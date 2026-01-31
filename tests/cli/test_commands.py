"""
Tests for dgf CLI commands.
Uses typer CliRunner to test commands without a running server.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def mock_client():
    """mock DataGenFlowClient that returns realistic data"""
    client = MagicMock()
    client.health.return_value = {"status": "healthy"}
    client.extension_status.return_value = {
        "blocks": {
            "total": 8,
            "builtin_blocks": 6,
            "custom_blocks": 1,
            "user_blocks": 1,
            "available": 7,
            "unavailable": 1,
        },
        "templates": {
            "total": 3,
            "builtin_templates": 2,
            "user_templates": 1,
        },
    }
    client.list_blocks.return_value = [
        {
            "type": "TextGenerator",
            "name": "Text Generator",
            "category": "generation",
            "source": "builtin",
            "available": True,
            "error": None,
        },
        {
            "type": "BrokenBlock",
            "name": "Broken Block",
            "category": "custom",
            "source": "user",
            "available": False,
            "error": "missing dependency: torch",
        },
    ]
    client.list_templates.return_value = [
        {
            "id": "qa_generation",
            "name": "Q&A Generation",
            "description": "Generate Q&A pairs",
            "source": "builtin",
        },
    ]
    client.validate_block.return_value = {"valid": True, "block": "TextGenerator"}
    client.install_block_deps.return_value = {"status": "ok", "installed": ["torch>=2.0"]}
    return client


@pytest.fixture
def cli_app(mock_client):
    """import the app with mocked client"""
    from lib.cli.main import app, get_client

    # patch get_client to return our mock
    with patch("lib.cli.main.get_client", return_value=mock_client):
        yield app


class TestStatusCommand:

    def test_status_shows_server_info(self, cli_app, mock_client):
        result = runner.invoke(cli_app, ["status"])
        assert result.exit_code == 0
        assert "7 available" in result.output
        assert "1 unavailable" in result.output

    def test_status_connection_error(self, cli_app, mock_client):
        mock_client.health.side_effect = Exception("Connection refused")
        result = runner.invoke(cli_app, ["status"])
        assert result.exit_code == 1
        assert "Cannot connect" in result.output


class TestBlocksCommands:

    def test_blocks_list(self, cli_app, mock_client):
        result = runner.invoke(cli_app, ["blocks", "list"])
        assert result.exit_code == 0
        assert "TextGenerator" in result.output
        assert "BrokenBlock" in result.output
        assert "builtin" in result.output
        assert "user" in result.output

    def test_blocks_validate_valid_file(self, cli_app, tmp_path):
        block_file = tmp_path / "my_block.py"
        block_file.write_text(
            'from lib.blocks.base import BaseBlock\n'
            'class MyBlock(BaseBlock):\n'
            '    pass\n'
        )
        result = runner.invoke(cli_app, ["blocks", "validate", str(block_file)])
        assert result.exit_code == 0
        assert "valid" in result.output
        assert "MyBlock" in result.output

    def test_blocks_validate_no_block_class(self, cli_app, tmp_path):
        block_file = tmp_path / "not_a_block.py"
        block_file.write_text("class Foo:\n    pass\n")
        result = runner.invoke(cli_app, ["blocks", "validate", str(block_file)])
        assert result.exit_code == 1
        assert "No block classes" in result.output

    def test_blocks_validate_syntax_error(self, cli_app, tmp_path):
        block_file = tmp_path / "bad.py"
        block_file.write_text("def broken(\n")
        result = runner.invoke(cli_app, ["blocks", "validate", str(block_file)])
        assert result.exit_code == 1
        assert "Syntax error" in result.output

    def test_blocks_validate_missing_file(self, cli_app):
        result = runner.invoke(cli_app, ["blocks", "validate", "/nonexistent.py"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_blocks_scaffold(self, cli_app, tmp_path):
        result = runner.invoke(
            cli_app, ["blocks", "scaffold", "SentimentAnalyzer", "-o", str(tmp_path)]
        )
        assert result.exit_code == 0
        output_file = tmp_path / "sentiment_analyzer.py"
        assert output_file.exists()
        content = output_file.read_text()
        assert "class SentimentAnalyzer" in content
        assert "BaseBlock" in content


class TestTemplatesCommands:

    def test_templates_list(self, cli_app, mock_client):
        result = runner.invoke(cli_app, ["templates", "list"])
        assert result.exit_code == 0
        assert "qa_generation" in result.output
        assert "Q&A Generation" in result.output

    def test_templates_validate_valid(self, cli_app, tmp_path):
        template_file = tmp_path / "my_template.yaml"
        template_file.write_text(
            'name: "Test Template"\n'
            'description: "A test"\n'
            'blocks:\n'
            '  - type: TextGenerator\n'
            '    config:\n'
            '      model: gpt-4o-mini\n'
        )
        result = runner.invoke(cli_app, ["templates", "validate", str(template_file)])
        assert result.exit_code == 0
        assert "valid" in result.output

    def test_templates_validate_missing_name(self, cli_app, tmp_path):
        template_file = tmp_path / "bad.yaml"
        template_file.write_text("blocks:\n  - type: Foo\n")
        result = runner.invoke(cli_app, ["templates", "validate", str(template_file)])
        assert result.exit_code == 1
        assert "name" in result.output

    def test_templates_validate_missing_blocks(self, cli_app, tmp_path):
        template_file = tmp_path / "bad2.yaml"
        template_file.write_text('name: "Test"\n')
        result = runner.invoke(cli_app, ["templates", "validate", str(template_file)])
        assert result.exit_code == 1
        assert "blocks" in result.output

    def test_templates_scaffold(self, cli_app, tmp_path):
        result = runner.invoke(
            cli_app, ["templates", "scaffold", "My Custom Pipeline", "-o", str(tmp_path)]
        )
        assert result.exit_code == 0
        output_file = tmp_path / "my_custom_pipeline.yaml"
        assert output_file.exists()
        content = output_file.read_text()
        assert "My Custom Pipeline" in content
        assert "blocks:" in content


class TestConfigureCommand:

    def test_configure_show(self, cli_app):
        result = runner.invoke(cli_app, ["configure", "--show"])
        assert result.exit_code == 0
        assert "Endpoint" in result.output

    def test_configure_set_endpoint(self, cli_app, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli_app, ["configure", "-e", "http://myserver:9000"])
        assert result.exit_code == 0
        env_content = (tmp_path / ".env").read_text()
        assert "DATAGENFLOW_ENDPOINT=http://myserver:9000" in env_content


class TestImageCommands:

    def test_image_scaffold(self, cli_app, tmp_path):
        output = tmp_path / "Dockerfile.custom"
        result = runner.invoke(cli_app, ["image", "scaffold", "-o", str(output)])
        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text()
        assert "datagenflow" in content.lower()

    def test_image_scaffold_with_blocks(self, cli_app, tmp_path):
        blocks_dir = tmp_path / "blocks"
        blocks_dir.mkdir()
        (blocks_dir / "my_block.py").write_text(
            'class MyBlock:\n'
            '    dependencies = ["torch>=2.0", "transformers"]\n'
        )
        output = tmp_path / "Dockerfile.custom"
        result = runner.invoke(
            cli_app, ["image", "scaffold", "-b", str(blocks_dir), "-o", str(output)]
        )
        assert result.exit_code == 0
        content = output.read_text()
        assert "torch>=2.0" in content
        assert "transformers" in content
