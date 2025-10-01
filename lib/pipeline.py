import asyncio
import json
from pathlib import Path

from lib.generator import Generator
from lib.storage import Storage
from lib.validator import Validator
from models import GenerationConfig, Record, SeedInput


class Pipeline:
    def __init__(
        self,
        storage: Storage,
        generator: Generator | None = None,
        validator: Validator | None = None,
    ) -> None:
        self.storage = storage
        self.generator = generator or Generator()
        self.validator = validator or Validator()

    async def process_seed_file(
        self, file_path: str, config: GenerationConfig | None = None
    ) -> dict[str, int]:
        seeds = self._parse_seed_file(file_path)
        if config:
            self.generator = Generator(config)

        total = 0
        success = 0
        failed = 0

        for seed in seeds:
            try:
                num_samples = seed.metadata.get("num_samples", 1)
                if not isinstance(num_samples, int):
                    num_samples = 1

                tasks = [self._generate_single(seed) for _ in range(num_samples)]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    total += 1
                    if isinstance(result, Exception):
                        failed += 1
                    else:
                        success += 1

            except Exception:
                failed += 1
                total += 1

        return {"total": total, "success": success, "failed": failed}

    async def _generate_single(self, seed: SeedInput) -> int:
        system = self.generator.render_template(seed.system, seed.metadata)
        user = self.generator.render_template(seed.user, seed.metadata)

        assistant = await self.generator.generate(system, user)

        record = Record(
            system=system, user=user, assistant=assistant, metadata=seed.metadata
        )

        if self.validator.validate(record):
            return await self.storage.save_record(record)
        else:
            raise ValueError("validation failed")

    def _parse_seed_file(self, file_path: str) -> list[SeedInput]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"seed file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = [data]

        return [SeedInput(**item) for item in data]
