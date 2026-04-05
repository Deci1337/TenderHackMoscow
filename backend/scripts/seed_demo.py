"""
Seed demo data: 3 realistic user profiles with contracts generated from real STE rows.

Run:
    python -m scripts.seed_demo
"""
import asyncio
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

DEMO_PROFILES = [
    {
        "inn": "7701234567",
        "name": "Школа №1234",
        "industry": "Образование",
        "region": "Москва",
        "purchase_pattern": {
            "Канцелярские товары": 45,
            "Мебель офисная": 20,
            "IT-оборудование": 12,
            "Спортивный инвентарь": 8,
        },
    },
    {
        "inn": "7709876543",
        "name": "Городская больница №5",
        "industry": "Медицина",
        "region": "Москва",
        "purchase_pattern": {
            "Медицинские товары": 80,
            "Расходные материалы": 60,
            "Хозяйственные товары": 25,
            "IT-оборудование": 15,
        },
    },
    {
        "inn": "7705551234",
        "name": "СтройМонтаж ООО",
        "industry": "Стройматериалы",
        "region": "Московская область",
        "purchase_pattern": {
            "Стройматериалы": 120,
            "Электротехника": 55,
            "Инструменты": 30,
            "Хозяйственные товары": 18,
        },
    },
]


async def seed_demo_contracts(db: AsyncSession) -> None:
    for profile in DEMO_PROFILES:
        await db.execute(text("""
            INSERT INTO user_profiles (inn, name, region, industry, profile_data, created_at)
            VALUES (:inn, :name, :region, :industry, CAST(:pd AS jsonb), now())
            ON CONFLICT (inn) DO UPDATE
              SET name = EXCLUDED.name,
                  region = EXCLUDED.region,
                  industry = EXCLUDED.industry,
                  profile_data = EXCLUDED.profile_data
        """), {
            "inn": profile["inn"],
            "name": profile["name"],
            "region": profile["region"],
            "industry": profile["industry"],
            "pd": f'{{"industry":"{profile["industry"]}","region":"{profile["region"]}"}}'
        })

        for category, count in profile["purchase_pattern"].items():
            result = await db.execute(text("""
                SELECT id FROM ste
                WHERE category ILIKE :cat
                LIMIT :lim
            """), {"cat": f"%{category}%", "lim": count})
            ste_ids = [row.id for row in result.fetchall()]

            for ste_id in ste_ids:
                contract_date = date.today() - timedelta(days=random.randint(1, 365))
                await db.execute(text("""
                    INSERT INTO contracts
                        (purchase_name, contract_id, ste_id, contract_date, cost,
                         customer_inn, customer_name, customer_region)
                    VALUES
                        (:pn, :cid, :sid, :dt, :cost, :inn, :cname, :reg)
                    ON CONFLICT (contract_id) DO NOTHING
                """), {
                    "pn": f"Закупка: {category}",
                    "cid": f"DEMO-{profile['inn']}-{ste_id}",
                    "sid": ste_id,
                    "dt": contract_date,
                    "cost": round(random.uniform(1000, 500000), 2),
                    "inn": profile["inn"],
                    "cname": profile["name"],
                    "reg": profile["region"],
                })

        await db.commit()

        try:
            from app.services.personalization_service import get_personalization_service
            svc = get_personalization_service()
            await svc.rebuild_from_db(profile["inn"], db)
            print(f"  Profile rebuilt in memory for {profile['inn']}")
        except Exception as e:
            print(f"  Warning: could not rebuild in-memory profile for {profile['inn']}: {e}")


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        from app.database import Base
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as db:
        # Remove only demo contracts to avoid wiping production data
        for p in DEMO_PROFILES:
            await db.execute(text("""
                DELETE FROM contracts
                WHERE customer_inn = :inn AND contract_id LIKE 'DEMO-%'
            """), {"inn": p["inn"]})
        await db.commit()

        await seed_demo_contracts(db)

    await engine.dispose()

    total_contracts = sum(
        sum(v for v in p["purchase_pattern"].values()) for p in DEMO_PROFILES
    )
    print(f"Seeded: {len(DEMO_PROFILES)} demo users, up to {total_contracts} contracts from real STE data")


if __name__ == "__main__":
    asyncio.run(main())
