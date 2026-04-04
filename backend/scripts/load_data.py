"""
Data loader: parses STE and Contracts datasets, loads into PostgreSQL,
then builds Dev2 ML search indexes (BM25 + embeddings + user profiles).

Usage:
  python -m scripts.load_data
  python -m scripts.load_data --ste-file data/ste.csv --contracts-file data/contracts.csv

Also supports headerless ``;``-separated STE/Contracts CSVs (hackathon export).
"""
import argparse
import asyncio
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.models import STE, Contract, UserProfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

STE_COLS = ["ste_id", "name", "category", "attributes"]
CONTRACT_COLS = [
    "purchase_name", "contract_id", "ste_id", "contract_date",
    "contract_cost", "customer_inn", "customer_name", "customer_region",
    "supplier_inn", "supplier_name", "supplier_region",
]


def deduplicate_attributes(attr_str: str) -> str:
    """Remove duplicated key:value pairs within the semicolon-separated attributes string."""
    if not attr_str or attr_str == "nan":
        return ""
    seen = set()
    unique_pairs = []
    for pair in str(attr_str).split(";"):
        pair = pair.strip()
        if pair and pair not in seen:
            seen.add(pair)
            unique_pairs.append(pair)
    return "; ".join(unique_pairs)


def _load_ste_df(filepath: str) -> pd.DataFrame:
    if filepath.endswith((".xlsx", ".xls")):
        return pd.read_excel(filepath)
    probe = pd.read_csv(filepath, sep=";", header=None, nrows=2)
    if len(probe.columns) >= 4:
        try:
            int(str(probe.iloc[0, 0]).strip())
            df = pd.read_csv(
                filepath, sep=";", header=None, names=STE_COLS,
                dtype={"ste_id": str}, low_memory=False,
            )
            df = df.drop_duplicates(subset="ste_id", keep="first")
            df["attributes"] = df["attributes"].fillna("").map(deduplicate_attributes)
            return df
        except (ValueError, TypeError):
            pass
    return pd.read_csv(filepath)


def _load_contracts_df(filepath: str) -> pd.DataFrame:
    if filepath.endswith((".xlsx", ".xls")):
        return pd.read_excel(filepath)
    probe = pd.read_csv(filepath, sep=";", header=None, nrows=2)
    if len(probe.columns) >= len(CONTRACT_COLS):
        try:
            int(str(probe.iloc[0, 2]).strip())
            return pd.read_csv(
                filepath, sep=";", header=None, names=CONTRACT_COLS,
                dtype={"contract_id": str, "ste_id": str, "customer_inn": str, "supplier_inn": str},
                low_memory=False,
            )
        except (ValueError, TypeError):
            pass
    return pd.read_csv(filepath)


def _ste_col_map(df: pd.DataFrame) -> dict:
    if set(STE_COLS).issubset(set(df.columns)):
        return {"id": "ste_id", "name": "name", "category": "category", "attributes": "attributes"}
    return _detect_columns(df, {
        "id": ["id", "ste_id", "identifier", "ste"],
        "name": ["name", "naimenovanie", "ste_name", "название"],
        "category": ["category", "kategoriya", "kategoria", "категория", "кпгз"],
        "attributes": ["attributes", "atributy", "attrs", "характеристики"],
    })


def _contracts_col_map(df: pd.DataFrame) -> dict:
    if set(CONTRACT_COLS).issubset(set(df.columns)):
        return {
            "purchase_name": "purchase_name",
            "contract_id": "contract_id",
            "ste_id": "ste_id",
            "contract_date": "contract_date",
            "cost": "contract_cost",
            "customer_inn": "customer_inn",
            "customer_name": "customer_name",
            "customer_region": "customer_region",
            "supplier_inn": "supplier_inn",
            "supplier_name": "supplier_name",
            "supplier_region": "supplier_region",
        }
    return _detect_columns(df, {
        "purchase_name": ["purchase_name", "naimenovanie_zakupki", "naimenovanie", "наименование"],
        "contract_id": ["contract_id", "identifikator_kontrakta", "id_kontrakta"],
        "ste_id": ["ste_id", "identifikator_ste", "id_ste", "кпгз"],
        "contract_date": ["contract_date", "data_zaklyucheniya", "data", "дата"],
        "cost": ["cost", "stoimost", "stoimost_kontrakta", "стоимость", "contract_cost"],
        "customer_inn": ["customer_inn", "inn_zakazchika", "инн заказчика", "инн"],
        "customer_name": ["customer_name", "naimenovanie_zakazchika"],
        "customer_region": ["customer_region", "region_zakazchika"],
        "supplier_inn": ["supplier_inn", "inn_postavshchika"],
        "supplier_name": ["supplier_name", "naimenovanie_postavshchika"],
        "supplier_region": ["supplier_region", "region_postavshchika"],
    })


# ---------------------------------------------------------------------------
# PostgreSQL loading (Dev1)
# ---------------------------------------------------------------------------

async def load_ste(session: AsyncSession, filepath: str):
    """Load STE catalog into PostgreSQL."""
    log.info("Loading STE from %s", filepath)
    df = _load_ste_df(filepath)
    log.info("STE: %d rows, cols: %s", len(df), list(df.columns))

    col_map = _ste_col_map(df)
    log.info("Column mapping: %s", col_map)

    count = 0
    for _, row in df.iterrows():
        attrs = _parse_attrs(row, col_map)
        ste = STE(
            id=int(row[col_map["id"]]),
            name=str(row[col_map["name"]]),
            category=_get_val(row, col_map, "category"),
            attributes=attrs,
        )
        session.add(ste)
        count += 1
        if count % 5000 == 0:
            await session.flush()
            log.info("  STE: flushed %d rows", count)

    await session.commit()
    log.info("STE: loaded %d rows", count)


async def load_contracts(session: AsyncSession, filepath: str):
    """Load Contracts into PostgreSQL."""
    log.info("Loading Contracts from %s", filepath)
    df = _load_contracts_df(filepath)
    log.info("Contracts: %d rows, cols: %s", len(df), list(df.columns))

    col_map = _contracts_col_map(df)
    log.info("Column mapping: %s", col_map)

    cid_col = col_map.get("contract_id")
    if cid_col:
        before = len(df)
        df = df.drop_duplicates(subset=[cid_col], keep="first")
        if len(df) < before:
            log.info("Dropped %d duplicate contract_id rows", before - len(df))

    count = 0
    for _, row in df.iterrows():
        contract = Contract(
            purchase_name=_get_val(row, col_map, "purchase_name"),
            contract_id=str(row[col_map["contract_id"]]),
            ste_id=_get_int(row, col_map, "ste_id"),
            contract_date=_parse_contract_date(row, col_map, "contract_date"),
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
    log.info("Contracts: loaded %d rows", count)


async def build_user_profiles(session: AsyncSession):
    log.info("Building user profiles from contract history")
    result = await session.execute(text("""
        INSERT INTO user_profiles (inn, name, region, profile_data, created_at)
        SELECT DISTINCT ON (customer_inn)
            customer_inn, customer_name, customer_region, '{}'::jsonb, now()
        FROM contracts WHERE customer_inn IS NOT NULL
        ON CONFLICT (inn) DO NOTHING
    """))
    await session.commit()
    log.info("User profiles: %d created", result.rowcount)


async def update_tsvectors(session: AsyncSession):
    log.info("Updating tsvector column")
    await session.execute(text("""
        UPDATE ste SET name_tsv = to_tsvector('russian', name) WHERE name_tsv IS NULL
    """))
    await session.commit()
    log.info("tsvector update done")


# ---------------------------------------------------------------------------
# Dev2 ML indexes (embeddings, BM25, in-memory profiles)
# ---------------------------------------------------------------------------

def build_ml_indexes(ste_file: str, contracts_file: str | None = None):
    """Build Dev2 in-memory ML indexes after PostgreSQL data is loaded."""
    try:
        import numpy as np
        from app.services.nlp_service import get_nlp_service
        from app.services.embedding_service import get_embedding_service
        from app.services.search_service import get_search_service, STEDocument

        log.info("Building ML indexes...")
        nlp = get_nlp_service()
        embedder = get_embedding_service()
        searcher = get_search_service()
        searcher.initialize(nlp, embedder)

        df = _load_ste_df(ste_file)
        col_map = _ste_col_map(df)

        documents, texts, ids, all_names = [], [], [], []
        for _, row in df.iterrows():
            sid = int(row[col_map["id"]]) if col_map.get("id") else 0
            name = str(row.get(col_map.get("name", ""), "") or "")
            if not name or name == "nan":
                continue
            cat = _get_val(row, col_map, "category")
            attrs = str(_parse_attrs(row, col_map))
            documents.append(STEDocument(
                ste_id=sid, name=name, category=cat, attributes=attrs,
                name_normalized=nlp.normalize_text(name),
                lemmas=nlp.lemmatize(name),
            ))
            texts.append(f"{name} {attrs}" if attrs != "{}" else name)
            ids.append(sid)
            all_names.append(name)

        nlp.build_frequency_dict_from_corpus(all_names)
        log.info("Generating embeddings for %d docs...", len(documents))
        batch_size = 256
        all_embs = []
        for i in range(0, len(texts), batch_size):
            all_embs.append(embedder.embed(texts[i:i+batch_size]))
            log.info("  %d/%d", min(i+batch_size, len(texts)), len(texts))

        if all_embs:
            embs = np.vstack(all_embs)
            for i, doc in enumerate(documents):
                if i < len(embs):
                    doc.embedding = embs[i]

        searcher.index_documents(documents)
        log.info("ML indexes built for %d documents", len(documents))

        if contracts_file:
            _build_ml_profiles(contracts_file, df, col_map, dict(zip(ids, np.vstack(all_embs) if all_embs else [])))

    except Exception as e:
        log.warning("ML index build failed (search will use SQL fallback): %s", e)


def _build_ml_profiles(contracts_file, ste_df, col_map, ste_embeddings):
    from collections import defaultdict
    from app.services.personalization_service import get_personalization_service
    import numpy as np

    df = _load_contracts_df(contracts_file)
    inn_col = next((c for c in df.columns if "inn" in c.lower() or "инн" in c.lower()), None)
    ste_col = next((c for c in df.columns if "ste" in c.lower() or "кпгз" in c.lower()), None)
    if not inn_col:
        return

    ste_cats = {}
    if col_map.get("category"):
        for _, row in ste_df.iterrows():
            sid = int(row[col_map.get("id", "id")]) if col_map.get("id") else 0
            cat = _get_val(row, col_map, "category")
            if cat:
                ste_cats[sid] = cat

    user_data: dict = defaultdict(lambda: {"ste_ids": [], "categories": []})
    for _, row in df.iterrows():
        inn = str(row[inn_col]).strip()
        if not inn or inn == "nan":
            continue
        sid = _get_int(row, {ste_col: ste_col} if ste_col else {}, ste_col) if ste_col else None
        if sid:
            user_data[inn]["ste_ids"].append(sid)
            if sid in ste_cats:
                user_data[inn]["categories"].append(ste_cats[sid])

    personalizer = get_personalization_service()
    for inn, data in user_data.items():
        personalizer.build_profile_from_contracts(
            customer_inn=inn, categories=data["categories"],
            ste_embeddings=ste_embeddings, purchased_ste_ids=data["ste_ids"],
        )
    log.info("ML profiles built for %d users", len(user_data))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_columns(df, expected):
    cols_lower = {c.lower().strip(): c for c in df.columns}
    mapping = {}
    for field, aliases in expected.items():
        for alias in aliases:
            if alias.lower() in cols_lower:
                mapping[field] = cols_lower[alias.lower()]
                break
        if field not in mapping:
            for col_lower, col_orig in cols_lower.items():
                for alias in aliases:
                    if alias.lower() in col_lower:
                        mapping[field] = col_orig
                        break
    return mapping


def _parse_attrs(row, col_map):
    col = col_map.get("attributes")
    if col and pd.notna(row.get(col)):
        raw = row[col]
        if isinstance(raw, str):
            try:
                import json
                return json.loads(raw)
            except Exception:
                return {"raw": raw}
        return {"raw": str(raw)}
    return {}


def _get_val(row, col_map, key):
    col = col_map.get(key)
    return str(row[col]) if col and pd.notna(row.get(col)) else None


def _get_int(row, col_map, key):
    col = col_map.get(key)
    if col and pd.notna(row.get(col)):
        try:
            return int(float(row[col]))
        except Exception:
            return None
    return None


def _get_float(row, col_map, key):
    col = col_map.get(key)
    if col and pd.notna(row.get(col)):
        try:
            return float(row[col])
        except Exception:
            return None
    return None


def _parse_contract_date(row, col_map, key):
    col = col_map.get(key)
    if not col or not pd.notna(row.get(col)):
        return None
    v = row[col]
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    dt = pd.to_datetime(v, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.date()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main_async(ste_file: str, contracts_file: str | None):
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        await load_ste(session, ste_file)
        await update_tsvectors(session)
        if contracts_file:
            await load_contracts(session, contracts_file)
            await build_user_profiles(session)

    await engine.dispose()
    build_ml_indexes(ste_file, contracts_file)
    log.info("All done")


def _auto_detect_files(data_dir: str):
    files = os.listdir(data_dir) if os.path.exists(data_dir) else []
    ste_file = next(
        (os.path.join(data_dir, f) for f in files if any(k in f.lower() for k in ["ste", "product", "tovar", "catalog"])),
        None,
    )
    contracts_file = next(
        (os.path.join(data_dir, f) for f in files if any(k in f.lower() for k in ["contract", "kontrakt"])),
        None,
    )
    return ste_file, contracts_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ste-file", default=None)
    parser.add_argument("--contracts-file", default=None)
    args = parser.parse_args()

    ste_file = args.ste_file
    contracts_file = args.contracts_file

    if not ste_file:
        ste_file, contracts_file = _auto_detect_files(settings.DATA_DIR)
        log.info("Auto-detected: ste=%s, contracts=%s", ste_file, contracts_file)

    if not ste_file:
        log.error("No STE file found in %s. Use --ste-file.", settings.DATA_DIR)
        sys.exit(1)

    asyncio.run(main_async(ste_file, contracts_file))


if __name__ == "__main__":
    main()
