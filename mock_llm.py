"""
mock llm server for testing without real llm
run: python3 mock_llm.py
then set LLM_ENDPOINT=http://localhost:11434/api/generate in .env
"""

import json

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class GenerateRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


@app.post("/api/generate")
async def generate(request: GenerateRequest) -> dict[str, str]:
    # extract user question from prompt
    prompt_parts = request.prompt.split("User:")
    if len(prompt_parts) > 1:
        user_part = prompt_parts[1].split("Assistant:")[0].strip()
    else:
        user_part = "question"

    # generate mock response based on prompt
    response = f"this is a mock response to: {user_part}. temperature={request.temperature}"

    return {"response": response}


if __name__ == "__main__":
    import uvicorn

    print("starting mock llm server on http://localhost:11434")
    print("set LLM_ENDPOINT=http://localhost:11434/api/generate in .env")
    uvicorn.run(app, host="0.0.0.0", port=11434)
