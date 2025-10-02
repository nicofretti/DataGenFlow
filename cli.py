import argparse
import asyncio
import sys

from loguru import logger

from lib.pipeline import Pipeline
from lib.storage import Storage
from models import GenerationConfig, RecordStatus

logger.remove()
logger.add(sys.stderr, format="<level>{message}</level>", level="INFO")


async def generate(args: argparse.Namespace) -> None:
    logger.info("initializing database...")
    storage = Storage()
    await storage.init_db()

    config = GenerationConfig(
        model=args.model,
        endpoint=args.endpoint,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    logger.info(f"processing seed file: {args.file}")
    pipeline = Pipeline(storage)
    result = await pipeline.process_seed_file(args.file, config)

    logger.success(
        f"generation complete: {result['success']} success, {result['failed']} failed, {result['total']} total"
    )


async def list_records(args: argparse.Namespace) -> None:
    storage = Storage()
    await storage.init_db()

    status = RecordStatus(args.status) if args.status else None
    records = await storage.get_all(status=status, limit=args.limit, offset=args.offset)

    print(f"found {len(records)} records\n")
    for r in records:
        print(f"[{r.id}] {r.status.value}")
        print(f"system: {r.system}")
        print(f"user: {r.user}")
        print(f"assistant: {r.assistant[:100]}...")
        print()


async def update_status(args: argparse.Namespace) -> None:
    storage = Storage()
    await storage.init_db()

    status = RecordStatus(args.status)
    success = await storage.update_record(args.id, status=status)

    if success:
        print(f"record {args.id} updated to {status.value}")
    else:
        print(f"record {args.id} not found")


async def export_records(args: argparse.Namespace) -> None:
    storage = Storage()
    await storage.init_db()

    status = RecordStatus(args.status) if args.status else None
    jsonl = await storage.export_jsonl(status=status)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(jsonl)

    count = len(jsonl.split("\n")) if jsonl else 0
    print(f"exported {count} records to {args.output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="QADataGen CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate command
    gen_parser = subparsers.add_parser("generate", help="generate records from seed file")
    gen_parser.add_argument("file", help="seed json file")
    gen_parser.add_argument("--model", help="llm model name")
    gen_parser.add_argument("--endpoint", help="llm endpoint url")
    gen_parser.add_argument("--temperature", type=float, default=0.7, help="temperature")
    gen_parser.add_argument("--max-tokens", type=int, help="max tokens")
    gen_parser.set_defaults(func=generate)

    # list command
    list_parser = subparsers.add_parser("list", help="list records")
    list_parser.add_argument("--status", choices=["pending", "accepted", "rejected", "edited"])
    list_parser.add_argument("--limit", type=int, default=10, help="max records to show")
    list_parser.add_argument("--offset", type=int, default=0, help="offset")
    list_parser.set_defaults(func=list_records)

    # update command
    update_parser = subparsers.add_parser("update", help="update record status")
    update_parser.add_argument("id", type=int, help="record id")
    update_parser.add_argument("status", choices=["accepted", "rejected", "edited"])
    update_parser.set_defaults(func=update_status)

    # export command
    export_parser = subparsers.add_parser("export", help="export records to jsonl")
    export_parser.add_argument("output", help="output file path")
    export_parser.add_argument(
        "--status", choices=["pending", "accepted", "rejected", "edited"]
    )
    export_parser.set_defaults(func=export_records)

    args = parser.parse_args()

    try:
        asyncio.run(args.func(args))
    except Exception as e:
        logger.error(f"error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
