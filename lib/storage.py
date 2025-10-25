import json
from datetime import datetime
from typing import Any, Callable

import aiosqlite
from aiosqlite import Connection

from config import settings
from models import Record, RecordStatus


class Storage:
    def __init__(self, db_path: str = settings.DATABASE_PATH) -> None:
        self.db_path = db_path
        self._conn: Connection | None = None  # persistent connection for :memory:

    async def init_db(self) -> None:
        # only ensure data dir if not using in-memory database
        if self.db_path != ":memory:":
            settings.ensure_data_dir()

        # for :memory: db, keep connection open
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
                    records_generated INTEGER DEFAULT 0,
                    records_failed INTEGER DEFAULT 0,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
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

            # migrate existing tables
            await self._migrate_schema(db)

            await db.commit()
        finally:
            # only close if not using persistent connection
            if self.db_path != ":memory:":
                await db.close()

    async def _migrate_schema(self, db: Connection) -> None:
        # check if pipeline_id column exists in records
        cursor = await db.execute("PRAGMA table_info(records)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        # add pipeline_id if missing
        if "pipeline_id" not in column_names:
            await db.execute("ALTER TABLE records ADD COLUMN pipeline_id INTEGER")

        # add job_id if missing
        if "job_id" not in column_names:
            await db.execute("ALTER TABLE records ADD COLUMN job_id INTEGER")

        # add trace if missing
        if "trace" not in column_names:
            await db.execute("ALTER TABLE records ADD COLUMN trace TEXT")

        # check if validation_config column exists in pipelines
        cursor = await db.execute("PRAGMA table_info(pipelines)")
        pipeline_columns = await cursor.fetchall()
        pipeline_column_names = [col[1] for col in pipeline_columns]

        # add validation_config if missing
        if "validation_config" not in pipeline_column_names:
            await db.execute("ALTER TABLE pipelines ADD COLUMN validation_config TEXT")

    async def _execute_with_connection(self, func: Callable[[Connection], Any]) -> Any:
        # helper to execute with appropriate connection handling
        if self._conn:
            return await func(self._conn)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                return await func(db)

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
            await db.commit()
            return cursor.lastrowid if cursor.lastrowid is not None else 0

        return await self._execute_with_connection(_save)

    async def get_all(
        self,
        status: RecordStatus | None = None,
        limit: int = 100,
        offset: int = 0,
        job_id: int | None = None,
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
            await db.commit()
            return cursor.rowcount > 0

        return await self._execute_with_connection(_update)

    async def delete_all_records(self, job_id: int | None = None) -> int:
        async def _delete(db: Connection) -> int:
            if job_id:
                cursor = await db.execute("DELETE FROM records WHERE job_id = ?", (job_id,))
                count = cursor.rowcount
                # also delete the job
                await db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
                await db.commit()
                return count
            else:
                cursor = await db.execute("DELETE FROM records")
                await db.commit()
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
            await db.commit()
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
            await db.commit()
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
            await db.commit()
            return cursor.rowcount > 0

        return await self._execute_with_connection(_update)

    async def delete_pipeline(self, pipeline_id: int) -> bool:
        async def _delete(db: Connection) -> bool:
            # cascade delete: records -> jobs -> pipeline
            # delete all records for this pipeline
            await db.execute("DELETE FROM records WHERE pipeline_id = ?", (pipeline_id,))

            # delete all jobs for this pipeline
            await db.execute("DELETE FROM jobs WHERE pipeline_id = ?", (pipeline_id,))

            # delete the pipeline
            cursor = await db.execute("DELETE FROM pipelines WHERE id = ?", (pipeline_id,))
            await db.commit()
            return cursor.rowcount > 0

        return await self._execute_with_connection(_delete)

    async def create_job(self, pipeline_id: int, total_seeds: int, status: str = "running") -> int:
        now = datetime.now()

        async def _create(db: Connection) -> int:
            sql = (
                "INSERT INTO jobs (pipeline_id, status, total_seeds, started_at) "
                "VALUES (?, ?, ?, ?)"
            )
            cursor = await db.execute(sql, (pipeline_id, status, total_seeds, now))
            await db.commit()
            return cursor.lastrowid if cursor.lastrowid is not None else 0

        return await self._execute_with_connection(_create)

    async def get_job(self, job_id: int) -> dict[str, Any] | None:
        async def _get(db: Connection) -> dict[str, Any] | None:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "pipeline_id": row["pipeline_id"],
                "status": row["status"],
                "total_seeds": row["total_seeds"],
                "records_generated": row["records_generated"],
                "records_failed": row["records_failed"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
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
            return [
                {
                    "id": row["id"],
                    "pipeline_id": row["pipeline_id"],
                    "status": row["status"],
                    "total_seeds": row["total_seeds"],
                    "records_generated": row["records_generated"],
                    "records_failed": row["records_failed"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                }
                for row in rows
            ]

        return await self._execute_with_connection(_list)

    async def update_job(self, job_id: int, **updates: Any) -> bool:
        if not updates:
            return False

        # filter to only valid database fields for jobs table
        valid_fields = {"status", "records_generated", "records_failed", "completed_at"}
        update_fields = {k: v for k, v in updates.items() if k in valid_fields}

        if not update_fields:
            return True  # no database fields to update, but not an error

        set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values: list[Any] = list(update_fields.values()) + [job_id]

        async def _update(db: Connection) -> bool:
            cursor = await db.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)
            await db.commit()
            return cursor.rowcount > 0

        return await self._execute_with_connection(_update)

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
