import asyncio

from lib.storage import Storage
from lib.workflow import Pipeline as WorkflowPipeline

PIPELINE_ID = 26
SEED_DATA = {
    "repetitions": 1,
    "metadata": {
        "content": (
            "Electric cars reduce emissions but require extensive charging "
            "infrastructure and have higher upfront costs compared to traditional vehicles."
        )
    },
}


async def main() -> None:
    storage = Storage()
    await storage.init_db()

    pipeline_data = await storage.get_pipeline(PIPELINE_ID)
    if not pipeline_data:
        print(f"Pipeline {PIPELINE_ID} not found")
        return

    workflow = WorkflowPipeline(
        name=pipeline_data.name, blocks=pipeline_data.definition["blocks"]
    )

    result, _, trace_id = await workflow.execute(SEED_DATA["metadata"])  # type: ignore[arg-type]
    print(f"trace_id: {trace_id}")
    print(f"result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
