import json
from datetime import datetime

import aiosqlite

from config import settings
from models import Record, RecordStatus


class Storage:
    def __init__(self, db_path: str = settings.DATABASE_PATH) -> None:
        self.db_path = db_path

    async def init_db(self) -> None:
        settings.ensure_data_dir()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system TEXT NOT NULL,
                    user TEXT NOT NULL,
                    assistant TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON records(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON records(created_at)
            """)
            await db.commit()

    async def save_record(self, record: Record) -> int:
        now = datetime.now()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO records (system, user, assistant, metadata, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.system,
                    record.user,
                    record.assistant,
                    json.dumps(record.metadata),
                    record.status.value,
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
