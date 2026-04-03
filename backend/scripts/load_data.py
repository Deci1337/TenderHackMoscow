"""
Data Loader Script.
Parses STE and Contracts datasets, generates embeddings, builds indexes.

Usage:
  python -m scripts.load_data --ste-file data/ste.csv --contracts-file data/contracts.csv
"""
import argparse
import sys
import time
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.nlp_service import get_nlp_service
from app.services.embedding_service import get_embedding_service
from app.services.search_service import get_search_service, STEDocument
from app.services.personalization_service import get_personalization_service


def load_ste_data(filepath: str) -> pd.DataFrame:
    """Load STE catalog data."""
    logger.info(f"Loading STE data from {filepath}")
    if filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath)
    else:
        df = pd.read_csv(filepath, sep=None, engine="python")

    logger.info(f"STE loaded: {len(df)} rows, columns: {list(df.columns)}")
    col_map = {}
    for col in df.columns:
        cl = col.lower().strip()
        if "id" in cl and "ste" in cl:
            col_map["ste_id"] = col
        elif "name" in cl or "наименование" in cl or "название" in cl:
            col_map["name"] = col
        elif "categ" in cl or "категория" in cl or "группа" in cl or "кпгз" in cl:
            col_map["category"] = col
        elif "attr" in cl or "характеристик" in cl or "спгз" in cl:
            col_map["attributes"] = col

    if "ste_id" not in col_map:
        first_id_col = [c for c in df.columns if "id" in c.lower()]
        if first_id_col:
            col_map["ste_id"] = first_id_col[0]
        else:
            df["_ste_id"] = range(1, len(df) + 1)
            col_map["ste_id"] = "_ste_id"

    if "name" not in col_map:
        text_cols = [c for c in df.columns if df[c].dtype == "object"]
        if text_cols:
            col_map["name"] = text_cols[0]

    logger.info(f"Column mapping: {col_map}")
    return df, col_map


def load_contracts_data(filepath: str) -> pd.DataFrame:
    """Load contracts data."""
    logger.info(f"Loading contracts from {filepath}")
    if filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath)
    else:
        df = pd.read_csv(filepath, sep=None, engine="python")
    logger.info(f"Contracts loaded: {len(df)} rows, columns: {list(df.columns)}")
    return df


def build_indexes(ste_df: pd.DataFrame, col_map: dict, contracts_df: pd.DataFrame | None = None):
    """Build all search indexes from data."""
    nlp = get_nlp_service()
    embedder = get_embedding_service()
    searcher = get_search_service()
    personalizer = get_personalization_service()

    searcher.initialize(nlp, embedder)

    documents: list[STEDocument] = []
    names_for_embedding: list[str] = []
    ste_ids_for_embedding: list[int] = []

    logger.info("Processing STE documents...")
    t0 = time.time()

    for _, row in ste_df.iterrows():
        ste_id = int(row[col_map["ste_id"]]) if col_map.get("ste_id") else 0
        name = str(row.get(col_map.get("name", ""), ""))
        category = str(row.get(col_map.get("category", ""), "")) if col_map.get("category") else None
        attributes = str(row.get(col_map.get("attributes", ""), "")) if col_map.get("attributes") else None

        if not name or name == "nan":
            continue

        normalized = nlp.normalize_text(name)
        lemmas = nlp.lemmatize(name)

        full_text = name
        if attributes and attributes != "nan":
            full_text = f"{name} {attributes}"

        documents.append(STEDocument(
            ste_id=ste_id,
            name=name,
            category=category if category != "nan" else None,
            attributes=attributes if attributes != "nan" else None,
            name_normalized=normalized,
            lemmas=lemmas,
        ))
        names_for_embedding.append(full_text)
        ste_ids_for_embedding.append(ste_id)

    logger.info(f"Processed {len(documents)} STE documents in {time.time()-t0:.1f}s")

    logger.info("Generating embeddings...")
    t0 = time.time()
    batch_size = 256
    all_embeddings = []
    for i in range(0, len(names_for_embedding), batch_size):
        batch = names_for_embedding[i:i+batch_size]
        embs = embedder.embed(batch)
        all_embeddings.append(embs)
        if (i // batch_size) % 10 == 0:
            logger.info(f"  Embedded {i+len(batch)}/{len(names_for_embedding)}")

    embeddings_matrix = np.vstack(all_embeddings) if all_embeddings else np.array([])
    logger.info(f"Embeddings generated: shape={embeddings_matrix.shape} in {time.time()-t0:.1f}s")

    for i, doc in enumerate(documents):
        if i < len(embeddings_matrix):
            doc.embedding = embeddings_matrix[i]

    logger.info("Building search index...")
    searcher.index_documents(documents)

    ste_embeddings = {
        ste_ids_for_embedding[i]: embeddings_matrix[i]
        for i in range(len(ste_ids_for_embedding))
        if i < len(embeddings_matrix)
    }

    if contracts_df is not None:
        logger.info("Building user profiles from contracts...")
        build_user_profiles(contracts_df, ste_df, col_map, ste_embeddings)

    logger.info("All indexes built successfully")
    return ste_embeddings


def build_user_profiles(
    contracts_df: pd.DataFrame,
    ste_df: pd.DataFrame,
    col_map: dict,
    ste_embeddings: dict[int, np.ndarray],
):
    """Build user profiles from contract history."""
    personalizer = get_personalization_service()

    inn_col = None
    ste_id_col = None
    for col in contracts_df.columns:
        cl = col.lower().strip()
        if "inn" in cl and "customer" in cl or "инн" in cl and "заказчик" in cl:
            inn_col = col
        elif "ste" in cl and "id" in cl or "кпгз" in cl and "id" in cl:
            ste_id_col = col

    if not inn_col:
        inn_candidates = [c for c in contracts_df.columns if "inn" in c.lower() or "инн" in c.lower()]
        inn_col = inn_candidates[0] if inn_candidates else None

    if not ste_id_col:
        ste_candidates = [c for c in contracts_df.columns if "ste" in c.lower() or "кпгз" in c.lower()]
        ste_id_col = ste_candidates[0] if ste_candidates else None

    if not inn_col:
        logger.warning("Could not find customer INN column in contracts")
        return

    ste_categories = {}
    if col_map.get("category"):
        for _, row in ste_df.iterrows():
            sid = int(row[col_map["ste_id"]]) if col_map.get("ste_id") else 0
            cat = str(row.get(col_map.get("category", ""), ""))
            if cat and cat != "nan":
                ste_categories[sid] = cat

    user_data: dict[str, dict] = defaultdict(lambda: {"categories": [], "ste_ids": []})

    for _, row in contracts_df.iterrows():
        inn = str(row[inn_col]).strip()
        if not inn or inn == "nan":
            continue
        sid = int(row[ste_id_col]) if ste_id_col and pd.notna(row.get(ste_id_col)) else None

        if sid:
            user_data[inn]["ste_ids"].append(sid)
            if sid in ste_categories:
                user_data[inn]["categories"].append(ste_categories[sid])

    for inn, data in user_data.items():
        personalizer.build_profile_from_contracts(
            customer_inn=inn,
            categories=data["categories"],
            ste_embeddings=ste_embeddings,
            purchased_ste_ids=data["ste_ids"],
        )

    logger.info(f"Built profiles for {len(user_data)} users")


def main():
    parser = argparse.ArgumentParser(description="Load data and build search indexes")
    parser.add_argument("--ste-file", required=True, help="Path to STE catalog file (CSV/XLSX)")
    parser.add_argument("--contracts-file", default=None, help="Path to contracts file (CSV/XLSX)")
    args = parser.parse_args()

    ste_df, col_map = load_ste_data(args.ste_file)

    contracts_df = None
    if args.contracts_file:
        contracts_df = load_contracts_data(args.contracts_file)

    build_indexes(ste_df, col_map, contracts_df)
    logger.info("Data loading complete")


if __name__ == "__main__":
    main()
