import json
import logging
import os
from datetime import datetime
from typing import Any

from lib.blocks.base import BaseBlock

logger = logging.getLogger(__name__)


class LangfuseDatasetBlock(BaseBlock):
    name = "Langfuse Dataset Upload"
    description = "Upload generated records to Langfuse dataset for evaluation"
    category = "integrations"
    inputs = ["*"]
    outputs = ["langfuse_upload_status"]

    def __init__(self):
        pass

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        from app import storage

        # check if langfuse env vars are configured
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if not public_key or not secret_key:
            logger.warning("Langfuse credentials not configured, skipping upload")
            return {"langfuse_upload_status": "skipped: credentials not configured"}

        # get job_id from accumulated state
        job_id = data.get("job_id")
        if not job_id:
            logger.warning("No job_id in accumulated state, skipping upload")
            return {"langfuse_upload_status": "skipped: only works in job context"}

        try:
            from langfuse import Langfuse

            # initialize langfuse client
            langfuse = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

            # get job and pipeline info
            job = await storage.get_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return {"langfuse_upload_status": "error: job not found"}

            pipeline = await storage.get_pipeline(job["pipeline_id"])
            if not pipeline:
                logger.error(f"Pipeline {job['pipeline_id']} not found")
                return {"langfuse_upload_status": "error: pipeline not found"}

            # generate dataset name: pipeline_name_timestamp
            pipeline_name = pipeline["name"].lower().replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dataset_name = f"{pipeline_name}_{timestamp}"

            # fetch all records for this job
            records = await storage.get_all(job_id=job_id)
            if not records:
                logger.warning(f"No records found for job {job_id}")
                return {"langfuse_upload_status": "skipped: no records to upload"}

            # create or get dataset
            dataset = langfuse.create_dataset(name=dataset_name)

            # upload each record as dataset item
            for record in records:
                try:
                    # parse metadata from json string
                    metadata_dict = (
                        json.loads(record.metadata)
                        if isinstance(record.metadata, str)
                        else record.metadata
                    )

                    # create dataset item
                    dataset.create_item(
                        input=metadata_dict,  # seed variables
                        expected_output=record.output,  # final pipeline output
                        metadata={
                            "record_id": record.id,
                            "status": record.status,
                            "trace": record.trace,
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to upload record {record.id}: {e}")
                    continue

            # flush langfuse client
            langfuse.flush()

            # update job metadata with success
            job_metadata = {
                "langfuse": {
                    "error": "",
                    "message": f"Uploaded {len(records)} records to dataset '{dataset_name}'",
                }
            }
            await storage.update_job(job_id, metadata=json.dumps(job_metadata))

            logger.info(
                f"Uploaded {len(records)} records to Langfuse dataset '{dataset_name}'"
            )
            return {
                "langfuse_upload_status": f"uploaded {len(records)} records to dataset '{dataset_name}'"
            }

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
                await storage.update_job(job_id, metadata=json.dumps(job_metadata))
            except Exception as update_error:
                logger.error(f"Failed to update job metadata: {update_error}")

            return {"langfuse_upload_status": f"error: {str(e)}"}
