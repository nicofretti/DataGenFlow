from typing import Any

from fastapi import APIRouter, HTTPException

from lib.blocks.registry import registry
from lib.dependency_manager import DependencyError, dependency_manager
from lib.entities.extensions import (
    BlockInfo,
    BlocksStatus,
    DependencyInfo,
    ExtensionsStatus,
    TemplateInfo,
    TemplatesStatus,
)
from lib.templates import template_registry

router = APIRouter(prefix="/extensions", tags=["extensions"])


@router.get("/status")
async def extensions_status() -> ExtensionsStatus:
    blocks = registry.list_blocks()
    templates = template_registry.list_templates()

    builtin_count = custom_count = user_count = available_count = 0
    for b in blocks:
        if b.source == "builtin":
            builtin_count += 1
        elif b.source == "custom":
            custom_count += 1
        elif b.source == "user":
            user_count += 1
        if b.available:
            available_count += 1

    return ExtensionsStatus(
        blocks=BlocksStatus(
            total=len(blocks),
            builtin_blocks=builtin_count,
            custom_blocks=custom_count,
            user_blocks=user_count,
            available=available_count,
            unavailable=len(blocks) - available_count,
        ),
        templates=TemplatesStatus(
            total=len(templates),
            builtin_templates=sum(1 for t in templates if t.source == "builtin"),
            user_templates=sum(1 for t in templates if t.source == "user"),
        ),
    )


@router.get("/blocks")
async def extensions_blocks() -> list[BlockInfo]:
    return registry.list_blocks()


@router.get("/templates")
async def extensions_templates() -> list[TemplateInfo]:
    return template_registry.list_templates()


@router.post("/reload")
async def reload_extensions() -> dict[str, str]:
    """manually trigger extension reload"""
    registry.reload()
    template_registry.reload()
    return {"status": "ok", "message": "Extensions reloaded"}


@router.post("/blocks/{name}/validate")
async def validate_block(name: str) -> dict[str, Any]:
    """validate a block's availability and dependencies"""
    block_class = registry.get_block_class(name)
    if block_class is None:
        entry = registry.get_entry(name)
        if entry and not entry.available:
            return {"valid": False, "block": name, "error": entry.error}
        raise HTTPException(status_code=404, detail=f"Block '{name}' not found")

    missing = dependency_manager.check_missing(block_class.dependencies)
    if missing:
        return {"valid": False, "block": name, "missing_dependencies": missing}
    return {"valid": True, "block": name}


@router.get("/blocks/{name}/dependencies")
async def block_dependencies(name: str) -> list[DependencyInfo]:
    """get dependency info for a block"""
    entry = registry.get_entry(name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Block '{name}' not found")
    if entry.block_class is None:
        raise HTTPException(
            status_code=422, detail=f"Block '{name}' failed to import — dependencies unknown"
        )
    return dependency_manager.get_dependency_info(entry.block_class.dependencies)


@router.post("/blocks/{name}/install-deps")
async def install_block_deps(name: str) -> dict[str, Any]:
    """install missing dependencies for a block (works for unavailable blocks too)"""
    entry = registry.get_entry(name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Block '{name}' not found")
    if entry.block_class is None:
        raise HTTPException(
            status_code=422, detail=f"Block '{name}' failed to import — dependencies unknown"
        )

    deps = entry.block_class.dependencies
    missing = dependency_manager.check_missing(deps)
    if not missing:
        return {"status": "ok", "installed": [], "message": "All dependencies already installed"}

    try:
        installed = await dependency_manager.install(missing)
        registry.reload()
        return {"status": "ok", "installed": installed}
    except DependencyError as e:
        raise HTTPException(status_code=500, detail=str(e))
