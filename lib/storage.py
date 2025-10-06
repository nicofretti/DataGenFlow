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

    async def _execute_with_connection(self, func):
        # helper to execute with appropriate connection handling
        if self._conn:
            return await func(self._conn)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                return await func(db)

    async def save_record(self, record: Record, pipeline_id: int | None = None) -> int:
        now = datetime.now()

        async def _save(db):
            cursor = await db.execute(
                """
                INSERT INTO records (system, user, assistant, metadata, status, pipeline_id, trace, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.system,
                    record.user,
                    record.assistant,
                    json.dumps(record.metadata),
                    record.status.value,
                    pipeline_id,
                    json.dumps(record.trace) if record.trace else None,
                    now,
                    now,
                ),
            )
            await db.commit()
            return cursor.lastrowid or 0

        return await self._execute_with_connection(_save)

    async def get_all(
        self, status: RecordStatus | None = None, limit: int = 100, offset: int = 0
    ) -> list[Record]:
        async def _get_all(db):
            db.row_factory = aiosqlite.Row
            if status:
                cursor = await db.execute(
                    """
                    SELECT * FROM records
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (status.value, limit, offset),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM records
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
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
