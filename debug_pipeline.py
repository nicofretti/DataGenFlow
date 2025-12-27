import asyncio
import logging
import os

import litellm

# disable ragas analytics (must be before any ragas imports)
os.environ["RAGAS_DO_NOT_TRACK"] = "true"

# suppress asyncio SSL errors at shutdown (harmless cleanup noise from pending HTTP connections)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

from lib.blocks.commons import UsageTracker
from lib.storage import Storage
from lib.workflow import Pipeline as WorkflowPipeline

# setup logging
logging.basicConfig(level=logging.DEBUG)

# register usage tracker callback
litellm.success_callback = [UsageTracker.callback]
# also try callbacks list
litellm.callbacks = [UsageTracker.callback]

PIPELINE_ID = 84
SEED_DATA = {
    "repetitions": 1,
    "metadata": {
        "content": "Python is a high-level, interpreted programming language known for its clear syntax and readability. It was created by Guido van Rossum and first released in 1991. Python supports multiple programming paradigms including procedural, object-oriented, and functional programming."
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

    execution_result = await workflow.execute(SEED_DATA["metadata"])
    print(f"trace_id: {execution_result.trace_id}")
    print(f"result: {execution_result.result}")
    print(f"usage: {execution_result.usage}")

    # shutdown ragas analytics batcher before event loop closes
    try:
        from ragas._analytics import _analytics_batcher

        _analytics_batcher.shutdown()
    except ImportError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
