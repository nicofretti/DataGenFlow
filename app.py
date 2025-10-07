import asyncio
import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from config import settings
from lib.blocks.registry import registry
from lib.errors import BlockNotFoundError, BlockExecutionError, ValidationError
from lib.generator import Generator
from lib.job_processor import process_job_in_thread
from lib.job_queue import JobQueue
from lib.storage import Storage
from lib.templates import template_registry
from lib.workflow import Pipeline as WorkflowPipeline
from models import Record, RecordStatus, RecordUpdate, SeedInput

storage = Storage()
job_queue = JobQueue()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await storage.init_db()
    yield


app = FastAPI(title="QADataGen", version="0.1.0", lifespan=lifespan)

# api router
api = FastAPI()


@api.post("/generate_from_file")
async def generate_from_file(
    file: UploadFile = File(...), pipeline_id: int = Form(...)
) -> dict[str, Any]:
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="only JSON files accepted")

    # load pipeline
    pipeline_data = await storage.get_pipeline(pipeline_id)
    if not pipeline_data:
        raise HTTPException(status_code=404, detail="pipeline not found")

    pipeline = WorkflowPipeline.load_from_dict(pipeline_data["definition"])

    # parse seed file
    content = await file.read()
    data = json.loads(content)
    seeds = [SeedInput(**item) for item in (data if isinstance(data, list) else [data])]

    logger.info(f"processing {len(seeds)} seeds with pipeline {pipeline_id}")

    total = 0
    success = 0
    failed = 0

    # process each seed
    for seed in seeds:
        num_samples = seed.metadata.get("num_samples", 1)
        if not isinstance(num_samples, int):
            num_samples = 1

        # render templates if needed
        generator = Generator()
        system = generator.render_template(seed.system, seed.metadata)
        user = generator.render_template(seed.user, seed.metadata)

        # execute pipeline num_samples times
        for _ in range(num_samples):
            total += 1
            try:
                # prepare input data for pipeline
                input_data = {"system": system, "user": user, **seed.metadata}

                # execute pipeline with trace
                result, trace, trace_id = await pipeline.execute(input_data)

                # create record from seed + pipeline output
                record = Record(
                    system=system,
                    user=user,
                    assistant=result.get("assistant", ""),
                    metadata=seed.metadata,
                    trace=trace,
                )

                await storage.save_record(record, pipeline_id=pipeline_id)
                success += 1
            except Exception as e:
                failed += 1
                logger.error(f"pipeline execution failed: {e}")

    return {"total": total, "success": success, "failed": failed}


@api.post("/generate")
async def generate(
    file: UploadFile = File(...), pipeline_id: int = Form(...)
) -> dict[str, Any]:
    """start a new background job for pipeline execution from seed file"""
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="only JSON files accepted")

    # check if there's already an active job
    active_job = job_queue.get_active_job()
    if active_job:
        raise HTTPException(
            status_code=409,
            detail=f"Job {active_job['id']} is already running. Cancel it first or wait for completion.",
        )

    # parse seed file to calculate total samples
    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    seeds = data if isinstance(data, list) else [data]

    # calculate total executions from all seeds
    total_samples = sum(
        seed.get("repetitions", 1)
        if isinstance(seed.get("repetitions"), int)
        else 1
        for seed in seeds
    )

    # save file temporarily
    tmp_file = Path(tempfile.gettempdir()) / f"seed_{pipeline_id}_{tempfile.mktemp().split('/')[-1]}.json"
    tmp_file.write_text(content.decode('utf-8'), encoding='utf-8')

    # create job in database
    job_id = await storage.create_job(pipeline_id, total_samples, status="running")

    # register job in memory queue
    job_queue.create_job(job_id, pipeline_id, total_samples, status="running")

    # start background processing with file path
    process_job_in_thread(job_id, pipeline_id, str(tmp_file), job_queue, storage)

    return {"job_id": job_id}


@api.get("/jobs/active")
async def get_active_job() -> dict[str, Any] | None:
    """get currently running job"""
    active_job = job_queue.get_active_job()
    if not active_job:
        raise HTTPException(status_code=404, detail="no active job")
    return active_job


@api.get("/jobs/{job_id}")
async def get_job(job_id: int) -> dict[str, Any]:
    """get job status by id"""
    # try memory first
    job = job_queue.get_job(job_id)
    if job:
        return job

    # fallback to database
    job = await storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@api.delete("/jobs/{job_id}")
async def cancel_job(job_id: int) -> dict[str, str]:
    """cancel a running job"""
    success = job_queue.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="job not found")

    # update database
    await storage.update_job(job_id, status="cancelled")

    return {"message": "Job cancelled"}


@api.get("/jobs")
async def list_jobs(pipeline_id: int | None = None) -> list[dict[str, Any]]:
    """list jobs, optionally filtered by pipeline_id"""
    # try memory first for recent jobs
    if pipeline_id:
        jobs = job_queue.get_pipeline_history(pipeline_id)
        if jobs:
            return jobs

    # fallback to database
    return await storage.list_jobs(pipeline_id=pipeline_id, limit=10)


@api.get("/records")
async def get_records(
    status: RecordStatus | None = None, limit: int = 100, offset: int = 0, job_id: int | None = None
) -> list[dict[str, Any]]:
    records = await storage.get_all(status=status, limit=limit, offset=offset, job_id=job_id)
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


@api.delete("/records")
async def delete_all_records() -> dict[str, Any]:
    count = await storage.delete_all_records()
    return {"deleted": count}


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
    try:
        pipeline_data = await storage.get_pipeline(pipeline_id)
        if not pipeline_data:
            raise HTTPException(status_code=404, detail="pipeline not found")

        pipeline = WorkflowPipeline.load_from_dict(pipeline_data["definition"])
        result, trace, trace_id = await pipeline.execute(data)
        return {"result": result, "trace": trace, "trace_id": trace_id}
    except HTTPException:
        # Let HTTPException propagate to FastAPI
        raise
    except BlockNotFoundError as e:
        logger.error(f"BlockNotFoundError in pipeline {pipeline_id}: {e.message}")
        return JSONResponse(
            status_code=400,
            content={"error": e.message, "detail": e.detail}
        )
    except (BlockExecutionError, ValidationError) as e:
        logger.error(f"{e.__class__.__name__} in pipeline {pipeline_id}: {e.message}")
        return JSONResponse(
            status_code=400,
            content={"error": e.message, "detail": e.detail}
        )
    except Exception as e:
        logger.exception(f"Unexpected error executing pipeline {pipeline_id}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Unexpected error: {str(e)}"}
        )


@api.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: int) -> dict[str, bool]:
    success = await storage.delete_pipeline(pipeline_id)
    if not success:
        raise HTTPException(status_code=404, detail="pipeline not found")
    return {"success": True}


@api.get("/templates")
async def list_templates() -> list[dict[str, Any]]:
    """List all available pipeline templates"""
    return template_registry.list_templates()


@api.post("/pipelines/from_template/{template_id}")
async def create_pipeline_from_template(template_id: str) -> dict[str, Any]:
    """Create a new pipeline from a template"""
    template = template_registry.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="template not found")

    # Create pipeline with template name
    pipeline_name = template["name"]
    pipeline_data = {"name": pipeline_name, "blocks": template["blocks"]}

    pipeline_id = await storage.save_pipeline(pipeline_name, pipeline_data)
    return {"id": pipeline_id, "name": pipeline_name, "template_id": template_id}


# mount api routes
app.mount("/api", api)

# serve frontend (built svelte app)
frontend_dir = Path("frontend/build")
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
