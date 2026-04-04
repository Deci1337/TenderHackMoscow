"""Find category names for door handles and stationery pens in real DB."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, "backend")

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession)

    async with Session() as s:
        # Find categories for door-handle type products
        rows = await s.execute(text("""
            SELECT DISTINCT category, COUNT(*) as cnt
            FROM ste
            WHERE name_tsv @@ plainto_tsquery('russian', 'ручка дверная')
               OR name ILIKE '%ручка дверн%'
               OR name ILIKE '%ручка для двер%'
            GROUP BY category ORDER BY cnt DESC LIMIT 15
        """))
        print("Door handle categories:")
        for r in rows:
            print(f"  {r.cnt:4d}  {r.category}")

        # Find categories for stationery pens
        rows2 = await s.execute(text("""
            SELECT DISTINCT category, COUNT(*) as cnt
            FROM ste
            WHERE name_tsv @@ plainto_tsquery('russian', 'ручка шариковая')
               OR name ILIKE '%ручка шарик%'
               OR name ILIKE '%ручка гелев%'
            GROUP BY category ORDER BY cnt DESC LIMIT 15
        """))
        print("\nStationery pen categories:")
        for r in rows2:
            print(f"  {r.cnt:4d}  {r.category}")

        # Show all categories matching ручка broadly
        rows3 = await s.execute(text("""
            SELECT DISTINCT category, COUNT(*) as cnt
            FROM ste
            WHERE name_tsv @@ plainto_tsquery('russian', 'ручка')
            GROUP BY category ORDER BY cnt DESC LIMIT 20
        """))
        print("\nAll 'ручка' categories:")
        for r in rows3:
            print(f"  {r.cnt:4d}  {r.category}")

    await engine.dispose()

asyncio.run(main())
