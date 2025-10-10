import asyncio
import json
from pathlib import Path

from loguru import logger
from tqdm import tqdm

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
        logger.info(f"parsed {len(seeds)} seed inputs")

        if config:
            self.generator = Generator(config)

        # calculate total samples
        total_samples = sum(
            seed.metadata.get("num_samples", 1)
            if isinstance(seed.metadata.get("num_samples"), int)
            else 1
            for seed in seeds
        )

        logger.info(f"generating {total_samples} samples...")

        total = 0
        success = 0
        failed = 0

        with tqdm(total=total_samples, desc="generating", unit="sample") as pbar:
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
                            logger.debug(f"generation failed: {result}")
                        else:
                            success += 1
                        pbar.update(1)

                except Exception as e:
                    failed += 1
                    total += 1
                    logger.debug(f"seed processing failed: {e}")
                    pbar.update(1)

        return {"total": total, "success": success, "failed": failed}

    async def _generate_single(self, seed: SeedInput) -> int:
        system = self.generator.render_template(seed.system, seed.metadata)
        user = self.generator.render_template(seed.user, seed.metadata)

        assistant = await self.generator.generate(system, user)

        record = Record(system=system, user=user, assistant=assistant, metadata=seed.metadata)

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
