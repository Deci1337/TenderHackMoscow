"""Rebuild tsvector and popularity indexes for real data."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "backend")

import asyncio, time, logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_timeout=600)
    Session = async_sessionmaker(engine, class_=AsyncSession)

    log.info("Updating name_tsv for all STE rows (537k rows, may take ~5 min)...")
    t0 = time.time()
    async with Session() as s:
        await s.execute(text("""
            UPDATE ste SET name_tsv = to_tsvector('russian', name)
            WHERE name_tsv IS NULL AND name IS NOT NULL
        """))
        await s.commit()
    log.info("name_tsv updated in %.1fs", time.time() - t0)

    log.info("Creating popularity view...")
    async with Session() as s:
        await s.execute(text("""
            CREATE TABLE IF NOT EXISTS ste_popularity AS
            SELECT ste_id, COUNT(*) AS contract_cnt
            FROM contracts
            GROUP BY ste_id
        """))
        await s.commit()
    log.info("Popularity table created.")

    async with Session() as s:
        tsv_count = (await s.execute(text("SELECT COUNT(*) FROM ste WHERE name_tsv IS NOT NULL"))).scalar()
        pop_count = (await s.execute(text("SELECT COUNT(*) FROM ste_popularity"))).scalar()
        log.info("STE with tsvector: %d", tsv_count)
        log.info("Popularity rows:   %d", pop_count)

    await engine.dispose()
    log.info("Done!")


asyncio.run(main())
