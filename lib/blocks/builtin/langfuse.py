import json
import logging
import os
from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext

logger = logging.getLogger(__name__)


class LangfuseDatasetBlock(BaseBlock):
    name = "Langfuse Dataset Upload"
    description = "Upload generated records to Langfuse dataset for evaluation"
    category = "integrations"
    inputs = ["*"]
    outputs = ["langfuse_upload_status"]

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        from app import storage

        # check if langfuse env vars are configured
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if not public_key or not secret_key:
            logger.warning("Langfuse credentials not configured, skipping upload")
            return {"langfuse_upload_status": "skipped: credentials not configured"}

        # only works in job context
        if context.job_id == 0:
            logger.warning("Not in job context, skipping upload")
            return {"langfuse_upload_status": "skipped: only works in job context"}

        try:
            # get job to check if we should upload now
            job = await storage.get_job(context.job_id)
            if not job:
                logger.error(f"Job {context.job_id} not found")
                return {"langfuse_upload_status": "error: job not found"}

            # only upload on the last seed to avoid duplicate uploads
            # check if this is the final execution
            if job.current_seed < job.total_seeds:
                logger.debug(
                    f"Skipping upload for job {context.job_id}: "
                    f"seed {job.current_seed}/{job.total_seeds} (waiting for completion)"
                )
                status = (
                    f"pending: waiting for job completion ({job.current_seed}/{job.total_seeds})"
                )
                return {"langfuse_upload_status": status}

            # check if already uploaded (idempotency)
            if job.metadata:
                try:
                    metadata = (
                        json.loads(job.metadata) if isinstance(job.metadata, str) else job.metadata
                    )
                    if metadata.get("langfuse", {}).get("uploaded"):
                        logger.info(f"Job {context.job_id} already uploaded to Langfuse, skipping")
                        msg = metadata["langfuse"].get("message", "")
                        return {"langfuse_upload_status": f"already uploaded: {msg}"}
                except (json.JSONDecodeError, TypeError):
                    pass
        except Exception as e:
            logger.exception("Failed to check job status")
            return {"langfuse_upload_status": f"error: {str(e)}"}

        try:
            from langfuse import Langfuse

            # initialize langfuse client
            langfuse = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

            # get pipeline info
            pipeline = await storage.get_pipeline(job.pipeline_id)
            if not pipeline:
                logger.error(f"Pipeline {job.pipeline_id} not found")
                return {"langfuse_upload_status": "error: pipeline not found"}

            # generate stable dataset name using job_id: pipeline_name_job{id}
            # this ensures all records from the same job go into the same dataset
            pipeline_name = pipeline.name.lower().replace(" ", "_")
            dataset_name = f"{pipeline_name}_job_{context.job_id}"

            # fetch all records for this job
            records = await storage.get_all(job_id=context.job_id)
            if not records:
                logger.warning(f"No records found for job {context.job_id}")
                return {"langfuse_upload_status": "skipped: no records to upload"}

            # create or get dataset (this ensures the dataset exists)
            langfuse.create_dataset(name=dataset_name)

            # upload each record as dataset item
            uploaded_count = 0
            for record in records:
                try:
                    # parse metadata from json string
                    metadata_dict = (
                        json.loads(record.metadata)
                        if isinstance(record.metadata, str)
                        else record.metadata
                    )

                    # create dataset item using langfuse client directly
                    langfuse.create_dataset_item(
                        dataset_name=dataset_name,
                        input=metadata_dict,  # seed variables
                        expected_output=record.output,  # final pipeline output
                        metadata={
                            "record_id": record.id,
                            "status": record.status,
                            "trace": record.trace,
                        },
                    )
                    uploaded_count += 1
                except Exception as e:
                    logger.warning(f"Failed to upload record {record.id}: {e}")
                    continue

            # flush langfuse client
            langfuse.flush()

            # update job metadata with success and mark as uploaded
            job_metadata = {
                "langfuse": {
                    "uploaded": True,
                    "dataset_name": dataset_name,
                    "records_count": uploaded_count,
                    "records_total": len(records),
                    "error": "",
                    "message": (
                        f"Uploaded {uploaded_count}/{len(records)} records "
                        f"to dataset '{dataset_name}'"
                    ),
                }
            }
            await storage.update_job(context.job_id, metadata=json.dumps(job_metadata))

            logger.info(
                f"Uploaded {uploaded_count}/{len(records)} records "
                f"to Langfuse dataset '{dataset_name}'"
            )
            status = f"uploaded {uploaded_count}/{len(records)} records to dataset '{dataset_name}'"
            return {"langfuse_upload_status": status}

        except Exception as e:
            logger.exception("Langfuse upload failed")
            # update job metadata with error
            job_metadata = {
                "langfuse": {
                    "error": str(e),
                    "message": "",
                }
            }
            try:
                await storage.update_job(context.job_id, metadata=json.dumps(job_metadata))
            except Exception as update_error:
                logger.error(f"Failed to update job metadata: {update_error}")

            return {"langfuse_upload_status": f"error: {str(e)}"}
