import pytest
from lib.blocks.research.adversarial_perturbation import AdversarialPerturbationBlock

@pytest.mark.asyncio
async def test_adversarial_creates_edge_cases():
    block = AdversarialPerturbationBlock(perturbation_type="realistic_noise", intensity=0.5)
    data = {"conversation": "User: Hello. Agent: Hi there!"}
    result = await block.execute(data)

    assert "perturbed_conversation" in result
    assert "difficulty_score" in result
    assert "perturbations_applied" in result
    assert len(result["perturbations_applied"]) > 0

@pytest.mark.asyncio
async def test_adversarial_records_paper():
    block = AdversarialPerturbationBlock()
    data = {"conversation": "test"}
    result = await block.execute(data)

    assert "Belinkov" in result["paper"]
