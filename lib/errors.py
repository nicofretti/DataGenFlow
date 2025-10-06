"""
Custom exceptions for pipeline execution
"""


class PipelineError(Exception):
    """Base exception for all pipeline-related errors"""

    def __init__(self, message: str, detail: dict | None = None):
        self.message = message
        self.detail = detail or {}
        super().__init__(self.message)


class BlockNotFoundError(PipelineError):
    """Raised when a block type is not registered"""

    pass


class BlockExecutionError(PipelineError):
    """Raised when a block fails during execution"""

    pass


class ValidationError(PipelineError):
    """Raised when a block returns fields not declared in outputs"""

    pass
