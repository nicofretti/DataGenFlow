"""HTTP client for DataGenFlow API."""

from typing import Any

import httpx


class DataGenFlowClient:
    """thin wrapper around the DataGenFlow REST API"""

    def __init__(self, endpoint: str, timeout: float = 30.0):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.endpoint}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def extension_status(self) -> dict[str, Any]:
        return self._request("GET", "/api/extensions/status")

    def list_blocks(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/extensions/blocks")

    def list_templates(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/extensions/templates")

    def reload_extensions(self) -> dict[str, Any]:
        return self._request("POST", "/api/extensions/reload")

    def validate_block(self, name: str) -> dict[str, Any]:
        return self._request("POST", f"/api/extensions/blocks/{name}/validate")

    def install_block_deps(self, name: str) -> dict[str, Any]:
        return self._request("POST", f"/api/extensions/blocks/{name}/install-deps")
