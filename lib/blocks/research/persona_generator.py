import json
import re
from typing import Any

from lib.blocks.base import BaseBlock
from lib.generator import Generator
from models import GenerationConfig


class PersonaGeneratorBlock(BaseBlock):
    name = "Persona Generator"
    description = "Generate conversational personas using algorithm from Li et al., 2016"
    inputs = []  # can work without seed
    outputs = ["personas", "persona_metadata"]
    algorithm = "persona_driven_generation"
    paper = "Li et al., 2016 - A Persona-Based Neural Conversation Model"

    def __init__(
        self,
        num_personas: int = 2,
        personality_traits: list[str] | None = None,
        generate_from_metadata: bool = True,
    ) -> None:
        self.num_personas = num_personas
        self.personality_traits = personality_traits or ["helpful", "knowledgeable"]
        self.generate_from_metadata = generate_from_metadata

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """generate personas, optionally conditioned on metadata context"""
        topic = data.get("topic", "general")
        context = data.get("context", "")

        prompt = self._build_generation_prompt(topic, context)

        generator = Generator(
            GenerationConfig(temperature=0.8, max_tokens=300)
        )

        personas = []
        for i in range(self.num_personas):
            persona_json = await generator.generate(
                system="You are generating persona data for training conversational AI systems.",
                user=prompt
            )
            persona = self._parse_persona(persona_json, topic)
            personas.append(persona)

        return {
            "personas": personas,
            "persona_metadata": {
                "count": len(personas),
                "traits": self.personality_traits,
                "topic": topic
            }
        }

    def _build_generation_prompt(self, topic: str, context: str) -> str:
        traits_str = ", ".join(self.personality_traits)
        return f"""Generate a conversational persona for {topic}.

Personality traits: {traits_str}
Context: {context or 'general conversation'}

Return as JSON with: name, age, occupation, personality (brief description), background (2-3 sentences), communication_style"""

    def _parse_persona(self, response: str, topic: str) -> dict[str, Any]:
        try:
            # extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                persona = json.loads(json_match.group())
                # add context field if topic was provided
                if topic and topic != "general":
                    persona["context"] = topic
                return persona
        except Exception:
            pass

        # fallback structured response
        return {
            "name": f"User_{self.num_personas}",
            "personality": "friendly",
            "background": response[:100],
            "context": topic if topic != "general" else ""
        }
