import httpx

from config import settings
from models import GenerationConfig


class Generator:
    def __init__(self, config: GenerationConfig | None = None) -> None:
        self.config = config or GenerationConfig()
        self.endpoint = self.config.endpoint or settings.LLM_ENDPOINT
        self.model = self.config.model or settings.LLM_MODEL
        self.api_key = settings.LLM_API_KEY

    def render_template(self, template: str, metadata: dict[str, str | int | float]) -> str:
        try:
            return template.format(**metadata)
        except KeyError as e:
            raise ValueError(f"missing metadata key: {e}")

    async def generate(self, system: str, user: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # openai-compatible format (works with ollama, openai, anthropic)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            payload["max_tokens"] = self.config.max_tokens

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(self.endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            # openai format response
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"unexpected response format: {data}")
