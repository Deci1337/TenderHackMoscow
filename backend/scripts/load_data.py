"""
Data loader script: parses STE and Contracts datasets, loads into PostgreSQL.
Run inside the backend container: python -m scripts.load_data
"""
import asyncio
import logging
import os
import sys

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.models import STE, Contract, UserProfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


async def load_ste(session: AsyncSession, filepath: str):
    """Load STE (product catalog) data from Excel/CSV."""
    log.info("Loading STE data from %s", filepath)
    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    log.info("STE dataset: %d rows, columns: %s", len(df), list(df.columns))
    log.info("Sample:\n%s", df.head(3).to_string())

    col_map = _detect_columns(df, {
        "id": ["id", "ste_id", "identifier", "ste"],
        "name": ["name", "naimenovanie", "ste_name"],
        "category": ["category", "kategoriya", "kategoria"],
        "attributes": ["attributes", "atributy", "attrs"],
    })
    log.info("Detected STE column mapping: %s", col_map)

    count = 0
    for _, row in df.iterrows():
        attrs = {}
        if col_map.get("attributes") and pd.notna(row.get(col_map["attributes"])):
            raw = row[col_map["attributes"]]
            if isinstance(raw, str):
                try:
                    import json
                    attrs = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    attrs = {"raw": raw}
            else:
                attrs = {"raw": str(raw)}

        ste = STE(
            id=int(row[col_map["id"]]),
            name=str(row[col_map["name"]]),
            category=str(row[col_map["category"]]) if col_map.get("category") and pd.notna(row.get(col_map["category"])) else None,
            attributes=attrs,
        )
        session.add(ste)
        count += 1
        if count % 5000 == 0:
            await session.flush()
            log.info("  STE: flushed %d rows", count)

    await session.commit()
    log.info("STE: loaded %d rows total", count)


async def load_contracts(session: AsyncSession, filepath: str):
    """Load Contracts data from Excel/CSV."""
    log.info("Loading Contracts data from %s", filepath)
    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    log.info("Contracts dataset: %d rows, columns: %s", len(df), list(df.columns))
    log.info("Sample:\n%s", df.head(3).to_string())

    col_map = _detect_columns(df, {
        "purchase_name": ["purchase_name", "naimenovanie_zakupki", "naimenovanie"],
        "contract_id": ["contract_id", "identifikator_kontrakta", "id_kontrakta"],
        "ste_id": ["ste_id", "identifikator_ste", "id_ste"],
        "contract_date": ["contract_date", "data_zaklyucheniya", "data"],
        "cost": ["cost", "stoimost", "stoimost_kontrakta"],
        "customer_inn": ["customer_inn", "inn_zakazchika"],
        "customer_name": ["customer_name", "naimenovanie_zakazchika"],
        "customer_region": ["customer_region", "region_zakazchika"],
        "supplier_inn": ["supplier_inn", "inn_postavshchika"],
        "supplier_name": ["supplier_name", "naimenovanie_postavshchika"],
        "supplier_region": ["supplier_region", "region_postavshchika"],
    })
    log.info("Detected Contract column mapping: %s", col_map)

    count = 0
    for _, row in df.iterrows():
        contract = Contract(
            purchase_name=_get_val(row, col_map, "purchase_name"),
            contract_id=str(row[col_map["contract_id"]]),
            ste_id=_get_int(row, col_map, "ste_id"),
            contract_date=_get_val(row, col_map, "contract_date"),
            cost=_get_float(row, col_map, "cost"),
            customer_inn=str(row[col_map["customer_inn"]]),
            customer_name=_get_val(row, col_map, "customer_name"),
            customer_region=_get_val(row, col_map, "customer_region"),
            supplier_inn=_get_val(row, col_map, "supplier_inn"),
            supplier_name=_get_val(row, col_map, "supplier_name"),
            supplier_region=_get_val(row, col_map, "supplier_region"),
        )
        session.add(contract)
        count += 1
        if count % 5000 == 0:
            await session.flush()
            log.info("  Contracts: flushed %d rows", count)

    await session.commit()
    log.info("Contracts: loaded %d rows total", count)


async def build_user_profiles(session: AsyncSession):
    """Build initial user profiles from contract history."""
    log.info("Building user profiles from contract history")
    result = await session.execute(text("""
        INSERT INTO user_profiles (inn, name, region, profile_data, created_at)
        SELECT DISTINCT ON (customer_inn)
            customer_inn, customer_name, customer_region, '{}'::jsonb, now()
        FROM contracts
        WHERE customer_inn IS NOT NULL
        ON CONFLICT (inn) DO NOTHING
    """))
    await session.commit()
    log.info("User profiles built: %d new profiles", result.rowcount)


async def update_tsvectors(session: AsyncSession):
    """Populate tsvector column for full-text search."""
    log.info("Updating tsvector column for STE")
    await session.execute(text("""
        UPDATE ste SET name_tsv = to_tsvector('russian', name)
        WHERE name_tsv IS NULL
    """))
    await session.commit()
    log.info("tsvector update complete")


def _detect_columns(df: pd.DataFrame, expected: dict[str, list[str]]) -> dict[str, str]:
    """Auto-detect column names by matching known aliases (case-insensitive)."""
    cols_lower = {c.lower().strip(): c for c in df.columns}
    mapping = {}
    for field, aliases in expected.items():
        for alias in aliases:
            if alias.lower() in cols_lower:
                mapping[field] = cols_lower[alias.lower()]
                break
        if field not in mapping:
            for col_lower, col_orig in cols_lower.items():
                if alias.lower() in col_lower:
                    mapping[field] = col_orig
                    break
    return mapping


def _get_val(row, col_map, key):
    col = col_map.get(key)
    if col and pd.notna(row.get(col)):
        return str(row[col])
    return None


def _get_int(row, col_map, key):
    col = col_map.get(key)
    if col and pd.notna(row.get(col)):
        try:
            return int(float(row[col]))
        except (ValueError, TypeError):
            return None
    return None


def _get_float(row, col_map, key):
    col = col_map.get(key)
    if col and pd.notna(row.get(col)):
        try:
            return float(row[col])
        except (ValueError, TypeError):
            return None
    return None


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    data_dir = settings.DATA_DIR
    log.info("Data directory: %s", data_dir)
    log.info("Files found: %s", os.listdir(data_dir) if os.path.exists(data_dir) else "DIRECTORY NOT FOUND")

    ste_file = None
    contracts_file = None
    for f in os.listdir(data_dir) if os.path.exists(data_dir) else []:
        fl = f.lower()
        if "ste" in fl or "product" in fl or "tovar" in fl:
            ste_file = os.path.join(data_dir, f)
        elif "contract" in fl or "kontrakt" in fl:
            contracts_file = os.path.join(data_dir, f)

    async with session_factory() as session:
        if ste_file:
            await load_ste(session, ste_file)
            await update_tsvectors(session)
        else:
            log.warning("STE file not found in %s", data_dir)

        if contracts_file:
            await load_contracts(session, contracts_file)
            await build_user_profiles(session)
        else:
            log.warning("Contracts file not found in %s", data_dir)

    await engine.dispose()
    log.info("Data loading complete")


if __name__ == "__main__":
    asyncio.run(main())
