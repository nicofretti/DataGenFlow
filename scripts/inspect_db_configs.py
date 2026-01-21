#!/usr/bin/env python3
"""Inspect LLM and embedding configurations in database"""

import asyncio
import sys
from pathlib import Path

# add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite

from lib.storage import Storage


async def main():
    storage = Storage("data/qa_records.db")
    try:
        await storage.init_db()

        # get LLM models
        print("=== LLM Models ===")
        llm_models = []

        async def get_llm_models(db):
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM llm_models")
            return await cursor.fetchall()

        llm_rows = await storage._execute_with_connection(get_llm_models)
        for row in llm_rows:
            model_dict = {key: row[key] for key in row.keys()}
            print(model_dict)
            llm_models.append(model_dict)

        print("\n=== Embedding Models ===")
        embedding_models = []

        async def get_embedding_models(db):
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM embedding_models")
            return await cursor.fetchall()

        emb_rows = await storage._execute_with_connection(get_embedding_models)
        for row in emb_rows:
            model_dict = {key: row[key] for key in row.keys()}
            print(model_dict)
            embedding_models.append(model_dict)

        return llm_models, embedding_models
    finally:
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
