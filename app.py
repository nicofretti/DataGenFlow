import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import APIRouter, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from config import settings
from lib.blocks.registry import registry
from lib.errors import BlockExecutionError, BlockNotFoundError, ValidationError
from lib.job_processor import process_job_in_thread
from lib.job_queue import JobQueue
from lib.llm_config import LLMConfigManager, LLMConfigNotFoundError
from lib.schema_utils import compute_accumulated_state_schema
from lib.storage import Storage
from lib.templates import template_registry
from lib.workflow import Pipeline as WorkflowPipeline
from models import (
    ConnectionTestResult,
    EmbeddingModelConfig,
    LLMModelConfig,
    Record,
    RecordStatus,
    RecordUpdate,
    SeedInput,
    SeedValidationRequest,
)

storage = Storage()
job_queue = JobQueue()
llm_config_manager = LLMConfigManager(storage)


def is_multiplier_pipeline(blocks: list[dict[str, Any]]) -> bool:
    if not blocks:
        return False

    first_block_type = blocks[0].get("type")
    if not first_block_type:
        return False

    block_class = registry.get_block_class(first_block_type)
    return getattr(block_class, "is_multiplier", False)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await storage.init_db()
    yield
    # close storage connection on shutdown
    await storage.close()


app = FastAPI(title="DataGenFlow", version="0.1.0", lifespan=lifespan)
api_router = APIRouter()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


def _validate_seed_structure(seed: dict[str, Any]) -> tuple[bool, bool, int]:
    """check seed structure and repetitions.

    returns (has_structure_error, has_repetition_error, zero_rep_count)
    """
    if not isinstance(seed, dict):
        return (True, False, 0)

    if "metadata" not in seed:
        return (True, False, 0)

    if not isinstance(seed["metadata"], dict):
        return (True, False, 0)

    repetitions = seed.get("repetitions", 1)
    if repetitions == 0:
        return (False, False, 1)
    if not isinstance(repetitions, int) or repetitions < 0:
        return (False, True, 0)

    return (False, False, 0)


def _validate_seed_fields(seed: dict[str, Any], required_inputs: list[str]) -> set[str]:
    """return set of missing required fields in seed metadata"""
    if not isinstance(seed, dict) or "metadata" not in seed:
        return set()

    metadata = seed["metadata"]
    if not isinstance(metadata, dict):
        return set()

    return {field for field in required_inputs if field not in metadata}


def _build_validation_errors(
    structure_err: bool, repetition_err: bool, missing: set[str], block_name: str
) -> list[str]:
    """build error messages from validation flags"""
    errors = []
    if structure_err:
        errors.append("Some seeds are not well structured (missing 'metadata' or invalid format)")
    if repetition_err:
        errors.append("Some seeds have invalid repetitions (must be positive integer)")
    if missing:
        fields_str = ", ".join(f"'{field}'" for field in sorted(missing))
        errors.append(
            f"Some seeds missing required field(s): {fields_str} (needed by {block_name} block)"
        )
    return errors


@api_router.post("/seeds/validate")
async def validate_seeds(request: SeedValidationRequest) -> dict[str, Any]:
    """validate seeds against pipeline's first block requirements"""
    pipeline_data = await storage.get_pipeline(request.pipeline_id)
    if not pipeline_data:
        raise HTTPException(status_code=404, detail="pipeline not found")

    blocks = pipeline_data["definition"]["blocks"]
    if not blocks:
        raise HTTPException(status_code=400, detail="pipeline has no blocks")

    block_class = registry.get_block_class(blocks[0]["type"])
    if not block_class:
        raise HTTPException(status_code=400, detail=f"block type '{blocks[0]['type']}' not found")

    required_inputs = block_class.get_required_fields(blocks[0].get("config", {}))
    structure_err, repetition_err, zero_count, missing_fields = False, False, 0, set()

    for seed in request.seeds:
        s_err, r_err, z_count = _validate_seed_structure(seed)
        structure_err, repetition_err, zero_count = (
            structure_err or s_err,
            repetition_err or r_err,
            zero_count + z_count,
        )
        missing_fields.update(_validate_seed_fields(seed, required_inputs))

    errors = _build_validation_errors(
        structure_err, repetition_err, missing_fields, block_class.name
    )
    warnings = (
        [f"{zero_count} seed(s) have repetitions=0 (will not generate records)"]
        if zero_count > 0
        else []
    )
    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


@api_router.post("/generate_from_file")
async def generate_from_file(
    file: UploadFile = File(...), pipeline_id: int = Form(...)
) -> dict[str, Any]:
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=400,
            detail="Only JSON files are accepted. Please upload a .json file.",
        )

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
        # execute pipeline seed.repetitions times
        for _ in range(seed.repetitions):
            total += 1
            try:
                # execute pipeline with metadata as input
                exec_result = await pipeline.execute(seed.metadata)
                # help mypy understand this is the tuple variant
                assert isinstance(exec_result, tuple)
                result, trace, trace_id = exec_result

                # create record from pipeline execution
                record = Record(
                    metadata=seed.metadata,
                    trace=trace,
                )

                await storage.save_record(record, pipeline_id=pipeline_id)
                success += 1
            except Exception as e:
                failed += 1
                logger.error(f"pipeline execution failed: {e}")

    return {"total": total, "success": success, "failed": failed}


async def _parse_markdown_file(content: bytes) -> tuple[list[dict[str, Any]], int]:
    """parse markdown file and return seeds and total samples"""
    markdown_content = content.decode("utf-8")
    if not markdown_content.strip():
        raise HTTPException(status_code=400, detail="Markdown file is empty")
    seeds = [{"repetitions": 1, "metadata": {"file_content": markdown_content}}]
    return seeds, 1


async def _parse_json_file(content: bytes) -> tuple[list[dict[str, Any]], int]:
    """parse and validate json seed file, return seeds and total samples"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"The JSON file is invalid: {str(e)}. Please check your file syntax.",
        )

    if not isinstance(data, (list, dict)):
        raise HTTPException(
            status_code=400,
            detail="The JSON file must contain an object or an array of objects.",
        )

    seeds = data if isinstance(data, list) else [data]
    for i, seed in enumerate(seeds):
        if not isinstance(seed, dict):
            raise HTTPException(
                status_code=400,
                detail=f"Seed {i + 1} must be an object. Please check your file structure.",
            )
        if "metadata" not in seed:
            raise HTTPException(
                status_code=400,
                detail=f"Seed {i + 1} is missing the required 'metadata' field.",
            )

    total = sum(
        seed.get("repetitions", 1) if isinstance(seed.get("repetitions", 1), int) else 1
        for seed in seeds
    )
    return seeds, total


async def _create_temp_seed_file(
    seeds: list[dict[str, Any]], content: bytes, is_markdown: bool, pipeline_id: int
) -> Path:
    """create temp file with seed data and return path"""
    import os

    file_suffix = ".md" if is_markdown else ".json"
    fd, tmp_path = tempfile.mkstemp(suffix=file_suffix, prefix=f"seed_{pipeline_id}_")
    try:
        os.write(fd, json.dumps(seeds).encode("utf-8") if is_markdown else content)
        os.close(fd)
        return Path(tmp_path)
    except Exception:
        os.close(fd)
        raise


@api_router.post("/generate")
async def generate(file: UploadFile = File(...), pipeline_id: int = Form(...)) -> dict[str, Any]:
    """start a new background job for pipeline execution from seed file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    is_markdown = file.filename.endswith(".md")
    if not is_markdown and not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json or .md files are accepted")

    active_job = job_queue.get_active_job()
    if active_job:
        raise HTTPException(
            status_code=409,
            detail=f"Job {active_job['id']} is already running. "
            "Cancel it first or wait for completion.",
        )

    content = await file.read()
    seeds, total_samples = await (
        _parse_markdown_file(content) if is_markdown else _parse_json_file(content)
    )
    tmp_file = await _create_temp_seed_file(seeds, content, is_markdown, pipeline_id)

    job_id = await storage.create_job(pipeline_id, total_samples, status="running")
    job_queue.create_job(job_id, pipeline_id, total_samples, status="running")
    process_job_in_thread(job_id, pipeline_id, str(tmp_file), job_queue, storage)

    return {"job_id": job_id}


@api_router.get("/jobs/active")
async def get_active_job() -> dict[str, Any] | None:
    """get currently running job"""
    active_job = job_queue.get_active_job()
    if not active_job:
        raise HTTPException(status_code=404, detail="no active job")
    return active_job


@api_router.get("/jobs/{job_id}")
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


@api_router.delete("/jobs/{job_id}")
async def cancel_job(job_id: int) -> dict[str, str]:
    """cancel a running job"""
    success = job_queue.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="job not found")

    # update database
    await storage.update_job(job_id, status="cancelled")

    return {"message": "Job cancelled"}


@api_router.get("/jobs")
async def list_jobs(pipeline_id: int | None = None) -> list[dict[str, Any]]:
    """list jobs, optionally filtered by pipeline_id"""
    # try memory first for recent jobs
    if pipeline_id:
        jobs = job_queue.get_pipeline_history(pipeline_id)
        if jobs:
            return jobs

    # fallback to database
    return await storage.list_jobs(pipeline_id=pipeline_id, limit=10)


@api_router.get("/records")
async def get_records(
    status: RecordStatus | None = None,
    limit: int = 100,
    offset: int = 0,
    job_id: int | None = None,
    pipeline_id: int | None = None,
) -> list[dict[str, Any]]:
    records = await storage.get_all(
        status=status,
        limit=limit,
        offset=offset,
        job_id=job_id,
        pipeline_id=pipeline_id,
    )
    return [record.model_dump() for record in records]


@api_router.get("/records/{record_id}")
async def get_record(record_id: int) -> dict[str, Any]:
    record = await storage.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="record not found")
    return record.model_dump()


@api_router.put("/records/{record_id}")
async def update_record(record_id: int, update: RecordUpdate) -> dict[str, bool]:
    updates = update.model_dump(exclude_unset=True)

    # separate standard fields from accumulated_state field updates
    standard_fields = {"output", "status", "metadata"}
    standard_updates = {k: v for k, v in updates.items() if k in standard_fields}
    accumulated_state_updates = {k: v for k, v in updates.items() if k not in standard_fields}

    # if there are accumulated_state field updates, handle them specially
    if accumulated_state_updates:
        success = await storage.update_record_accumulated_state(
            record_id, accumulated_state_updates, **standard_updates
        )
    else:
        success = await storage.update_record(record_id, **standard_updates)

    if not success:
        raise HTTPException(status_code=404, detail="record not found")
    return {"success": True}


@api_router.delete("/records")
async def delete_all_records(job_id: int | None = None) -> dict[str, Any]:
    count = await storage.delete_all_records(job_id=job_id)
    # also remove from in-memory job queue
    if job_id:
        job_queue.delete_job(job_id)
    return {"deleted": count}


@api_router.get("/export")
async def export_records(
    status: RecordStatus | None = None, job_id: int | None = None
) -> PlainTextResponse:
    jsonl = await storage.export_jsonl(status=status, job_id=job_id)
    return PlainTextResponse(content=jsonl, media_type="application/x-ndjson")


@api_router.get("/export/download")
async def download_export(
    status: RecordStatus | None = None, job_id: int | None = None
) -> FileResponse:
    jsonl = await storage.export_jsonl(status=status, job_id=job_id)
    tmp_file = Path(tempfile.gettempdir()) / "qa_export.jsonl"
    tmp_file.write_text(jsonl, encoding="utf-8")
    return FileResponse(
        tmp_file,
        media_type="application/x-ndjson",
        filename="qa_export.jsonl",
    )


@api_router.get("/blocks")
async def list_blocks() -> list[dict[str, Any]]:
    """list all registered blocks with dynamically injected model options"""
    blocks = registry.list_blocks()

    # get available llm models
    llm_models = await llm_config_manager.list_llm_models()
    model_names = [model.name for model in llm_models]

    # inject model options into TextGenerator and StructuredGenerator schemas
    for block in blocks:
        if block.get("type") in ["TextGenerator", "StructuredGenerator"]:
            if "config_schema" in block and "properties" in block["config_schema"]:
                if "model" in block["config_schema"]["properties"]:
                    # add enum with available model names
                    block["config_schema"]["properties"]["model"]["enum"] = model_names

    return blocks


@api_router.post("/pipelines")
async def create_pipeline(pipeline_data: dict[str, Any]) -> dict[str, Any]:
    name = pipeline_data.get("name")
    blocks = pipeline_data.get("blocks")

    if not name or not blocks:
        raise HTTPException(status_code=400, detail="name and blocks required")

    pipeline_id = await storage.save_pipeline(name, pipeline_data)
    return {"id": pipeline_id, "name": name}


@api_router.get("/pipelines")
async def list_pipelines() -> list[dict[str, Any]]:
    return await storage.list_pipelines()


@api_router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: int) -> dict[str, Any]:
    pipeline = await storage.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="pipeline not found")

    blocks = pipeline.get("definition", {}).get("blocks", [])
    pipeline["first_block_is_multiplier"] = is_multiplier_pipeline(blocks)

    return pipeline


@api_router.put("/pipelines/{pipeline_id}")
async def update_pipeline(pipeline_id: int, pipeline_data: dict[str, Any]) -> dict[str, Any]:
    name = pipeline_data.get("name")
    blocks = pipeline_data.get("blocks")

    if not name or not blocks:
        raise HTTPException(status_code=400, detail="name and blocks required")

    success = await storage.update_pipeline(pipeline_id, name, pipeline_data)
    if not success:
        raise HTTPException(status_code=404, detail="pipeline not found")

    return {"id": pipeline_id, "name": name}


@api_router.post("/pipelines/{pipeline_id}/execute", response_model=None)
async def execute_pipeline(pipeline_id: int, data: dict[str, Any]) -> dict[str, Any] | JSONResponse:
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
        return JSONResponse(status_code=400, content={"error": e.message, "detail": e.detail})
    except (BlockExecutionError, ValidationError) as e:
        logger.error(f"{e.__class__.__name__} in pipeline {pipeline_id}: {e.message}")
        return JSONResponse(status_code=400, content={"error": e.message, "detail": e.detail})
    except Exception as e:
        logger.exception(f"Unexpected error executing pipeline {pipeline_id}")
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})


@api_router.get("/pipelines/{pipeline_id}/accumulated_state_schema")
async def get_accumulated_state_schema(pipeline_id: int) -> dict[str, list[str]]:
    """get list of field names that will be in accumulated state for this pipeline"""
    pipeline_data = await storage.get_pipeline(pipeline_id)
    if not pipeline_data:
        raise HTTPException(status_code=404, detail="pipeline not found")

    blocks = pipeline_data["definition"]["blocks"]
    fields = compute_accumulated_state_schema(blocks)
    return {"fields": fields}


@api_router.put("/pipelines/{pipeline_id}/validation_config")
async def update_validation_config(
    pipeline_id: int, validation_config: dict[str, Any]
) -> dict[str, bool]:
    """update the validation_config for a pipeline"""
    # validate structure
    if "field_order" not in validation_config:
        raise HTTPException(
            status_code=400, detail="validation_config must have field_order property"
        )

    field_order = validation_config["field_order"]
    if not isinstance(field_order, dict):
        raise HTTPException(status_code=400, detail="field_order must be an object")

    required_keys = {"primary", "secondary", "hidden"}
    if not all(key in field_order for key in required_keys):
        raise HTTPException(
            status_code=400,
            detail=f"field_order must have {required_keys} arrays",
        )

    # update database
    success = await storage.update_pipeline_validation_config(pipeline_id, validation_config)
    if not success:
        raise HTTPException(status_code=404, detail="pipeline not found")

    return {"success": True}


@api_router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: int) -> dict[str, bool]:
    # get all jobs for this pipeline to remove from memory
    jobs = await storage.list_jobs(pipeline_id=pipeline_id, limit=1000)

    # delete pipeline (cascade deletes jobs and records)
    success = await storage.delete_pipeline(pipeline_id)
    if not success:
        raise HTTPException(status_code=404, detail="pipeline not found")

    # remove jobs from in-memory queue
    for job in jobs:
        job_queue.delete_job(job["id"])

    return {"success": True}


@api_router.get("/llm-models")
async def list_llm_models() -> list[LLMModelConfig]:
    """list all configured llm models"""
    return await llm_config_manager.list_llm_models()


@api_router.get("/llm-models/{name}")
async def get_llm_model(name: str) -> LLMModelConfig:
    """get llm model config by name"""
    try:
        return await llm_config_manager.get_llm_model(name)
    except LLMConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@api_router.post("/llm-models")
async def create_llm_model(config: LLMModelConfig) -> dict[str, str]:
    """create or update llm model config"""
    try:
        await llm_config_manager.save_llm_model(config)
        return {"message": "llm model saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.put("/llm-models/{name}")
async def update_llm_model(name: str, config: LLMModelConfig) -> dict[str, str]:
    """update llm model config"""
    if name != config.name:
        raise HTTPException(status_code=400, detail="name in path must match name in body")
    try:
        await llm_config_manager.save_llm_model(config)
        return {"message": "llm model updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.delete("/llm-models/{name}")
async def delete_llm_model(name: str) -> dict[str, str]:
    """delete llm model config"""
    try:
        await llm_config_manager.delete_llm_model(name)
        return {"message": "llm model deleted successfully"}
    except LLMConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@api_router.post("/llm-models/test")
async def test_llm_connection(config: LLMModelConfig) -> ConnectionTestResult:
    """test llm connection"""
    return await llm_config_manager.test_llm_connection(config)


@api_router.get("/embedding-models")
async def list_embedding_models() -> list[EmbeddingModelConfig]:
    """list all configured embedding models"""
    return await llm_config_manager.list_embedding_models()


@api_router.get("/embedding-models/{name}")
async def get_embedding_model(name: str) -> EmbeddingModelConfig:
    """get embedding model config by name"""
    try:
        return await llm_config_manager.get_embedding_model(name)
    except LLMConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@api_router.post("/embedding-models")
async def create_embedding_model(config: EmbeddingModelConfig) -> dict[str, str]:
    """create or update embedding model config"""
    try:
        await llm_config_manager.save_embedding_model(config)
        return {"message": "embedding model saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.put("/embedding-models/{name}")
async def update_embedding_model(name: str, config: EmbeddingModelConfig) -> dict[str, str]:
    """update embedding model config"""
    if name != config.name:
        raise HTTPException(status_code=400, detail="name in path must match name in body")
    try:
        await llm_config_manager.save_embedding_model(config)
        return {"message": "embedding model updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.delete("/embedding-models/{name}")
async def delete_embedding_model(name: str) -> dict[str, str]:
    """delete embedding model config"""
    try:
        await llm_config_manager.delete_embedding_model(name)
        return {"message": "embedding model deleted successfully"}
    except LLMConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@api_router.post("/embedding-models/test")
async def test_embedding_connection(
    config: EmbeddingModelConfig,
) -> ConnectionTestResult:
    """test embedding connection"""
    return await llm_config_manager.test_embedding_connection(config)


@api_router.get("/templates")
async def list_templates() -> list[dict[str, Any]]:
    """List all available pipeline templates"""
    return template_registry.list_templates()


@api_router.post("/pipelines/from_template/{template_id}")
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


# include api router with /api prefix
app.include_router(api_router, prefix="/api")

# serve frontend (built react app)
frontend_dir = Path("frontend/build")
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
