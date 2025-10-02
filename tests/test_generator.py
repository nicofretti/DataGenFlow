import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.generator import Generator


async def test_generation():
    gen = Generator()
    print(f"endpoint: {gen.endpoint}")
    print(f"model: {gen.model}")

    try:
        response = await gen.generate("You are a teacher", "Explain gravity")
        print(f"success! response: {response[:100]}...")
    except Exception as e:
        print(f"error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_generation())
