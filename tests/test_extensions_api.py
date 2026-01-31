"""
Tests for extensions API endpoints.
"""


def test_extensions_status(client):
    response = client.get("/api/extensions/status")
    assert response.status_code == 200
    data = response.json()
    assert "blocks" in data
    assert "templates" in data
    assert "builtin_blocks" in data["blocks"]
    assert "user_blocks" in data["blocks"]
    assert "builtin_templates" in data["templates"]
    assert "user_templates" in data["templates"]


def test_extensions_blocks(client):
    response = client.get("/api/extensions/blocks")
    assert response.status_code == 200
    blocks = response.json()
    assert isinstance(blocks, list)
    assert len(blocks) > 0
    # every block has source and available
    for b in blocks:
        assert "source" in b
        assert "available" in b


def test_extensions_templates(client):
    response = client.get("/api/extensions/templates")
    assert response.status_code == 200
    templates = response.json()
    assert isinstance(templates, list)
    assert len(templates) > 0
    for t in templates:
        assert "source" in t
        assert "id" in t


def test_extensions_reload(client):
    response = client.post("/api/extensions/reload")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_validate_block_available(client):
    response = client.post("/api/extensions/blocks/TextGenerator/validate")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["block"] == "TextGenerator"


def test_validate_block_not_found(client):
    response = client.post("/api/extensions/blocks/NonExistent/validate")
    assert response.status_code == 404


def test_block_dependencies_endpoint(client):
    response = client.get("/api/extensions/blocks/TextGenerator/dependencies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
