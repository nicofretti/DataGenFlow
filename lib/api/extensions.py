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

    return ExtensionsStatus(
        blocks=BlocksStatus(
            total=len(blocks),
            builtin_blocks=sum(1 for b in blocks if b.source == "builtin"),
            custom_blocks=sum(1 for b in blocks if b.source == "custom"),
            user_blocks=sum(1 for b in blocks if b.source == "user"),
            available=sum(1 for b in blocks if b.available),
            unavailable=sum(1 for b in blocks if not b.available),
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
    return {"status": "ok", "message": "Extensions reloaded"}


@router.post("/blocks/{name}/validate")
async def validate_block(name: str) -> dict:
    """validate a block's availability and dependencies"""
    block_class = registry.get_block_class(name)
    if block_class is None:
        # check if it's registered but unavailable
        unavailable = next((b for b in registry.list_blocks() if b.type == name), None)
        if unavailable and not unavailable.available:
            return {"valid": False, "block": name, "error": unavailable.error}
        raise HTTPException(status_code=404, detail=f"Block '{name}' not found")

    missing = dependency_manager.check_missing(block_class.dependencies)
    if missing:
        return {"valid": False, "block": name, "missing_dependencies": missing}
    return {"valid": True, "block": name}


@router.get("/blocks/{name}/dependencies")
async def block_dependencies(name: str) -> list[DependencyInfo]:
    """get dependency info for a block"""
    block_class = registry.get_block_class(name)
    if block_class is None:
        raise HTTPException(status_code=404, detail=f"Block '{name}' not found")
    return dependency_manager.get_dependency_info(block_class.dependencies)


@router.post("/blocks/{name}/install-deps")
async def install_block_deps(name: str) -> dict:
    """install missing dependencies for a block"""
    block_class = registry.get_block_class(name)
    if block_class is None:
        raise HTTPException(status_code=404, detail=f"Block '{name}' not found")

    missing = dependency_manager.check_missing(block_class.dependencies)
    if not missing:
        return {"status": "ok", "message": "All dependencies already installed"}

    try:
        installed = dependency_manager.install(missing)
        return {"status": "ok", "installed": installed}
    except DependencyError as e:
        raise HTTPException(status_code=500, detail=str(e))
