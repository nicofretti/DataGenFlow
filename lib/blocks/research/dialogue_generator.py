from lib.blocks.base import BaseBlock
from lib.generator import Generator
from models import GenerationConfig


class DialogueGeneratorBlock(BaseBlock):
    name = "Dialogue Generator"
    description = "Generate multi-turn conversations using persona-driven algorithm (Li et al., 2016)"
    inputs = []  # can work with personas or just topic
    outputs = ["dialogue", "turn_count", "algorithm"]
    algorithm = "persona_driven_dialogue"
    paper = "Li et al., 2016 - A Persona-Based Neural Conversation Model"

    def __init__(self, turns: int = 5, algo: str = "persona_driven", max_tokens: int = 2000):
        self.turns = turns
        self.algo = algo
        self.max_tokens = max_tokens

    async def execute(self, data: dict) -> dict:
        """generate dialogue using persona-driven algorithm"""
        personas = data.get("personas", None)
        topic = data.get("topic", "general conversation")

        # if no personas, generate them
        if not personas:
            personas = self._generate_default_personas(topic)

        dialogue = await self._generate_dialogue(personas, topic)

        return {
            "dialogue": dialogue,
            "turn_count": self.turns,
            "algorithm": "persona_driven_dialogue"
        }

    def _generate_default_personas(self, topic: str) -> list:
        """fallback: generate personas if not provided"""
        return [
            {"name": "User", "personality": "curious"},
            {"name": "Agent", "personality": "helpful"}
        ]

    async def _generate_dialogue(self, personas: list, topic: str) -> str:
        """generate multi-turn dialogue"""
        system_prompt = self._build_system_prompt(personas, topic)
        user_prompt = f"Generate a {self.turns}-turn conversation about {topic}"

        config = GenerationConfig(
            temperature=0.8,
            max_tokens=self.max_tokens
        )
        generator = Generator(config=config)

        dialogue = await generator.generate(
            system=system_prompt,
            user=user_prompt
        )

        return dialogue

    def _build_system_prompt(self, personas: list, topic: str) -> str:
        persona_desc = "\n".join([
            f"- {p.get('name', 'Speaker')}: {p.get('personality', 'neutral')}"
            for p in personas
        ])

        return f"""You are generating a realistic conversation for training data.

Topic: {topic}

Personas:
{persona_desc}

Generate natural, diverse dialogue that:
- Shows distinct personalities for each speaker
- Covers the topic naturally
- Includes realistic responses and follow-ups
- Uses Format: Speaker: Message"""
