import asyncio
from lib.storage import Storage
from lib.workflow import Pipeline as WorkflowPipeline

PIPELINE_ID = 1
SEED_DATA = {"metadata": {"system": "You are helpful", "user": "Test question"}}

async def main():
    storage = Storage()
    await storage.init_db()

    pipeline_data = await storage.get_pipeline(PIPELINE_ID)
    if not pipeline_data:
        print(f"Pipeline {PIPELINE_ID} not found")
        return

    workflow = WorkflowPipeline(
        name=pipeline_data["name"],
        blocks=pipeline_data["definition"]["blocks"]
    )
    
    result, trace, trace_id = await workflow.execute(SEED_DATA["metadata"])
    print(f"trace_id: {trace_id}")
    print(f"result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
