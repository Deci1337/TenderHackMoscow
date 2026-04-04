"""Check DB status after data load."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "backend")

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.config import settings


async def query(s, sql):
    try:
        return (await s.execute(text(sql))).scalar()
    except Exception as e:
        await s.rollback()
        return f"ERROR: {e}"


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession)

    async with Session() as s:
        print("STE total:         ", await query(s, "SELECT COUNT(*) FROM ste"))
    async with Session() as s:
        print("STE with tsvector: ", await query(s, "SELECT COUNT(*) FROM ste WHERE name_tsv IS NOT NULL"))
    async with Session() as s:
        print("Contracts:         ", await query(s, "SELECT COUNT(*) FROM contracts"))
    async with Session() as s:
        tables = [r[0] for r in (await s.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )))]
        print("Tables:", tables)
    async with Session() as s:
        indexes = [r[0] for r in (await s.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename='ste' ORDER BY indexname"
        )))]
        print("STE indexes:", indexes)

    await engine.dispose()


asyncio.run(main())
