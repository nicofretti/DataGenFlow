"""
Dependency manager for block dependencies.

Parses, checks, and installs pip dependencies declared in block classes.
"""

import importlib.metadata
import logging
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lib.blocks.base import BaseBlock

from lib.entities.extensions import DependencyInfo

logger = logging.getLogger(__name__)


class DependencyError(Exception):
    pass


def _parse_package_name(requirement: str) -> str:
    """extract package name from a requirement string like 'torch>=2.0.0'"""
    for sep in (">=", "<=", "==", ">", "<", "[", "!=", "~="):
        requirement = requirement.split(sep)[0]
    return requirement.strip()


class DependencyManager:

    def get_block_dependencies(self, block_class: type["BaseBlock"]) -> list[str]:
        return getattr(block_class, "dependencies", [])

    def check_missing(self, requirements: list[str]) -> list[str]:
        missing = []
        for req in requirements:
            name = _parse_package_name(req)
            try:
                importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                missing.append(req)
        return missing

    def get_dependency_info(self, requirements: list[str]) -> list[DependencyInfo]:
        result = []
        for req in requirements:
            name = _parse_package_name(req)
            try:
                version = importlib.metadata.version(name)
                result.append(DependencyInfo(
                    requirement=req, name=name,
                    installed_version=version, status="ok",
                ))
            except importlib.metadata.PackageNotFoundError:
                result.append(DependencyInfo(
                    requirement=req, name=name,
                    status="not_installed",
                ))
        return result

    def install(self, requirements: list[str], timeout: int = 300) -> list[str]:
        """install requirements using uv. returns list of installed packages."""
        if not requirements:
            return []

        cmd = ["uv", "pip", "install", "--quiet"] + requirements
        logger.info(f"installing dependencies: {requirements}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                raise DependencyError(f"uv pip install failed: {result.stderr}")
            logger.info(f"successfully installed: {requirements}")
            return requirements
        except subprocess.TimeoutExpired:
            raise DependencyError(f"installation timed out after {timeout}s")
        except FileNotFoundError:
            raise DependencyError("uv not found")


dependency_manager = DependencyManager()
