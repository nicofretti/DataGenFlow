"""domain entities organized by concern"""

from lib.entities.job import Job, JobStatus, TERMINAL_STATUSES
from lib.entities.record import Record, RecordCreate, RecordStatus, RecordUpdate
from lib.entities.pipeline import (
    Pipeline, BlockDefinition, SeedInput,
    Usage, Constraints, ExecutionResult,
    ValidationConfig, FieldOrder, TraceEntry,
    PipelineDefinition,
)
from lib.entities.llm_config import (
    LLMProvider, LLMModelConfig, EmbeddingModelConfig, ConnectionTestResult
)
from lib.entities.database import PipelineRecord
from lib.entities.api import GenerationConfig, SeedValidationRequest
from lib.entities.block_execution_context import BlockExecutionContext

__all__ = [
    # Job domain
    "Job", "JobStatus", "TERMINAL_STATUSES",
    # Record domain
    "Record", "RecordCreate", "RecordStatus", "RecordUpdate",
    # Pipeline domain
    "Pipeline", "BlockDefinition", "SeedInput",
    "Usage", "Constraints", "ExecutionResult",
    "ValidationConfig", "FieldOrder", "TraceEntry",
    "PipelineDefinition",
    # LLM Config domain
    "LLMProvider", "LLMModelConfig", "EmbeddingModelConfig", "ConnectionTestResult",
    # Database domain
    "PipelineRecord",
    # API domain
    "GenerationConfig", "SeedValidationRequest",
    # Execution context
    "BlockExecutionContext",
]
