"""Quick diagnostic: test DB queries and search API."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.config import settings


async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    S = async_sessionmaker(engine, class_=AsyncSession)
    async with S() as s:
        r = await s.execute(text("SELECT count(*) FROM ste"))
        print(f"STE count: {r.scalar()}")

        r = await s.execute(text("SELECT count(*) FROM contracts"))
        print(f"Contracts count: {r.scalar()}")

        r = await s.execute(text("SELECT count(*) FROM user_profiles"))
        print(f"Users count: {r.scalar()}")

        # Check pg_trgm similarity for the word "bumaga"
        query_word = "\u0431\u0443\u043c\u0430\u0433\u0430"
        r = await s.execute(text(
            "SELECT name, similarity(name, :q) as sim FROM ste ORDER BY sim DESC LIMIT 5"
        ), {"q": query_word})
        print(f"\nSimilarity scores for '{query_word}':")
        for row in r.all():
            print(f"  sim={row[1]:.3f}  {row[0]}")

        # Check tsvector
        r = await s.execute(text(
            "SELECT name FROM ste WHERE name_tsv @@ plainto_tsquery('russian', :q) LIMIT 5"
        ), {"q": query_word})
        results = [row[0] for row in r.all()]
        print(f"\ntsquery results for '{query_word}': {results}")

        # Check pg_trgm % operator
        r = await s.execute(text(
            "SELECT name FROM ste WHERE name % :q LIMIT 5"
        ), {"q": query_word})
        results = [row[0] for row in r.all()]
        print(f"\npg_trgm % results for '{query_word}': {results}")

        # Check name_tsv is populated
        r = await s.execute(text(
            "SELECT id, name, name_tsv IS NOT NULL as has_tsv FROM ste LIMIT 5"
        ))
        print("\nSample STE rows (tsv populated?):")
        for row in r.all():
            print(f"  id={row[0]} has_tsv={row[2]} name={row[1]}")

        # Check current threshold
        r = await s.execute(text("SHOW pg_trgm.similarity_threshold"))
        print(f"\npg_trgm.similarity_threshold: {r.scalar()}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
