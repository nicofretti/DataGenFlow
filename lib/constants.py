"""shared constants for the application"""

# fields that can be updated on a record via API
RECORD_UPDATABLE_FIELDS = frozenset({"output", "status", "metadata"})

# fields that can be updated on a job
JOB_UPDATABLE_FIELDS = frozenset(
    {
        "status",
        "current_seed",
        "total_seeds",
        "records_generated",
        "records_failed",
        "progress",
        "current_block",
        "current_step",
        "error",
        "completed_at",
        "usage",
    }
)
