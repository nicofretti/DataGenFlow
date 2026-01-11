import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import APIRouter, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from config import settings
from lib.blocks.registry import registry
from lib.constants import RECORD_UPDATABLE_FIELDS
from lib.entities import (
    ConnectionTestResult,
    EmbeddingModelConfig,
    JobStatus,
    LLMModelConfig,
    PipelineRecord,
    RecordCreate,
    RecordStatus,
    RecordUpdate,
    SeedInput,
    SeedValidationRequest,
    ValidationConfig,
)
from lib.errors import BlockExecutionError, BlockNotFoundError, ValidationError
from lib.job_processor import process_job_in_thread
from lib.job_queue import JobQueue
from lib.llm_config import LLMConfigManager, LLMConfigNotFoundError
from lib.storage import Storage
from lib.templates import template_registry
from lib.workflow import Pipeline as WorkflowPipeline

storage = Storage()
job_queue = JobQueue()
llm_config_manager = LLMConfigManager(storage)

# security: file upload size limit
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def is_multiplier_pipeline(blocks: list[dict[str, Any]]) -> bool:
    if not blocks:
        return False

    first_block_type = blocks[0].get("type")
    if not first_block_type:
        return False

    block_class = registry.get_block_class(first_block_type)
    return getattr(block_class, "is_multiplier", False)


def _patch_langfuse_usage_bug() -> None:
    """patch litellm langfuse bug where .get() is called on pydantic model instead of dict"""
    try:
        from litellm.types.utils import CompletionUsage

        if not hasattr(CompletionUsage, "get"):
            # add get method so pydantic model works like dict
            def pydantic_get(self, key, default=None):
                return getattr(self, key, default)

            CompletionUsage.get = pydantic_get
    except (ImportError, AttributeError):
        # best-effort patch: if litellm or CompletionUsage is unavailable or changed,
        # simply skip applying the compatibility shim and continue without failing.
        logger.warning(
            "Skipping Langfuse usage patch: litellm or CompletionUsage is unavailable "
            "or has an unexpected structure."
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    import os

    import litellm

    from lib.blocks.commons import UsageTracker

    await storage.init_db()

    # patch langfuse bug before enabling it
    _patch_langfuse_usage_bug()

    # configure langfuse integration and usage tracking
    # note: litellm.callbacks is for custom callbacks, success_callback is for built-in integrations
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        litellm.success_callback = ["langfuse"]
        logger.info("Langfuse observability enabled")

    # always register usage tracker via callbacks (works for all LLM calls including RAGAS)
    litellm.callbacks = [UsageTracker.callback]

    yield
    # close storage connection on shutdown
    await storage.close()


app = FastAPI(title="DataGenFlow", version="0.1.0", lifespan=lifespan)
api_router = APIRouter()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/api/langfuse/status")
async def langfuse_status() -> dict[str, Any]:
    """check if langfuse integration is enabled"""
    import os

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    enabled = bool(public_key and secret_key)
    return {
        "enabled": enabled,
        "host": host if enabled else None,
    }


def _validate_seed_repetitions(seed: SeedInput) -> tuple[bool, int]:
    """check seed repetitions.

    returns (has_repetition_error, zero_rep_count)
    """
    if seed.repetitions == 0:
        return (False, 1)
    if seed.repetitions < 0:
        return (True, 0)
    return (False, 0)


def _validate_seed_fields(seed: SeedInput, required_inputs: list[str]) -> set[str]:
    """return set of missing required fields in seed metadata"""
    return {field for field in required_inputs if field not in seed.metadata}


def _build_validation_errors(repetition_err: bool, missing: set[str], block_name: str) -> list[str]:
    """build error messages from validation flags"""
    errors = []
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

    blocks = pipeline_data.definition["blocks"]
    if not blocks:
        raise HTTPException(status_code=400, detail="pipeline has no blocks")

    block_class = registry.get_block_class(blocks[0]["type"])
    if not block_class:
        raise HTTPException(status_code=400, detail=f"block type '{blocks[0]['type']}' not found")

    required_inputs = block_class.get_required_fields(blocks[0].get("config", {}))
    repetition_err, zero_count, missing_fields = False, 0, set()

    for seed in request.seeds:
        r_err, z_count = _validate_seed_repetitions(seed)
        repetition_err = repetition_err or r_err
        zero_count += z_count
        missing_fields.update(_validate_seed_fields(seed, required_inputs))

    errors = _build_validation_errors(repetition_err, missing_fields, block_class.name)
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

    pipeline = WorkflowPipeline.load_from_dict(pipeline_data.definition)

    # parse seed file with size limit
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"file too large (max {MAX_FILE_SIZE // (1024 * 1024)}MB)",
        )
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
                exec_result = await pipeline.execute(seed.metadata, pipeline_id=pipeline_id)
                # help mypy understand this is the tuple variant
                assert isinstance(exec_result, tuple)
                result, trace, trace_id = exec_result

                # create record from pipeline execution
                record = RecordCreate(
                    metadata=seed.metadata,
                    trace=trace,
                )

                await storage.save_record(record, pipeline_id=pipeline_id)
                success += 1
            except Exception:
                failed += 1
                logger.exception("pipeline execution failed")

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
        logger.exception(f"failed to create temp seed file for pipeline {pipeline_id}")
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
            detail=f"Job {active_job.id} is already running. "
            "Cancel it first or wait for completion.",
        )

    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"file too large (max {MAX_FILE_SIZE // (1024 * 1024)}MB)",
        )
    seeds, total_samples = await (
        _parse_markdown_file(content) if is_markdown else _parse_json_file(content)
    )
    tmp_file = await _create_temp_seed_file(seeds, content, is_markdown, pipeline_id)

    job_id = await storage.create_job(pipeline_id, total_samples, status=JobStatus.RUNNING)
    job_queue.create_job(job_id, pipeline_id, total_samples, status=JobStatus.RUNNING)
    process_job_in_thread(job_id, pipeline_id, str(tmp_file), job_queue, storage)

    return {"job_id": job_id}


@api_router.get("/jobs/active")
async def get_active_job() -> dict[str, Any] | None:
    """get currently running job"""
    active_job = job_queue.get_active_job()
    if not active_job:
        raise HTTPException(status_code=404, detail="no active job")
    return active_job.model_dump()


@api_router.get("/jobs/{job_id}")
async def get_job(job_id: int) -> dict[str, Any]:
    """get job status by id"""
    # try memory first
    job = job_queue.get_job(job_id)
    if job:
        return job.model_dump()

    # fallback to database
    job_obj = await storage.get_job(job_id)
    if not job_obj:
        raise HTTPException(status_code=404, detail="job not found")
    return job_obj.model_dump()


@api_router.delete("/jobs/{job_id}")
async def cancel_job(job_id: int) -> dict[str, str]:
    """cancel a running job"""
    success = job_queue.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="job not found")

    # update database
    await storage.update_job(job_id, status=JobStatus.CANCELLED)

    return {"message": "Job cancelled"}


@api_router.get("/jobs")
async def list_jobs(pipeline_id: int | None = None) -> list[dict[str, Any]]:
    """list jobs, optionally filtered by pipeline_id"""
    # try memory first for recent jobs
    if pipeline_id:
        jobs = job_queue.get_pipeline_history(pipeline_id)
        if jobs:
            return [j.model_dump() for j in jobs]

    # fallback to database
    jobs_list = await storage.list_jobs(pipeline_id=pipeline_id, limit=10)
    return [job.model_dump() for job in jobs_list]


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
    standard_updates = {k: v for k, v in updates.items() if k in RECORD_UPDATABLE_FIELDS}
    accumulated_state_updates = {
        k: v for k, v in updates.items() if k not in RECORD_UPDATABLE_FIELDS
    }

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

    # get available llm and embedding models
    llm_models = await llm_config_manager.list_llm_models()
    embedding_models = await llm_config_manager.list_embedding_models()
    model_names = [model.name for model in llm_models]
    embedding_names = [model.name for model in embedding_models]

    # inject model options into block schemas
    for block in blocks:
        block_type = block.get("type")
        props = block.get("config_schema", {}).get("properties", {})

        # inject LLM model options
        if block_type in ["TextGenerator", "StructuredGenerator", "RagasMetrics"]:
            if "model" in props:
                props["model"]["enum"] = model_names

        # inject embedding model options for RagasMetrics
        if block_type == "RagasMetrics":
            if "embedding_model" in props:
                props["embedding_model"]["enum"] = embedding_names

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
async def list_pipelines() -> list[PipelineRecord]:
    return await storage.list_pipelines()


@api_router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: int) -> dict[str, Any]:
    pipeline = await storage.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="pipeline not found")

    blocks = pipeline.definition.get("blocks", [])
    pipeline_dict = pipeline.model_dump()
    pipeline_dict["first_block_is_multiplier"] = is_multiplier_pipeline(blocks)
    pipeline_dict["first_block_type"] = blocks[0].get("type") if blocks else None

    return pipeline_dict


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

        pipeline = WorkflowPipeline.load_from_dict(pipeline_data.definition)
        exec_result = await pipeline.execute(data, pipeline_id=pipeline_id)
        # handle both ExecutionResult and list[ExecutionResult]
        if isinstance(exec_result, list):
            # multiplier pipeline
            return {
                "results": [
                    {
                        "result": r.result,
                        "trace": r.trace,
                        "trace_id": r.trace_id,
                        "usage": r.usage.model_dump(),
                    }
                    for r in exec_result
                ]
            }
        else:
            # normal pipeline
            return {
                "result": exec_result.result,
                "trace": exec_result.trace,
                "trace_id": exec_result.trace_id,
                "usage": exec_result.usage.model_dump(),
            }
    except HTTPException:
        # Let HTTPException propagate to FastAPI
        raise
    except BlockNotFoundError as e:
        logger.exception(f"BlockNotFoundError in pipeline {pipeline_id}")
        return JSONResponse(status_code=400, content={"error": e.message, "detail": e.detail})
    except (BlockExecutionError, ValidationError) as e:
        logger.exception(f"{e.__class__.__name__} in pipeline {pipeline_id}")
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

    blocks = pipeline_data.definition.get("blocks", [])
    fields = registry.compute_accumulated_state_schema(blocks)
    return {"fields": fields}


@api_router.put("/pipelines/{pipeline_id}/validation_config")
async def update_validation_config(
    pipeline_id: int, validation_config: dict[str, Any]
) -> dict[str, bool]:
    """update the validation_config for a pipeline"""
    # validate structure using pydantic
    try:
        validated_config = ValidationConfig(**validation_config)
    except PydanticValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # update database
    success = await storage.update_pipeline_validation_config(
        pipeline_id, validated_config.model_dump()
    )
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
        job_queue.delete_job(job.id)

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
        logger.exception("failed to save llm model")
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
        logger.exception(f"failed to update llm model {name}")
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
        logger.exception("failed to save embedding model")
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
        logger.exception(f"failed to update embedding model {name}")
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
