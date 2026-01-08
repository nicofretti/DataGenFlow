"""
usage tracker for accumulating LLM token usage across multiple calls

useful for blocks that call external libraries (like ragas) which make
LLM calls internally without exposing usage information.
"""

import contextvars
import threading
from collections import defaultdict
from typing import Any

from lib.entities.pipeline import Usage

# context variable to store current trace_id for calls that don't pass metadata
_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_trace_id", default=None
)


class UsageTracker:
    """thread-safe usage accumulator per trace_id

    usage:
        # register callback in app.py
        litellm.success_callback = ["langfuse", UsageTracker.callback]

        # set current trace_id for external library calls (like ragas)
        UsageTracker.set_current_trace_id(context.trace_id)

        # in block execute method, after LLM calls complete
        usage = UsageTracker.get_and_clear(context.trace_id)
        return {"_usage": usage}
    """

    _usage: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
        }
    )
    _lock = threading.Lock()

    @classmethod
    def set_current_trace_id(cls, trace_id: str | None) -> None:
        """set current trace_id for calls that don't pass metadata"""
        _current_trace_id.set(trace_id)

    @classmethod
    def get_current_trace_id(cls) -> str | None:
        """get current trace_id from context"""
        return _current_trace_id.get()

    @classmethod
    def callback(
        cls,
        kwargs: dict[str, Any],
        completion_response: Any,
        start_time: float,
        end_time: float,
    ) -> None:
        """LiteLLM success callback to accumulate usage"""
        # try metadata first, fallback to context variable
        trace_id = kwargs.get("metadata", {}).get("trace_id")
        if not trace_id:
            trace_id = cls.get_current_trace_id()
        if not trace_id:
            return

        usage = getattr(completion_response, "usage", None)
        if not usage:
            return

        with cls._lock:
            cls._usage[trace_id]["input_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
            cls._usage[trace_id]["output_tokens"] += getattr(usage, "completion_tokens", 0) or 0
            cls._usage[trace_id]["cached_tokens"] += (
                getattr(usage, "cache_read_input_tokens", 0) or 0
            )

    @classmethod
    def get_and_clear(cls, trace_id: str) -> dict[str, int]:
        """get accumulated usage for trace_id and clear it"""
        with cls._lock:
            usage = dict(
                cls._usage.pop(
                    trace_id,
                    {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cached_tokens": 0,
                    },
                )
            )
        return usage

    @classmethod
    def to_pipeline_usage(cls, trace_id: str) -> Usage:
        """get accumulated usage as pipeline.Usage object"""
        usage = cls.get_and_clear(trace_id)
        return Usage(
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cached_tokens=usage["cached_tokens"],
        )

    @classmethod
    def clear_all(cls) -> None:
        """clear all tracked usage (useful for testing)"""
        with cls._lock:
            cls._usage.clear()
