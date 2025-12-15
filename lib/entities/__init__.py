"""domain entities organized by concern"""

from lib.entities.api import GenerationConfig, SeedValidationRequest
from lib.entities.block_execution_context import BlockExecutionContext
from lib.entities.database import PipelineRecord
from lib.entities.job import TERMINAL_STATUSES, Job, JobStatus
from lib.entities.llm_config import (
    ConnectionTestResult,
    EmbeddingModelConfig,
    LLMModelConfig,
    LLMProvider,
)
from lib.entities.pipeline import (
    BlockDefinition,
    Constraints,
    ExecutionResult,
    FieldOrder,
    Pipeline,
    PipelineDefinition,
    SeedInput,
    TraceEntry,
    Usage,
    ValidationConfig,
)
from lib.entities.record import Record, RecordCreate, RecordStatus, RecordUpdate

__all__ = [
    # Job domain
    "Job",
    "JobStatus",
    "TERMINAL_STATUSES",
    # Record domain
    "Record",
    "RecordCreate",
    "RecordStatus",
    "RecordUpdate",
    # Pipeline domain
    "Pipeline",
    "BlockDefinition",
    "SeedInput",
    "Usage",
    "Constraints",
    "ExecutionResult",
    "ValidationConfig",
    "FieldOrder",
    "TraceEntry",
    "PipelineDefinition",
    # LLM Config domain
    "LLMProvider",
    "LLMModelConfig",
    "EmbeddingModelConfig",
    "ConnectionTestResult",
    # Database domain
    "PipelineRecord",
    # API domain
    "GenerationConfig",
    "SeedValidationRequest",
    # Execution context
    "BlockExecutionContext",
]
