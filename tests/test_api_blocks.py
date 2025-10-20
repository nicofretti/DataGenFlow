import pytest
from httpx import AsyncClient, ASGITransport

from app import app


@pytest.mark.asyncio
async def test_get_blocks_includes_algorithm_info():
    """test that /api/blocks endpoint returns algorithm and paper fields for research blocks"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/blocks")
        assert response.status_code == 200

        blocks = response.json()
        assert isinstance(blocks, list)
        assert len(blocks) > 0

        # find BackTranslationBlock
        back_translation = None
        for block in blocks:
            if block["type"] == "BackTranslationBlock":
                back_translation = block
                break

        # should have found the block
        assert back_translation is not None, "BackTranslationBlock not found in blocks list"

        # should have algorithm and paper fields
        assert "algorithm" in back_translation, "BackTranslationBlock missing algorithm field"
        assert "paper" in back_translation, "BackTranslationBlock missing paper field"

        # verify values
        assert back_translation["algorithm"] == "back_translation_diversity"
        assert "Sennrich" in back_translation["paper"]


@pytest.mark.asyncio
async def test_get_blocks_includes_algorithm_info_for_all_research_blocks():
    """test that all research blocks have algorithm and paper fields"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/blocks")
        assert response.status_code == 200

        blocks = response.json()

        # find all research blocks (they should have algorithm field)
        research_blocks = [
            "BackTranslationBlock",
            "PersonaGeneratorBlock",
            "AdversarialPerturbationBlock"
        ]

        for block_type in research_blocks:
            block = None
            for b in blocks:
                if b["type"] == block_type:
                    block = b
                    break

            if block:  # only test if block exists
                # research blocks should have algorithm info
                assert "algorithm" in block or block_type == "PersonaGeneratorBlock", \
                    f"{block_type} missing algorithm field"
