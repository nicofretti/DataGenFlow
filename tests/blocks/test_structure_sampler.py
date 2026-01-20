import pytest

from lib.blocks.builtin.structure_sampler import StructureSampler
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import ValidationError


def make_context(state: dict) -> BlockExecutionContext:
    """helper to create test context"""
    return BlockExecutionContext(
        trace_id="test-trace",
        pipeline_id=1,
        accumulated_state=state,
    )


class TestStructureSamplerInit:
    def test_init_basic(self):
        block = StructureSampler(
            target_count=10,
            categorical_fields=["plan"],
        )
        assert block.target_count_template == "10"
        assert block.categorical_fields_template == '["plan"]'
        assert block.numeric_fields_template == ""
        assert block.dependencies_template == ""

    def test_init_with_all_params(self):
        block = StructureSampler(
            target_count=5,
            categorical_fields=["plan", "role"],
            numeric_fields=["storage"],
            dependencies={"role": ["plan"]},
            seed=42,
        )
        assert block.target_count_template == "5"
        assert block.categorical_fields_template == '["plan", "role"]'
        assert block.numeric_fields_template == '["storage"]'
        assert block.dependencies_template == '{"role": ["plan"]}'
        assert block.seed == 42


class TestStructureSamplerDistributions:
    @pytest.mark.asyncio
    async def test_categorical_distribution(self):
        block = StructureSampler(
            target_count=10,
            categorical_fields=["plan"],
            seed=42,
        )
        # set attributes that would normally be set in execute()
        block.categorical_fields = ["plan"]

        samples = [
            {"plan": "Free"},
            {"plan": "Free"},
            {"plan": "Pro"},
        ]

        profile = block._compute_categorical_distributions(samples)

        # check probabilities sum to 1
        assert abs(sum(profile["plan"].values()) - 1.0) < 0.001
        # check Free is ~67% (2/3) and Pro is ~33% (1/3)
        assert abs(profile["plan"]["Free"] - 0.667) < 0.01
        assert abs(profile["plan"]["Pro"] - 0.333) < 0.01

    @pytest.mark.asyncio
    async def test_conditional_probabilities(self):
        block = StructureSampler(
            target_count=10,
            categorical_fields=["plan", "role"],
            dependencies={"role": ["plan"]},
            seed=42,
        )
        # set attributes that would normally be set in execute()
        block.categorical_fields = ["plan", "role"]
        block.dependencies = {"role": ["plan"]}

        samples = [
            {"plan": "Free", "role": "Viewer"},
            {"plan": "Free", "role": "Viewer"},
            {"plan": "Pro", "role": "Editor"},
            {"plan": "Pro", "role": "Admin"},
        ]

        profile = block._compute_conditional_probabilities(samples)

        # check conditional probability for role given plan
        assert "role|plan=Free" in profile
        assert profile["role|plan=Free"]["Viewer"] == 1.0

        assert "role|plan=Pro" in profile
        assert profile["role|plan=Pro"]["Editor"] == 0.5
        assert profile["role|plan=Pro"]["Admin"] == 0.5

    @pytest.mark.asyncio
    async def test_numeric_statistics(self):
        block = StructureSampler(
            target_count=10,
            numeric_fields=["storage"],
            categorical_fields=[],
            seed=42,
        )
        # set attributes that would normally be set in execute()
        block.numeric_fields = ["storage"]

        samples = [
            {"storage": 1},
            {"storage": 2},
            {"storage": 3},
        ]

        stats = block._compute_numeric_statistics(samples)

        assert stats["storage"]["min"] == 1
        assert stats["storage"]["max"] == 3
        assert stats["storage"]["mean"] == 2.0


class TestStructureSamplerGeneration:
    @pytest.mark.asyncio
    async def test_generate_skeletons_basic(self):
        block = StructureSampler(
            target_count=5,
            categorical_fields=["plan"],
            seed=42,
        )

        context = make_context(
            {
                "samples": [
                    {"plan": "Free"},
                    {"plan": "Free"},
                    {"plan": "Pro"},
                ]
            }
        )

        result = await block.execute(context)

        # check we got dict with skeletons key
        assert "skeletons" in result
        skeletons = result["skeletons"]
        # check we got 5 skeletons
        assert len(skeletons) == 5
        # check all have plan field
        for skeleton in skeletons:
            assert "plan" in skeleton
            assert skeleton["plan"] in ["Free", "Pro"]

    @pytest.mark.asyncio
    async def test_generate_skeletons_with_dependencies(self):
        block = StructureSampler(
            target_count=10,
            categorical_fields=["plan", "role"],
            dependencies={"role": ["plan"]},
            seed=42,
        )

        context = make_context(
            {
                "samples": [
                    {"plan": "Free", "role": "Viewer"},
                    {"plan": "Free", "role": "Viewer"},
                    {"plan": "Pro", "role": "Editor"},
                ]
            }
        )

        result = await block.execute(context)

        # check all Free plans have Viewer role (100% in samples)
        skeletons = result["skeletons"]
        for skeleton in skeletons:
            if skeleton["plan"] == "Free":
                assert skeleton["role"] == "Viewer"

    @pytest.mark.asyncio
    async def test_generate_skeletons_with_hints(self):
        block = StructureSampler(
            target_count=3,
            categorical_fields=["plan"],
            numeric_fields=["storage"],
            seed=42,
        )

        context = make_context(
            {
                "samples": [
                    {"plan": "Free", "storage": 1},
                    {"plan": "Free", "storage": 2},
                    {"plan": "Pro", "storage": 50},
                ]
            }
        )

        result = await block.execute(context)

        # check hints are included
        skeletons = result["skeletons"]
        for skeleton in skeletons:
            assert "_hints" in skeleton
            assert "storage_range" in skeleton["_hints"]
            assert "exemplars" in skeleton["_hints"]
            # check storage range is [1, 50]
            assert skeleton["_hints"]["storage_range"] == [1, 50]


class TestStructureSamplerEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_samples_raises_error(self):
        block = StructureSampler(
            target_count=5,
            categorical_fields=["plan"],
        )

        context = make_context({"samples": []})

        with pytest.raises(ValidationError, match="No samples provided"):
            await block.execute(context)

    @pytest.mark.asyncio
    async def test_missing_samples_raises_error(self):
        block = StructureSampler(
            target_count=5,
            categorical_fields=["plan"],
        )

        context = make_context({})

        with pytest.raises(ValidationError, match="No samples provided"):
            await block.execute(context)

    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self):
        block = StructureSampler(
            target_count=5,
            categorical_fields=["a", "b"],
            dependencies={"a": ["b"], "b": ["a"]},
        )

        context = make_context({"samples": [{"a": "1", "b": "2"}]})

        with pytest.raises(ValidationError, match="Circular dependency"):
            await block.execute(context)


class TestStructureSamplerSchema:
    def test_schema_structure(self):
        schema = StructureSampler.get_schema()
        assert schema["name"] == "Structure Sampler"
        assert schema["category"] == "seeders"
        assert schema["outputs"] == ["skeletons", "_seed_samples"]

    def test_schema_has_required_configs(self):
        schema = StructureSampler.get_schema()
        config_props = schema["config_schema"]["properties"]
        assert "target_count" in config_props
        assert "categorical_fields" in config_props
        assert "numeric_fields" in config_props
        assert "dependencies" in config_props
        assert "seed" in config_props
