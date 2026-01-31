"""DataGenFlow CLI - Manage blocks and templates."""

import ast
import os
import re
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from lib.cli.client import DataGenFlowClient

app = typer.Typer(
    name="dgf",
    help="DataGenFlow CLI - Manage blocks and templates",
    no_args_is_help=True,
)
console = Console()

blocks_app = typer.Typer(help="Manage custom blocks")
templates_app = typer.Typer(help="Manage pipeline templates")
image_app = typer.Typer(help="Build custom Docker images")

app.add_typer(blocks_app, name="blocks")
app.add_typer(templates_app, name="templates")
app.add_typer(image_app, name="image")


def get_endpoint() -> str:
    """get API endpoint from env or .env file"""
    endpoint = os.getenv("DATAGENFLOW_ENDPOINT")
    if endpoint:
        return endpoint

    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATAGENFLOW_ENDPOINT="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    return "http://localhost:8000"


def get_client() -> DataGenFlowClient:
    return DataGenFlowClient(get_endpoint())


# ============ Status ============


@app.command()
def status() -> None:
    """Show DataGenFlow server status and extension info."""
    client = get_client()

    try:
        client.health()
        ext = client.extension_status()

        blocks = ext["blocks"]
        templates = ext["templates"]

        console.print(f"[green]✓[/green] Server: {get_endpoint()}")
        console.print(
            f"  Blocks: {blocks['available']} available, "
            f"{blocks['unavailable']} unavailable"
        )
        console.print(
            f"  Templates: {templates['total']} total "
            f"({templates['builtin_templates']} builtin, "
            f"{templates['user_templates']} user)"
        )

    except Exception as e:
        console.print(f"[red]✗[/red] Cannot connect to {get_endpoint()}: {e}")
        raise typer.Exit(1)


# ============ Blocks ============


@blocks_app.command("list")
def blocks_list() -> None:
    """List all registered blocks."""
    client = get_client()
    blocks = client.list_blocks()

    table = Table(title="Registered Blocks")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Category", style="green")
    table.add_column("Status")
    table.add_column("Source", style="dim")

    for block in blocks:
        if block.get("available", True):
            block_status = "[green]✓[/green]"
        else:
            error = block.get("error", "unavailable")
            block_status = f"[red]✗ {error[:30]}[/red]"

        table.add_row(
            block.get("name", block["type"]),
            block["type"],
            block.get("category", "general"),
            block_status,
            block.get("source", "unknown"),
        )

    console.print(table)


@blocks_app.command("validate")
def blocks_validate(
    path: Path = typer.Argument(..., help="Path to block Python file"),
) -> None:
    """Validate a block file without adding it."""
    if not path.exists():
        console.print(f"[red]✗[/red] File not found: {path}")
        raise typer.Exit(1)

    try:
        tree = ast.parse(path.read_text())
    except SyntaxError as e:
        console.print(f"[red]✗[/red] Syntax error: {e}")
        raise typer.Exit(1)

    block_names = _find_block_classes(tree)
    if not block_names:
        console.print("[red]✗[/red] No block classes found (must inherit from BaseBlock)")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] {path.name} is valid")
    console.print(f"  Blocks found: {', '.join(block_names)}")


@blocks_app.command("scaffold")
def blocks_scaffold(
    name: str = typer.Argument(..., help="Block class name (e.g., SentimentAnalyzer)"),
    output: Path = typer.Option(Path("."), "-o", "--output", help="Output directory"),
    category: str = typer.Option("general", "-c", "--category", help="Block category"),
) -> None:
    """Generate a block template file."""
    filename = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower() + ".py"
    display_name = re.sub(r"(?<!^)(?=[A-Z])", " ", name)

    output_path = output / filename
    template = f'''"""
{display_name} block for DataGenFlow.
"""
from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext


class {name}(BaseBlock):
    name = "{display_name}"
    description = "TODO: Add description"
    category = "{category}"
    inputs = ["text"]
    outputs = ["result"]

    # dependencies = ["some-package>=1.0.0"]

    def __init__(self, param: str = "default"):
        self.param = param

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        text = context.get_state("text", "")
        result = text
        return {{"result": result}}
'''

    output_path.write_text(template)
    console.print(f"[green]✓[/green] Created {output_path}")


# ============ Templates ============


@templates_app.command("list")
def templates_list() -> None:
    """List all available templates."""
    client = get_client()
    templates = client.list_templates()

    table = Table(title="Available Templates")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Description", style="green")
    table.add_column("Source", style="dim")

    for tmpl in templates:
        table.add_row(
            tmpl["id"],
            tmpl["name"],
            (tmpl.get("description", "") or "")[:50],
            tmpl.get("source", "unknown"),
        )

    console.print(table)


@templates_app.command("validate")
def templates_validate(
    path: Path = typer.Argument(..., help="Path to template YAML file"),
) -> None:
    """Validate a template file without adding it."""
    if not path.exists():
        console.print(f"[red]✗[/red] File not found: {path}")
        raise typer.Exit(1)

    import yaml

    try:
        with open(path) as f:
            data = yaml.safe_load(f)

        errors = []
        if "name" not in data:
            errors.append("Missing 'name' field")
        if "blocks" not in data:
            errors.append("Missing 'blocks' field")
        elif not isinstance(data["blocks"], list):
            errors.append("'blocks' must be a list")
        elif len(data["blocks"]) == 0:
            errors.append("'blocks' list cannot be empty")
        else:
            for i, block in enumerate(data["blocks"]):
                if "type" not in block:
                    errors.append(f"Block {i} missing 'type' field")

        if errors:
            console.print(f"[red]✗[/red] {path.name} is invalid:")
            for error in errors:
                console.print(f"  - {error}")
            raise typer.Exit(1)

        console.print(f"[green]✓[/green] {path.name} is valid")
        console.print(f"  Name: {data['name']}")
        console.print(f"  Blocks: {len(data['blocks'])}")

    except yaml.YAMLError as e:
        console.print(f"[red]✗[/red] Invalid YAML: {e}")
        raise typer.Exit(1)


@templates_app.command("scaffold")
def templates_scaffold(
    name: str = typer.Argument(..., help="Template name"),
    output: Path = typer.Option(Path("."), "-o", "--output", help="Output directory"),
) -> None:
    """Generate a template YAML file."""
    filename = name.lower().replace(" ", "_") + ".yaml"
    output_path = output / filename

    template = f'''name: "{name}"
description: "TODO: Add description"

example_seed:
  text: "Sample input text"

blocks:
  - type: TextGenerator
    config:
      model: "gpt-4o-mini"
      user_prompt: |
        Process the following text:
        {{{{ text }}}}
'''

    output_path.write_text(template)
    console.print(f"[green]✓[/green] Created {output_path}")


# ============ Image ============


@image_app.command("scaffold")
def image_scaffold(
    blocks_dir: Path = typer.Option(
        None, "--blocks-dir", "-b", help="Directory containing blocks"
    ),
    output: Path = typer.Option(
        Path("Dockerfile.custom"), "-o", "--output", help="Output path"
    ),
) -> None:
    """Generate a Dockerfile for custom image with dependencies."""
    deps: set[str] = set()

    if blocks_dir and blocks_dir.exists():
        for py_file in blocks_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                tree = ast.parse(py_file.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for item in node.body:
                            if (
                                isinstance(item, ast.Assign)
                                and any(
                                    isinstance(t, ast.Name) and t.id == "dependencies"
                                    for t in item.targets
                                )
                                and isinstance(item.value, ast.List)
                            ):
                                for elt in item.value.elts:
                                    if isinstance(elt, ast.Constant):
                                        deps.add(elt.value)
            except Exception:
                pass

    dockerfile = "# Custom DataGenFlow image with dependencies\n"
    dockerfile += "# Generated by: dgf image scaffold\n\n"
    dockerfile += "FROM datagenflow/datagenflow:latest\n\n"

    if deps:
        dockerfile += "# Install block dependencies\n"
        dockerfile += "RUN uv pip install \\\n"
        dockerfile += " \\\n".join(f"    {dep}" for dep in sorted(deps))
        dockerfile += "\n"
    else:
        dockerfile += "# No additional dependencies detected\n"

    dockerfile += "\n# User blocks and templates are mounted at runtime:\n"
    dockerfile += "#   -v ./user_blocks:/app/user_blocks\n"
    dockerfile += "#   -v ./user_templates:/app/user_templates\n"

    output.write_text(dockerfile)
    console.print(f"[green]✓[/green] Created {output}")

    if deps:
        console.print(f"  Dependencies: {len(deps)}")
        for dep in sorted(deps):
            console.print(f"    - {dep}")


@image_app.command("build")
def image_build(
    dockerfile: Path = typer.Option(Path("Dockerfile.custom"), "-f", "--dockerfile"),
    tag: str = typer.Option("my-datagenflow:latest", "-t", "--tag"),
) -> None:
    """Build a custom Docker image."""
    if not dockerfile.exists():
        console.print(f"[red]✗[/red] Dockerfile not found: {dockerfile}")
        console.print("Run 'dgf image scaffold' first")
        raise typer.Exit(1)

    cmd = ["docker", "build", "-f", str(dockerfile), "-t", tag, "."]
    console.print(f"Building image: {tag}")

    try:
        subprocess.run(cmd, check=True)
        console.print(f"\n[green]✓[/green] Successfully built {tag}")
    except subprocess.CalledProcessError:
        console.print("\n[red]✗[/red] Build failed")
        raise typer.Exit(1)


# ============ Configure ============


@app.command()
def configure(
    endpoint: str = typer.Option(None, "--endpoint", "-e", help="DataGenFlow API endpoint"),
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
) -> None:
    """Configure CLI settings."""
    env_file = Path(".env")

    if show or endpoint is None:
        console.print("Current configuration:")
        console.print(f"  Endpoint: {get_endpoint()}")
        return

    lines = []
    found = False

    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATAGENFLOW_ENDPOINT="):
                lines.append(f"DATAGENFLOW_ENDPOINT={endpoint}")
                found = True
            else:
                lines.append(line)

    if not found:
        lines.append(f"DATAGENFLOW_ENDPOINT={endpoint}")

    env_file.write_text("\n".join(lines) + "\n")
    console.print(f"[green]✓[/green] Configuration saved to {env_file}")


# ============ Helpers ============


def _find_block_classes(tree: ast.AST) -> list[str]:
    """extract class names that inherit from a *Block base class"""
    block_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = ""
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr
                if "Block" in base_name:
                    block_names.append(node.name)
                    break
    return block_names


if __name__ == "__main__":
    app()
