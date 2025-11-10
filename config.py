import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    LLM_ENDPOINT: str = os.getenv("LLM_ENDPOINT", "http://localhost:11434/v1/chat/completions")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3")

    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/qa_records.db")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    @classmethod
    def ensure_data_dir(cls) -> None:
        db_path = Path(cls.DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()

# Configure logging based on DEBUG mode
if settings.DEBUG:
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    # disable verbose logs
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
else:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    # disable verbose logs
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
