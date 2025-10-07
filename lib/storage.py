import json
from datetime import datetime

import aiosqlite

from config import settings
from models import Record, RecordStatus, RecordUpdate


class Storage:
    def __init__(self, db_path: str = settings.DATABASE_PATH) -> None:
        self.db_path = db_path
        self._conn = None  # persistent connection for :memory:

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
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pipelines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    definition TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system TEXT NOT NULL,
                    user TEXT NOT NULL,
                    assistant TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    status TEXT NOT NULL,
                    pipeline_id INTEGER,
                    trace TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pipeline_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL DEFAULT 0.0,
                    current_seed INTEGER DEFAULT 0,
                    total_seeds INTEGER NOT NULL,
                    current_block TEXT,
                    current_step TEXT,
                    records_generated INTEGER DEFAULT 0,
                    records_failed INTEGER DEFAULT 0,
                    error TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON records(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON records(created_at)
            """)

            # migrate existing tables
            await self._migrate_schema(db)

            await db.commit()
        finally:
            # only close if not using persistent connection
            if self.db_path != ":memory:":
                await db.close()

    async def _migrate_schema(self, db) -> None:
        # check if pipeline_id column exists
        cursor = await db.execute("PRAGMA table_info(records)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        # add pipeline_id if missing
        if "pipeline_id" not in column_names:
            await db.execute("ALTER TABLE records ADD COLUMN pipeline_id INTEGER")

        # add trace if missing
        if "trace" not in column_names:
            await db.execute("ALTER TABLE records ADD COLUMN trace TEXT")

        # add job_id if missing
        if "job_id" not in column_names:
            await db.execute("ALTER TABLE records ADD COLUMN job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL")

    async def _execute_with_connection(self, func):
        # helper to execute with appropriate connection handling
        if self._conn:
            return await func(self._conn)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                return await func(db)

    async def save_record(self, record: Record, pipeline_id: int | None = None, job_id: int | None = None) -> int:
        now = datetime.now()

        async def _save(db):
            cursor = await db.execute(
                """
                INSERT INTO records (system, user, assistant, metadata, status, pipeline_id, job_id, trace, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.system,
                    record.user,
                    record.assistant,
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
            return cursor.lastrowid or 0

        return await self._execute_with_connection(_save)

    async def get_all(
        self, status: RecordStatus | None = None, limit: int = 100, offset: int = 0, job_id: int | None = None
    ) -> list[Record]:
        async def _get_all(db):
            db.row_factory = aiosqlite.Row
            conditions = []
            params = []

            if status:
                conditions.append("status = ?")
                params.append(status.value)

            if job_id:
                conditions.append("job_id = ?")
                params.append(job_id)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            params.extend([limit, offset])

            cursor = await db.execute(
                f"""
                SELECT * FROM records
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params,
            )
            rows = await cursor.fetchall()
            return [self._row_to_record(row) for row in rows]

        return await self._execute_with_connection(_get_all)

    async def get_by_id(self, record_id: int) -> Record | None:
        async def _get(db):
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM records WHERE id = ?", (record_id,))
            row = await cursor.fetchone()
            return self._row_to_record(row) if row else None

        return await self._execute_with_connection(_get)

    async def update_record(
        self, record_id: int, updates: RecordUpdate | None = None, **kwargs
    ) -> bool:
        # handle both RecordUpdate object and kwargs
        if updates:
            update_dict = {
                k: v for k, v in updates.model_dump().items() if v is not None
            }
        else:
            update_dict = kwargs

        if not update_dict:
            return False

        valid_fields = {"system", "user", "assistant", "status", "metadata"}
        update_fields = {k: v for k, v in update_dict.items() if k in valid_fields}

        if not update_fields:
            return False

        if "status" in update_fields and isinstance(update_fields["status"], RecordStatus):
            update_fields["status"] = update_fields["status"].value

        if "metadata" in update_fields:
            update_fields["metadata"] = json.dumps(update_fields["metadata"])

        update_fields["updated_at"] = datetime.now()

        set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values = list(update_fields.values()) + [record_id]

        async def _update(db):
            cursor = await db.execute(
                f"UPDATE records SET {set_clause} WHERE id = ?", values
            )
            await db.commit()
            return cursor.rowcount > 0

        return await self._execute_with_connection(_update)

    async def delete_record(self, record_id: int) -> bool:
        async def _delete(db):
            cursor = await db.execute("DELETE FROM records WHERE id = ?", (record_id,))
            await db.commit()
            return cursor.rowcount > 0

        return await self._execute_with_connection(_delete)

    async def delete_all_records(self) -> int:
        async def _delete(db):
            cursor = await db.execute("DELETE FROM records")
            await db.commit()
            return cursor.rowcount

        return await self._execute_with_connection(_delete)

    async def count_records(self, status: RecordStatus | None = None) -> int:
        async def _count(db):
            if status:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM records WHERE status = ?", (status.value,)
                )
            else:
                cursor = await db.execute("SELECT COUNT(*) FROM records")
            result = await cursor.fetchone()
            return result[0] if result else 0

        return await self._execute_with_connection(_count)

    async def export_jsonl(self, status: RecordStatus | None = None) -> str:
        records = await self.get_all(status=status, limit=999999)
        lines = []
        for record in records:
            # get pipeline_output from accumulated state if trace exists
            pipeline_output = None
            if record.trace and len(record.trace) > 0:
                final_state = record.trace[-1].get("accumulated_state", {})
                pipeline_output = final_state.get("pipeline_output")

            obj = {
                "id": record.id,
                "system": record.system,
                "user": record.user,
                "assistant": record.assistant,
                "pipeline_output": pipeline_output,
                "metadata": record.metadata,
                "status": record.status.value,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            }
            lines.append(json.dumps(obj))
        return "\n".join(lines)

    async def save_pipeline(self, name: str, definition: dict) -> int:
        now = datetime.now()

        async def _save(db):
            cursor = await db.execute(
                "INSERT INTO pipelines (name, definition, created_at) VALUES (?, ?, ?)",
                (name, json.dumps(definition), now),
            )
            await db.commit()
            return cursor.lastrowid or 0

        return await self._execute_with_connection(_save)

    async def get_pipeline(self, pipeline_id: int) -> dict | None:
        async def _get(db):
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
            }

        return await self._execute_with_connection(_get)

    async def list_pipelines(self) -> list[dict]:
        async def _list(db):
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM pipelines ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "definition": json.loads(row["definition"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        return await self._execute_with_connection(_list)

    async def delete_pipeline(self, pipeline_id: int) -> bool:
        async def _delete(db):
            cursor = await db.execute("DELETE FROM pipelines WHERE id = ?", (pipeline_id,))
            await db.commit()
            return cursor.rowcount > 0

        return await self._execute_with_connection(_delete)

    async def create_job(
        self, pipeline_id: int, total_seeds: int, status: str = "running"
    ) -> int:
        now = datetime.now().isoformat()

        async def _create(db):
            cursor = await db.execute(
                """
                INSERT INTO jobs (pipeline_id, status, total_seeds, started_at)
                VALUES (?, ?, ?, ?)
                """,
                (pipeline_id, status, total_seeds, now),
            )
            await db.commit()
            return cursor.lastrowid or 0

        return await self._execute_with_connection(_create)

    async def get_job(self, job_id: int) -> dict | None:
        async def _get(db):
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return dict(row)

        return await self._execute_with_connection(_get)

    async def update_job(self, job_id: int, **updates) -> bool:
        if not updates:
            return False

        valid_fields = {
            "status",
            "progress",
            "current_seed",
            "current_block",
            "current_step",
            "records_generated",
            "records_failed",
            "error",
            "completed_at",
        }
        update_fields = {k: v for k, v in updates.items() if k in valid_fields}

        if not update_fields:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values = list(update_fields.values()) + [job_id]

        async def _update(db):
            cursor = await db.execute(
                f"UPDATE jobs SET {set_clause} WHERE id = ?", values
            )
            await db.commit()
            return cursor.rowcount > 0

        return await self._execute_with_connection(_update)

    async def list_jobs(self, pipeline_id: int | None = None, limit: int = 10) -> list[dict]:
        async def _list(db):
            db.row_factory = aiosqlite.Row
            if pipeline_id:
                cursor = await db.execute(
                    "SELECT * FROM jobs WHERE pipeline_id = ? ORDER BY started_at DESC LIMIT ?",
                    (pipeline_id, limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM jobs ORDER BY started_at DESC LIMIT ?", (limit,)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

        return await self._execute_with_connection(_list)

    async def delete_job(self, job_id: int) -> bool:
        async def _delete(db):
            cursor = await db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            await db.commit()
            return cursor.rowcount > 0

        return await self._execute_with_connection(_delete)

    def _row_to_record(self, row: aiosqlite.Row) -> Record:
        return Record(
            id=row["id"],
            system=row["system"],
            user=row["user"],
            assistant=row["assistant"],
            metadata=json.loads(row["metadata"]),
            status=RecordStatus(row["status"]),
            trace=json.loads(row["trace"]) if row["trace"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
