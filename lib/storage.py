import json
from datetime import datetime

import aiosqlite

from config import settings
from models import Record, RecordStatus


class Storage:
    def __init__(self, db_path: str = settings.DATABASE_PATH) -> None:
        self.db_path = db_path

    async def init_db(self) -> None:
        # only ensure data dir if not using in-memory database
        if self.db_path != ":memory:":
            settings.ensure_data_dir()
        async with aiosqlite.connect(self.db_path) as db:
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
            await db.commit()

    async def save_record(self, record: Record, pipeline_id: int | None = None) -> int:
        now = datetime.now()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO records (system, user, assistant, metadata, status, pipeline_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.system,
                    record.user,
                    record.assistant,
                    json.dumps(record.metadata),
                    record.status.value,
                    pipeline_id,
                    now,
                    now,
                ),
            )
            await db.commit()
            return cursor.lastrowid or 0

    async def get_all(
        self, status: RecordStatus | None = None, limit: int = 100, offset: int = 0
    ) -> list[Record]:
        async with aiosqlite.connect(self.db_path) as db:
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

    async def get_by_id(self, record_id: int) -> Record | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM records WHERE id = ?", (record_id,))
            row = await cursor.fetchone()
            return self._row_to_record(row) if row else None

    async def update_record(self, record_id: int, **updates: str | RecordStatus) -> bool:
        if not updates:
            return False

        valid_fields = {"system", "user", "assistant", "status", "metadata"}
        update_fields = {k: v for k, v in updates.items() if k in valid_fields}

        if not update_fields:
            return False

        if "status" in update_fields and isinstance(update_fields["status"], RecordStatus):
            update_fields["status"] = update_fields["status"].value

        if "metadata" in update_fields:
            update_fields["metadata"] = json.dumps(update_fields["metadata"])

        update_fields["updated_at"] = datetime.now()

        set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values = list(update_fields.values()) + [record_id]

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"UPDATE records SET {set_clause} WHERE id = ?", values
            )
            await db.commit()
            return cursor.rowcount > 0

    async def export_jsonl(self, status: RecordStatus | None = None) -> str:
        records = await self.get_all(status=status, limit=999999)
        lines = []
        for record in records:
            obj = {
                "id": record.id,
                "system": record.system,
                "user": record.user,
                "assistant": record.assistant,
                "metadata": record.metadata,
                "status": record.status.value,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            }
            lines.append(json.dumps(obj))
        return "\n".join(lines)

    async def save_pipeline(self, name: str, definition: dict) -> int:
        now = datetime.now()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO pipelines (name, definition, created_at) VALUES (?, ?, ?)",
                (name, json.dumps(definition), now),
            )
            await db.commit()
            return cursor.lastrowid or 0

    async def get_pipeline(self, pipeline_id: int) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
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

    async def list_pipelines(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
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

    async def delete_pipeline(self, pipeline_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM pipelines WHERE id = ?", (pipeline_id,))
            await db.commit()
            return cursor.rowcount > 0

    def _row_to_record(self, row: aiosqlite.Row) -> Record:
        return Record(
            id=row["id"],
            system=row["system"],
            user=row["user"],
            assistant=row["assistant"],
            metadata=json.loads(row["metadata"]),
            status=RecordStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
