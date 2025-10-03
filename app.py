import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from lib.blocks.registry import registry
from lib.pipeline import Pipeline
from lib.storage import Storage
from lib.workflow import Pipeline as WorkflowPipeline
from models import GenerationConfig, RecordStatus, RecordUpdate

storage = Storage()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await storage.init_db()
    yield


app = FastAPI(title="QADataGen", version="0.1.0", lifespan=lifespan)

# api router
api = FastAPI()


@api.post("/generate")
async def generate(
    file: UploadFile = File(...), config: GenerationConfig | None = None
) -> dict[str, Any]:
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="only JSON files accepted")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        pipeline = Pipeline(storage)
        result = await pipeline.process_seed_file(tmp_path, config)
        return result
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@api.get("/records")
async def get_records(
    status: RecordStatus | None = None, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    records = await storage.get_all(status=status, limit=limit, offset=offset)
    return [record.model_dump() for record in records]


@api.get("/records/{record_id}")
async def get_record(record_id: int) -> dict[str, Any]:
    record = await storage.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="record not found")
    return record.model_dump()


@api.put("/records/{record_id}")
async def update_record(record_id: int, update: RecordUpdate) -> dict[str, bool]:
    updates = update.model_dump(exclude_unset=True)
    success = await storage.update_record(record_id, **updates)
    if not success:
        raise HTTPException(status_code=404, detail="record not found")
    return {"success": True}


@api.get("/export")
async def export_records(status: RecordStatus | None = None) -> PlainTextResponse:
    jsonl = await storage.export_jsonl(status=status)
    return PlainTextResponse(content=jsonl, media_type="application/x-ndjson")


@api.get("/export/download")
async def download_export(status: RecordStatus | None = None) -> FileResponse:
    jsonl = await storage.export_jsonl(status=status)
    tmp_file = Path(tempfile.gettempdir()) / "qa_export.jsonl"
    tmp_file.write_text(jsonl, encoding="utf-8")
    return FileResponse(
        tmp_file,
        media_type="application/x-ndjson",
        filename="qa_export.jsonl",
    )


@api.get("/blocks")
async def list_blocks() -> list[dict[str, Any]]:
    return registry.list_blocks()


@api.post("/pipelines")
async def create_pipeline(pipeline_data: dict[str, Any]) -> dict[str, Any]:
    name = pipeline_data.get("name")
    blocks = pipeline_data.get("blocks")

    if not name or not blocks:
        raise HTTPException(status_code=400, detail="name and blocks required")

    pipeline_id = await storage.save_pipeline(name, pipeline_data)
    return {"id": pipeline_id, "name": name}


@api.get("/pipelines")
async def list_pipelines() -> list[dict[str, Any]]:
    return await storage.list_pipelines()


@api.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: int) -> dict[str, Any]:
    pipeline = await storage.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="pipeline not found")
    return pipeline


@api.post("/pipelines/{pipeline_id}/execute")
async def execute_pipeline(
    pipeline_id: int, data: dict[str, Any]
) -> dict[str, Any]:
    pipeline_data = await storage.get_pipeline(pipeline_id)
    if not pipeline_data:
        raise HTTPException(status_code=404, detail="pipeline not found")

    pipeline = WorkflowPipeline.load_from_dict(pipeline_data["definition"])
    result = await pipeline.execute(data)
    return result


@api.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: int) -> dict[str, bool]:
    success = await storage.delete_pipeline(pipeline_id)
    if not success:
        raise HTTPException(status_code=404, detail="pipeline not found")
    return {"success": True}


# mount api routes
app.mount("/api", api)

# serve frontend (built svelte app)
frontend_dir = Path("frontend/build")
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
