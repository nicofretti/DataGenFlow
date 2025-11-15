import json
import logging
from datetime import datetime
from typing import Any, Callable

import aiosqlite
from aiosqlite import Connection

from config import settings
from models import Record, RecordStatus

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, db_path: str = settings.DATABASE_PATH) -> None:
        self.db_path = db_path
        self._conn: Connection | None = None  # persistent connection for :memory:

    async def init_db(self) -> None:
        # ensure data directory exists for file-based databases
        if self.db_path != ":memory:":
            settings.ensure_data_dir()

        # for :memory: db, keep connection open persistently
        if self.db_path == ":memory:":
            self._conn = await aiosqlite.connect(self.db_path)
            db = self._conn
        else:
            db = await aiosqlite.connect(self.db_path)

        try:
            # create pipelines table first to avoid foreign key issues
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS pipelines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    definition TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pipeline_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    total_seeds INTEGER NOT NULL,
                    current_seed INTEGER DEFAULT 0,
                    records_generated INTEGER DEFAULT 0,
                    records_failed INTEGER DEFAULT 0,
                    progress REAL DEFAULT 0.0,
                    current_block TEXT,
                    current_step TEXT,
                    error TEXT,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
                )
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    output TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    status TEXT NOT NULL,
                    pipeline_id INTEGER,
                    job_id INTEGER,
                    trace TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id),
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                )
            """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status ON records(status)
            """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_created_at ON records(created_at)
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_models (
                    name TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    api_key TEXT,
                    model_name TEXT NOT NULL
                )
            """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_models (
                    name TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    api_key TEXT,
                    model_name TEXT NOT NULL,
                    dimensions INTEGER
                )
            """
            )

            # migrate existing tables
            await self._migrate_schema(db)

            # auto-migration from .env
            await self._migrate_env_to_db(db)

            await db.commit()
        finally:
            # only close if not using persistent connection
            if self.db_path != ":memory:":
                await db.close()

    async def _migrate_schema(self, db: Connection) -> None:
        # migrate records table
        cursor = await db.execute("PRAGMA table_info(records)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        if "pipeline_id" not in column_names:
            await db.execute("ALTER TABLE records ADD COLUMN pipeline_id INTEGER")

        if "job_id" not in column_names:
            await db.execute("ALTER TABLE records ADD COLUMN job_id INTEGER")

        if "trace" not in column_names:
            await db.execute("ALTER TABLE records ADD COLUMN trace TEXT")

        # migrate pipelines table
        cursor = await db.execute("PRAGMA table_info(pipelines)")
        pipeline_columns = await cursor.fetchall()
        pipeline_column_names = [col[1] for col in pipeline_columns]

        if "validation_config" not in pipeline_column_names:
            await db.execute("ALTER TABLE pipelines ADD COLUMN validation_config TEXT")

        # migrate jobs table
        cursor = await db.execute("PRAGMA table_info(jobs)")
        job_columns = await cursor.fetchall()
        job_column_names = [col[1] for col in job_columns]

        if "current_seed" not in job_column_names:
            await db.execute("ALTER TABLE jobs ADD COLUMN current_seed INTEGER DEFAULT 0")

        if "progress" not in job_column_names:
            await db.execute("ALTER TABLE jobs ADD COLUMN progress REAL DEFAULT 0.0")

        if "current_block" not in job_column_names:
            await db.execute("ALTER TABLE jobs ADD COLUMN current_block TEXT")

        if "current_step" not in job_column_names:
            await db.execute("ALTER TABLE jobs ADD COLUMN current_step TEXT")

        if "created_at" not in job_column_names:
            await db.execute("ALTER TABLE jobs ADD COLUMN created_at TIMESTAMP")

        if "error" not in job_column_names:
            await db.execute("ALTER TABLE jobs ADD COLUMN error TEXT")

    async def _migrate_env_to_db(self, db: Connection) -> None:
        """migrate .env config to database if no models configured"""
        # check if any llm models exist
        cursor = await db.execute("SELECT COUNT(*) FROM llm_models")
        count_row = await cursor.fetchone()
        model_count = count_row[0] if count_row else 0

        if model_count == 0 and settings.LLM_MODEL:
            # detect provider from endpoint
            endpoint_lower = settings.LLM_ENDPOINT.lower()
            if "11434" in endpoint_lower or "ollama" in endpoint_lower:
                provider = "ollama"
            elif "anthropic" in endpoint_lower:
                provider = "anthropic"
            elif "generativelanguage" in endpoint_lower or "gemini" in endpoint_lower:
                provider = "gemini"
            else:
                provider = "openai"

            # create default model from .env
            await db.execute(
                """
                INSERT INTO llm_models (name, provider, endpoint, api_key, model_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "default",
                    provider,
                    settings.LLM_ENDPOINT,
                    settings.LLM_API_KEY if settings.LLM_API_KEY else None,
                    settings.LLM_MODEL,
                ),
            )

    async def _execute_with_connection(self, func: Callable[[Connection], Any]) -> Any:
        if self._conn:
            result = await func(self._conn)
            await self._conn.commit()
            return result

        async with aiosqlite.connect(self.db_path) as db:
            result = await func(db)
            await db.commit()
            return result

    async def save_record(
        self, record: Record, pipeline_id: int | None = None, job_id: int | None = None
    ) -> int:
        now = datetime.now()

        async def _save(db: Connection) -> int:
            cursor = await db.execute(
                """
                INSERT INTO records (
                    output, metadata, status, pipeline_id, job_id, trace,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.output or "",
                    json.dumps(record.metadata),
                    record.status.value,
                    pipeline_id,
                    job_id,
                    json.dumps(record.trace) if record.trace else None,
                    now,
                    now,
                ),
            )
            return cursor.lastrowid if cursor.lastrowid is not None else 0

        return await self._execute_with_connection(_save)

    async def get_all(
        self,
        status: RecordStatus | None = None,
        limit: int = 100,
        offset: int = 0,
        job_id: int | None = None,
        pipeline_id: int | None = None,
    ) -> list[Record]:
        async def _get_all(db: Connection) -> list[Record]:
            db.row_factory = aiosqlite.Row

            # build query with filters
            where_clauses = []
            params: list[str | int] = []

            if status:
                where_clauses.append("status = ?")
                params.append(status.value)

            if job_id:
                where_clauses.append("job_id = ?")
                params.append(job_id)

            if pipeline_id:
                where_clauses.append("pipeline_id = ?")
                params.append(pipeline_id)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            params.extend([limit, offset])

            cursor = await db.execute(
                f"""
                SELECT * FROM records
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params,
            )
            rows = await cursor.fetchall()
            return [self._row_to_record(row) for row in rows]

        return await self._execute_with_connection(_get_all)

    async def get_by_id(self, record_id: int) -> Record | None:
        async def _get(db: Connection) -> Record | None:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM records WHERE id = ?", (record_id,))
            row = await cursor.fetchone()
            return self._row_to_record(row) if row else None

        return await self._execute_with_connection(_get)

    async def update_record(self, record_id: int, **updates: str | RecordStatus) -> bool:
        if not updates:
            return False

        valid_fields = {"output", "status", "metadata"}
        update_fields: dict[str, Any] = {k: v for k, v in updates.items() if k in valid_fields}

        if not update_fields:
            return False

        if "status" in update_fields and isinstance(update_fields["status"], RecordStatus):
            update_fields["status"] = update_fields["status"].value

        if "metadata" in update_fields:
            update_fields["metadata"] = json.dumps(update_fields["metadata"])

        update_fields["updated_at"] = datetime.now()

        set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values: list[Any] = list(update_fields.values()) + [record_id]

        async def _update(db: Connection) -> bool:
            cursor = await db.execute(f"UPDATE records SET {set_clause} WHERE id = ?", values)
            return cursor.rowcount > 0

        return await self._execute_with_connection(_update)

    async def update_record_accumulated_state(
        self,
        record_id: int,
        accumulated_state_updates: dict[str, Any],
        **standard_updates: Any,
    ) -> bool:
        # first get the record to access its trace
        record = await self.get_by_id(record_id)
        if not record or not record.trace:
            return False

        # update the last step's accumulated_state in the trace
        trace = record.trace
        if trace and len(trace) > 0:
            last_step = trace[-1]
            if "accumulated_state" in last_step:
                # update the accumulated_state with new values
                last_step["accumulated_state"].update(accumulated_state_updates)

        # prepare updates including the modified trace
        update_fields: dict[str, Any] = {}

        # add standard field updates
        valid_fields = {"output", "status", "metadata"}
        for k, v in standard_updates.items():
            if k in valid_fields:
                update_fields[k] = v

        # add the updated trace
        update_fields["trace"] = json.dumps(trace)
        update_fields["updated_at"] = datetime.now()

        if "status" in update_fields and isinstance(update_fields["status"], RecordStatus):
            update_fields["status"] = update_fields["status"].value

        if "metadata" in update_fields:
            update_fields["metadata"] = json.dumps(update_fields["metadata"])

        set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values: list[Any] = list(update_fields.values()) + [record_id]

        async def _update(db: Connection) -> bool:
            cursor = await db.execute(f"UPDATE records SET {set_clause} WHERE id = ?", values)
            return cursor.rowcount > 0

        return await self._execute_with_connection(_update)

    async def delete_all_records(self, job_id: int | None = None) -> int:
        async def _delete(db: Connection) -> int:
            if job_id:
                await db.execute("BEGIN")
                try:
                    cursor = await db.execute("DELETE FROM records WHERE job_id = ?", (job_id,))
                    count = cursor.rowcount
                    await db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
                    await db.execute("COMMIT")
                    return count
                except Exception:
                    logger.exception(
                        f"transaction failed during delete_all_records for job_id={job_id}"
                    )
                    await db.execute("ROLLBACK")
                    raise
            else:
                cursor = await db.execute("DELETE FROM records")
                return cursor.rowcount

        return await self._execute_with_connection(_delete)

    async def export_jsonl(
        self, status: RecordStatus | None = None, job_id: int | None = None
    ) -> str:
        records = await self.get_all(status=status, limit=999999, job_id=job_id)
        lines = []
        for record in records:
            # extract accumulated_state from the last trace entry
            accumulated_state = {}
            if record.trace and len(record.trace) > 0:
                full_state = record.trace[-1].get("accumulated_state", {})
                # exclude metadata keys to avoid duplication
                accumulated_state = {
                    k: v for k, v in full_state.items() if k not in record.metadata
                }

            obj = {
                "id": record.id,
                "metadata": record.metadata,
                "status": record.status.value,
                "accumulated_state": accumulated_state,
                "created_at": (record.created_at.isoformat() if record.created_at else None),
                "updated_at": (record.updated_at.isoformat() if record.updated_at else None),
            }
            lines.append(json.dumps(obj))
        return "\n".join(lines)

    async def save_pipeline(self, name: str, definition: dict[str, Any]) -> int:
        now = datetime.now()

        async def _save(db: Connection) -> int:
            cursor = await db.execute(
                "INSERT INTO pipelines (name, definition, created_at) VALUES (?, ?, ?)",
                (name, json.dumps(definition), now),
            )
            return cursor.lastrowid if cursor.lastrowid is not None else 0

        return await self._execute_with_connection(_save)

    async def get_pipeline(self, pipeline_id: int) -> dict[str, Any] | None:
        async def _get(db: Connection) -> dict[str, Any] | None:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM pipelines WHERE id = ?", (pipeline_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "name": row["name"],
                "definition": json.loads(row["definition"]),
                "created_at": row["created_at"],
                "validation_config": (
                    json.loads(row["validation_config"]) if row["validation_config"] else None
                ),
            }

        return await self._execute_with_connection(_get)

    async def list_pipelines(self) -> list[dict[str, Any]]:
        async def _list(db: Connection) -> list[dict[str, Any]]:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM pipelines ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "definition": json.loads(row["definition"]),
                    "created_at": row["created_at"],
                    "validation_config": (
                        json.loads(row["validation_config"]) if row["validation_config"] else None
                    ),
                }
                for row in rows
            ]

        return await self._execute_with_connection(_list)

    async def update_pipeline(
        self, pipeline_id: int, name: str, definition: dict[str, Any]
    ) -> bool:
        async def _update(db: Connection) -> bool:
            cursor = await db.execute(
                "UPDATE pipelines SET name = ?, definition = ? WHERE id = ?",
                (name, json.dumps(definition), pipeline_id),
            )
            return cursor.rowcount > 0

        return await self._execute_with_connection(_update)

    async def update_pipeline_validation_config(
        self, pipeline_id: int, validation_config: dict[str, Any]
    ) -> bool:
        async def _update(db: Connection) -> bool:
            cursor = await db.execute(
                "UPDATE pipelines SET validation_config = ? WHERE id = ?",
                (json.dumps(validation_config), pipeline_id),
            )
            return cursor.rowcount > 0

        return await self._execute_with_connection(_update)

    async def delete_pipeline(self, pipeline_id: int) -> bool:
        async def _delete(db: Connection) -> bool:
            await db.execute("BEGIN")
            try:
                # cascade delete: records -> jobs -> pipeline
                await db.execute("DELETE FROM records WHERE pipeline_id = ?", (pipeline_id,))
                await db.execute("DELETE FROM jobs WHERE pipeline_id = ?", (pipeline_id,))
                cursor = await db.execute("DELETE FROM pipelines WHERE id = ?", (pipeline_id,))
                await db.execute("COMMIT")
                return cursor.rowcount > 0
            except Exception:
                logger.exception(
                    f"transaction failed during delete_pipeline for pipeline_id={pipeline_id}"
                )
                await db.execute("ROLLBACK")
                raise

        return await self._execute_with_connection(_delete)

    async def create_job(self, pipeline_id: int, total_seeds: int, status: str = "running") -> int:
        now = datetime.now()

        async def _create(db: Connection) -> int:
            sql = (
                "INSERT INTO jobs (pipeline_id, status, total_seeds, started_at, created_at) "
                "VALUES (?, ?, ?, ?, ?)"
            )
            cursor = await db.execute(sql, (pipeline_id, status, total_seeds, now, now))
            return cursor.lastrowid if cursor.lastrowid is not None else 0

        return await self._execute_with_connection(_create)

    async def get_job(self, job_id: int) -> dict[str, Any] | None:
        async def _get(db: Connection) -> dict[str, Any] | None:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = await cursor.fetchone()
            if not row:
                return None

            # handle columns that might not exist in older databases
            row_dict = dict(row)
            return {
                "id": row_dict["id"],
                "pipeline_id": row_dict["pipeline_id"],
                "status": row_dict["status"],
                "total_seeds": row_dict["total_seeds"],
                "current_seed": row_dict.get("current_seed", 0),
                "records_generated": row_dict["records_generated"],
                "records_failed": row_dict["records_failed"],
                "progress": row_dict.get("progress", 0.0),
                "current_block": row_dict.get("current_block"),
                "current_step": row_dict.get("current_step"),
                "error": row_dict.get("error"),
                "started_at": row_dict["started_at"],
                "completed_at": row_dict["completed_at"],
                "created_at": row_dict.get("created_at"),
            }

        return await self._execute_with_connection(_get)

    async def list_jobs(
        self, pipeline_id: int | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        async def _list(db: Connection) -> list[dict[str, Any]]:
            db.row_factory = aiosqlite.Row
            if pipeline_id:
                cursor = await db.execute(
                    "SELECT * FROM jobs WHERE pipeline_id = ? ORDER BY started_at DESC LIMIT ?",
                    (pipeline_id, limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM jobs ORDER BY started_at DESC LIMIT ?",
                    (limit,),
                )
            rows = await cursor.fetchall()

            # convert rows to dicts to use .get() method
            result = []
            for row in rows:
                row_dict = dict(row)
                result.append(
                    {
                        "id": row_dict["id"],
                        "pipeline_id": row_dict["pipeline_id"],
                        "status": row_dict["status"],
                        "total_seeds": row_dict["total_seeds"],
                        "current_seed": row_dict.get("current_seed", 0),
                        "records_generated": row_dict["records_generated"],
                        "records_failed": row_dict["records_failed"],
                        "progress": row_dict.get("progress", 0.0),
                        "current_block": row_dict.get("current_block"),
                        "current_step": row_dict.get("current_step"),
                        "error": row_dict.get("error"),
                        "started_at": row_dict["started_at"],
                        "completed_at": row_dict["completed_at"],
                        "created_at": row_dict.get("created_at"),
                    }
                )
            return result

        return await self._execute_with_connection(_list)

    async def update_job(self, job_id: int, **updates: Any) -> bool:
        if not updates:
            return False

        # filter to only valid database fields for jobs table
        valid_fields = {
            "status",
            "total_seeds",
            "current_seed",
            "records_generated",
            "records_failed",
            "progress",
            "current_block",
            "current_step",
            "error",
            "completed_at",
        }
        update_fields = {k: v for k, v in updates.items() if k in valid_fields}

        if not update_fields:
            return True  # no database fields to update, but not an error

        set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values: list[Any] = list(update_fields.values()) + [job_id]

        async def _update(db: Connection) -> bool:
            cursor = await db.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
            return cursor.rowcount > 0

        return await self._execute_with_connection(_update)

    async def close(self) -> None:
        """close the database connection if one is open"""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def list_llm_models(self) -> list[dict[str, Any]]:
        """list all configured llm models"""

        async def _list(db: Connection) -> list[dict[str, Any]]:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM llm_models")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

        return await self._execute_with_connection(_list)

    async def get_llm_model(self, name: str) -> dict[str, Any] | None:
        """get llm model config by name"""

        async def _get(db: Connection) -> dict[str, Any] | None:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM llm_models WHERE name = ?", (name,))
            row = await cursor.fetchone()
            return dict(row) if row else None

        return await self._execute_with_connection(_get)

    async def save_llm_model(self, config: dict[str, Any]) -> None:
        """create or update llm model config (upsert)"""

        async def _save(db: Connection) -> None:
            await db.execute(
                """
                INSERT INTO llm_models (name, provider, endpoint, api_key, model_name)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    provider = excluded.provider,
                    endpoint = excluded.endpoint,
                    api_key = excluded.api_key,
                    model_name = excluded.model_name
                """,
                (
                    config["name"],
                    config["provider"],
                    config["endpoint"],
                    config.get("api_key"),
                    config["model_name"],
                ),
            )

        await self._execute_with_connection(_save)

    async def delete_llm_model(self, name: str) -> bool:
        """delete llm model config"""

        async def _delete(db: Connection) -> bool:
            cursor = await db.execute("DELETE FROM llm_models WHERE name = ?", (name,))
            return cursor.rowcount > 0

        return await self._execute_with_connection(_delete)

    async def list_embedding_models(self) -> list[dict[str, Any]]:
        """list all configured embedding models"""

        async def _list(db: Connection) -> list[dict[str, Any]]:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM embedding_models")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

        return await self._execute_with_connection(_list)

    async def get_embedding_model(self, name: str) -> dict[str, Any] | None:
        """get embedding model config by name"""

        async def _get(db: Connection) -> dict[str, Any] | None:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM embedding_models WHERE name = ?", (name,))
            row = await cursor.fetchone()
            return dict(row) if row else None

        return await self._execute_with_connection(_get)

    async def save_embedding_model(self, config: dict[str, Any]) -> None:
        """create or update embedding model config (upsert)"""

        async def _save(db: Connection) -> None:
            await db.execute(
                """
                INSERT INTO embedding_models
                    (name, provider, endpoint, api_key, model_name, dimensions)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    provider = excluded.provider,
                    endpoint = excluded.endpoint,
                    api_key = excluded.api_key,
                    model_name = excluded.model_name,
                    dimensions = excluded.dimensions
                """,
                (
                    config["name"],
                    config["provider"],
                    config["endpoint"],
                    config.get("api_key"),
                    config["model_name"],
                    config.get("dimensions"),
                ),
            )

        await self._execute_with_connection(_save)

    async def delete_embedding_model(self, name: str) -> bool:
        """delete embedding model config"""

        async def _delete(db: Connection) -> bool:
            cursor = await db.execute("DELETE FROM embedding_models WHERE name = ?", (name,))
            return cursor.rowcount > 0

        return await self._execute_with_connection(_delete)

    def _row_to_record(self, row: aiosqlite.Row) -> Record:
        return Record(
            id=row["id"],
            output=row["output"],
            metadata=json.loads(row["metadata"]),
            status=RecordStatus(row["status"]),
            trace=json.loads(row["trace"]) if row["trace"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
