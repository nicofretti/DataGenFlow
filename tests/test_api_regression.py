"""
API regression tests — lock current behavior before extensibility changes.
"""


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_blocks_endpoint_returns_list(client):
    response = client.get("/api/blocks")
    assert response.status_code == 200
    blocks = response.json()
    assert isinstance(blocks, list)
    assert len(blocks) > 0


def test_blocks_endpoint_schema_shape(client):
    """each block must have type, name, description, category, inputs, outputs, config_schema"""
    response = client.get("/api/blocks")
    blocks = response.json()

    required_keys = {"type", "name", "description", "category", "inputs", "outputs", "config_schema"}
    for block in blocks:
        missing = required_keys - set(block.keys())
        assert not missing, f"Block {block.get('type', '?')} missing keys: {missing}"


def test_blocks_endpoint_includes_core_blocks(client):
    response = client.get("/api/blocks")
    block_types = [b["type"] for b in response.json()]

    assert "TextGenerator" in block_types
    assert "StructuredGenerator" in block_types
    assert "ValidatorBlock" in block_types
    assert "JSONValidatorBlock" in block_types
    assert "FieldMapper" in block_types


def test_templates_endpoint_returns_list(client):
    response = client.get("/api/templates")
    assert response.status_code == 200
    templates = response.json()
    assert isinstance(templates, list)
    assert len(templates) > 0


def test_templates_endpoint_schema_shape(client):
    """each template must have id, name, description"""
    response = client.get("/api/templates")
    templates = response.json()

    for template in templates:
        assert "id" in template, f"Template missing 'id': {template}"
        assert "name" in template, f"Template missing 'name': {template}"
        assert "description" in template, f"Template missing 'description': {template}"


def test_templates_endpoint_includes_core_templates(client):
    response = client.get("/api/templates")
    template_ids = [t["id"] for t in response.json()]

    assert "json_generation" in template_ids
    assert "text_classification" in template_ids
    assert "qa_generation" in template_ids
    assert "ragas_evaluation" in template_ids


def test_pipelines_endpoint_returns_list(client):
    response = client.get("/api/pipelines")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_pipeline_from_template(client):
    response = client.post("/api/pipelines/from_template/json_generation")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["name"] == "JSON Generation"
    assert data["template_id"] == "json_generation"


def test_create_pipeline_from_invalid_template(client):
    response = client.post("/api/pipelines/from_template/nonexistent")
    assert response.status_code == 404
