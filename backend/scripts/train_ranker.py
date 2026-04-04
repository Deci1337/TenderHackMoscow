"""
Train CatBoost ranker using REAL search scores from BM25 + FAISS indexes.

Key differences from v1 (synthetic scores):
  - BM25 scores computed from actual rank_bm25 index over 543K STEs
  - Semantic scores computed from real rubert-tiny2 embeddings via cosine similarity
  - Profile similarity from actual user embedding (mean of purchased item embeddings)
  - 5-level relevance: 4=exact match, 3=also purchased, 2=same category, 1=user category, 0=other
  - Embeddings cached to disk (~650MB) so subsequent runs are fast

Usage:
  python scripts/train_ranker.py --ste-file ../data.csv --contracts-file ../contracts.csv
"""
import sys
import time
import argparse
from pathlib import Path
from collections import defaultdict, Counter

import numpy as np
import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ranking_service import FEATURE_NAMES

STE_COLS = ["ste_id", "name", "category", "attributes"]
CONTRACT_COLS = [
    "purchase_name", "contract_id", "ste_id", "contract_date",
    "contract_cost", "customer_inn", "customer_name", "customer_region",
    "supplier_inn", "supplier_name", "supplier_region",
]

DATA_DIR = Path(__file__).parent.parent / "app" / "data"
EMBEDDING_CACHE = DATA_DIR / "ste_embeddings_cache.npy"
STE_IDS_CACHE = DATA_DIR / "ste_ids_cache.npy"


def _ndcg_at_k(y_true: np.ndarray, y_pred: np.ndarray, k: int = 10) -> float:
    order = np.argsort(-y_pred)[:k]
    dcg = sum((2 ** y_true[i] - 1) / np.log2(j + 2) for j, i in enumerate(order))
    ideal_order = np.argsort(-y_true)[:k]
    idcg = sum((2 ** y_true[i] - 1) / np.log2(j + 2) for j, i in enumerate(ideal_order))
    return dcg / idcg if idcg > 0 else 0.0


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(ste_file: str, contracts_file: str):
    logger.info("Loading STE catalog...")
    ste_df = pd.read_csv(ste_file, sep=";", header=None, names=STE_COLS, dtype={"ste_id": str})
    ste_df = ste_df.drop_duplicates(subset="ste_id", keep="first")
    ste_df["ste_id_int"] = ste_df["ste_id"].astype(int)
    ste_df["name"] = ste_df["name"].fillna("")
    logger.info(f"STE: {len(ste_df)} unique items")

    logger.info("Loading contracts...")
    contracts_df = pd.read_csv(
        contracts_file, sep=";", header=None, names=CONTRACT_COLS,
        dtype={"ste_id": str, "customer_inn": str}, low_memory=False,
    )
    logger.info(f"Contracts: {len(contracts_df)} rows")
    return ste_df, contracts_df


# ---------------------------------------------------------------------------
# Index construction (BM25 + embeddings)
# ---------------------------------------------------------------------------

def init_nlp():
    from app.services.nlp_service import NLPService
    nlp = NLPService()
    nlp.initialize()
    return nlp


def compute_or_load_embeddings(ste_names: list[str]) -> np.ndarray:
    if EMBEDDING_CACHE.exists():
        cached = np.load(EMBEDDING_CACHE)
        if cached.shape[0] == len(ste_names):
            logger.info(f"Loaded cached embeddings: {cached.shape}")
            return cached
        logger.info("Cache size mismatch, recomputing...")

    import torch
    from transformers import AutoTokenizer, AutoModel

    model_name = "cointegrated/rubert-tiny2"
    logger.info(f"Computing embeddings for {len(ste_names)} items with {model_name} (one-time, ~15-20 min)...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()

    batch_size = 256
    all_embs = []
    for start in range(0, len(ste_names), batch_size):
        batch = ste_names[start:start + batch_size]
        encoded = tokenizer(batch, padding=True, truncation=True, max_length=64, return_tensors="pt")
        with torch.no_grad():
            output = model(**encoded)
        emb = output.last_hidden_state[:, 0, :].numpy()
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-9)
        emb = emb / norms
        all_embs.append(emb)
        if (start // batch_size + 1) % 200 == 0:
            logger.info(f"  embedded {start + len(batch)}/{len(ste_names)}")

    embeddings = np.vstack(all_embs).astype(np.float32)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDING_CACHE, embeddings)
    logger.info(f"Embeddings cached to {EMBEDDING_CACHE} ({embeddings.nbytes / 1e6:.0f} MB)")
    return embeddings


def build_bm25_index(tokenized_docs: list[list[str]]):
    from rank_bm25 import BM25Okapi
    logger.info(f"Building BM25 index from {len(tokenized_docs)} docs...")
    return BM25Okapi(tokenized_docs)


# ---------------------------------------------------------------------------
# User profile construction
# ---------------------------------------------------------------------------

def build_users(contracts_df, ste_categories, ste_id_to_idx, embeddings_norm):
    logger.info("Building user profiles from contracts...")
    user_purchases = defaultdict(set)
    user_cats_raw = defaultdict(list)

    for _, row in contracts_df.iterrows():
        inn = str(row["customer_inn"]).strip()
        try:
            sid = int(row["ste_id"])
        except (ValueError, TypeError):
            continue
        if inn and inn != "nan" and sid in ste_id_to_idx:
            user_purchases[inn].add(sid)
            cat = ste_categories.get(sid, "")
            if cat:
                user_cats_raw[inn].append(cat)

    # Popularity from contract counts
    pop_counts = contracts_df["ste_id"].value_counts()
    max_pop = pop_counts.max() or 1
    pop_map = (pop_counts / max_pop).to_dict()

    users = {}
    for inn, purchased in user_purchases.items():
        if len(purchased) < 3:
            continue
        cats = user_cats_raw[inn]
        cat_counter = Counter(cats)
        total = sum(cat_counter.values()) or 1
        cat_weights = {c: count / total for c, count in cat_counter.items()}

        purchased_idxs = [ste_id_to_idx[s] for s in purchased if s in ste_id_to_idx]
        if purchased_idxs:
            user_emb = embeddings_norm[purchased_idxs].mean(axis=0)
            norm = np.linalg.norm(user_emb)
            user_emb = user_emb / norm if norm > 1e-9 else user_emb
        else:
            user_emb = None

        users[inn] = {
            "purchased": purchased,
            "cat_weights": cat_weights,
            "embedding": user_emb,
            "total_contracts": len(purchased),
        }

    logger.info(f"Built profiles for {len(users)} users (from {len(user_purchases)} total)")
    return users, pop_map


# ---------------------------------------------------------------------------
# Training data generation with REAL scores
# ---------------------------------------------------------------------------

def generate_training_data(
    users, bm25_index, embeddings_norm, nlp,
    ste_ids, ste_names, ste_categories, ste_id_to_idx, pop_map,
    max_users=1000, queries_per_user=5, top_k=100, seed=42,
):
    rng = np.random.default_rng(seed)

    user_inns = list(users.keys())
    rng.shuffle(user_inns)
    sampled = user_inns[:min(max_users, len(user_inns))]
    logger.info(f"Generating training data: {len(sampled)} users, {queries_per_user} queries each")

    all_features, all_labels, all_groups = [], [], []
    group_id = 0
    n_ste = len(ste_ids)

    for u_idx, inn in enumerate(sampled):
        user = users[inn]
        purchased = list(user["purchased"])
        n_q = min(queries_per_user, len(purchased))
        query_sids = rng.choice(purchased, n_q, replace=False)

        for query_sid in query_sids:
            q_idx = ste_id_to_idx.get(query_sid)
            if q_idx is None:
                continue
            q_name = ste_names[q_idx]
            q_cat = ste_categories.get(query_sid, "")
            if not q_name or q_name == "nan":
                continue

            # -- REAL BM25 scores --
            q_tokens = nlp.lemmatize(q_name)
            if not q_tokens:
                continue
            bm25_raw = bm25_index.get_scores(q_tokens)
            bm25_max = bm25_raw.max() or 1.0
            bm25_norm = bm25_raw / bm25_max

            # -- REAL semantic scores (cosine similarity, embeddings already L2-normalized) --
            q_emb = embeddings_norm[q_idx]
            sem_scores = embeddings_norm @ q_emb

            # Candidate set: top BM25 + top semantic + user's purchased items
            top_bm25_idxs = set(np.argsort(bm25_raw)[-top_k:])
            top_sem_idxs = set(np.argsort(sem_scores)[-top_k:])
            purchased_idxs = {ste_id_to_idx[s] for s in purchased if s in ste_id_to_idx}
            candidates = top_bm25_idxs | top_sem_idxs | purchased_idxs

            if len(candidates) > 400:
                extras = candidates - top_bm25_idxs - top_sem_idxs
                keep = top_bm25_idxs | top_sem_idxs
                extras_list = list(extras)
                rng.shuffle(extras_list)
                candidates = keep | set(extras_list[:400 - len(keep)])

            group_features, group_labels = [], []
            for c_idx in candidates:
                c_sid = ste_ids[c_idx]
                c_cat = ste_categories.get(c_sid, "")

                bm25_f = float(bm25_norm[c_idx])
                sem_f = float(sem_scores[c_idx])
                cat_match = 1.0 if c_cat in user["cat_weights"] else 0.0
                cat_weight = user["cat_weights"].get(c_cat, 0.0)
                profile_sim = float(np.dot(user["embedding"], embeddings_norm[c_idx])) if user["embedding"] is not None else 0.0
                popularity = float(pop_map.get(str(c_sid), 0.0))
                name_len = min(len(ste_names[c_idx]) / 100.0, 1.0)
                is_purchased = 1.0 if c_sid in user["purchased"] else 0.0
                is_negative = 0.0
                total_c = min(user["total_contracts"] / 100.0, 1.0)
                session_clicks = 0.0

                features = np.array([
                    bm25_f, sem_f, cat_match, cat_weight, profile_sim,
                    min(popularity, 1.0), name_len,
                    0.0, is_negative, total_c, session_clicks,
                ], dtype=np.float32)

                if c_sid == query_sid:
                    rel = 4.0
                elif c_sid in user["purchased"]:
                    rel = 3.0
                elif c_cat == q_cat and c_cat:
                    rel = 2.0
                elif c_cat in user["cat_weights"]:
                    rel = 1.0
                else:
                    rel = 0.0

                group_features.append(features)
                group_labels.append(rel)

            if len(group_features) < 3:
                continue
            for f, l in zip(group_features, group_labels):
                all_features.append(f)
                all_labels.append(l)
                all_groups.append(group_id)
            group_id += 1

        if (u_idx + 1) % 100 == 0:
            logger.info(f"  {u_idx+1}/{len(sampled)} users, {len(all_features)} samples, {group_id} groups")

    X = np.array(all_features, dtype=np.float32)
    y = np.array(all_labels, dtype=np.float32)
    groups = np.array(all_groups, dtype=np.int32)

    label_dist = {int(v): int(np.sum(y == v)) for v in sorted(np.unique(y))}
    logger.info(
        f"Training data: {X.shape[0]} samples, {X.shape[1]} features, {group_id} groups | "
        f"labels: {label_dist}"
    )
    return X, y, groups


# ---------------------------------------------------------------------------
# CatBoost training
# ---------------------------------------------------------------------------

def save_training_data(X, y, groups, path: Path):
    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df["relevance"] = y
    df["group_id"] = groups
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info(f"Training data saved to {path} ({len(df)} rows)")


def train_catboost(X, y, groups, val_fraction: float = 0.2):
    from catboost import CatBoostRanker, Pool

    unique_groups = np.unique(groups)
    rng = np.random.RandomState(42)
    rng.shuffle(unique_groups)
    split_idx = int(len(unique_groups) * (1 - val_fraction))
    train_groups_set = set(unique_groups[:split_idx])

    train_mask = np.isin(groups, list(train_groups_set))
    val_mask = ~train_mask

    X_train, y_train, g_train = X[train_mask], y[train_mask], groups[train_mask]
    X_val, y_val, g_val = X[val_mask], y[val_mask], groups[val_mask]

    logger.info(f"Train/Val split: {len(X_train)} / {len(X_val)} samples")

    train_pool = Pool(data=X_train, label=y_train, group_id=g_train.tolist())
    val_pool = Pool(data=X_val, label=y_val, group_id=g_val.tolist())

    model = CatBoostRanker(
        iterations=1000,
        learning_rate=0.05,
        depth=6,
        loss_function="YetiRank",
        eval_metric="NDCG:top=10;type=Exp",
        verbose=100,
        random_seed=42,
        l2_leaf_reg=3.0,
        border_count=128,
        use_best_model=True,
        od_type="Iter",
        od_wait=80,
    )
    model.fit(train_pool, eval_set=val_pool)

    model_path = DATA_DIR / "catboost_ranker.cbm"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_path))
    logger.info(f"CatBoost model saved to {model_path}")

    val_pred = model.predict(X_val)
    val_group_ids = np.unique(g_val)
    ndcg_scores = []
    for gid in val_group_ids:
        mask = g_val == gid
        if mask.sum() < 2:
            continue
        ndcg_scores.append(_ndcg_at_k(y_val[mask], val_pred[mask], k=10))
    avg_ndcg = np.mean(ndcg_scores) if ndcg_scores else 0.0
    logger.info(f"Validation NDCG@10: {avg_ndcg:.4f} (over {len(ndcg_scores)} groups)")

    for imp_type in ["PredictionValuesChange", "LossFunctionChange"]:
        try:
            importances = model.get_feature_importance(data=train_pool, type=imp_type)
            logger.info(f"Feature importances ({imp_type}):")
            for name, imp in sorted(zip(FEATURE_NAMES, importances), key=lambda x: -x[1]):
                logger.info(f"  {name}: {imp:.4f}")
            break
        except Exception as e:
            logger.debug(f"Importance type {imp_type} failed: {e}")

    return model, avg_ndcg


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Train LTR ranker with real search scores")
    parser.add_argument("--ste-file", required=True)
    parser.add_argument("--contracts-file", required=True)
    parser.add_argument("--max-users", type=int, default=1000)
    parser.add_argument("--queries-per-user", type=int, default=5)
    parser.add_argument("--top-k", type=int, default=100)
    parser.add_argument("--skip-embeddings-cache", action="store_true")
    args = parser.parse_args()

    t0 = time.time()

    ste_df, contracts_df = load_data(args.ste_file, args.contracts_file)

    ste_ids = ste_df["ste_id_int"].values
    ste_names = ste_df["name"].values.tolist()
    ste_categories = dict(zip(ste_df["ste_id_int"], ste_df["category"].fillna("")))
    ste_id_to_idx = {sid: i for i, sid in enumerate(ste_ids)}

    if args.skip_embeddings_cache and EMBEDDING_CACHE.exists():
        EMBEDDING_CACHE.unlink()

    nlp = init_nlp()
    logger.info(f"Tokenizing {len(ste_names)} STE names for BM25 (takes ~5 min)...")
    tokenized = []
    for i, name in enumerate(ste_names):
        tokenized.append(nlp.lemmatize(name) or [""])
        if (i + 1) % 100000 == 0:
            logger.info(f"  tokenized {i+1}/{len(ste_names)}")
    bm25_index = build_bm25_index(tokenized)

    embeddings_norm = compute_or_load_embeddings(ste_names)

    users, pop_map = build_users(contracts_df, ste_categories, ste_id_to_idx, embeddings_norm)

    X, y, groups = generate_training_data(
        users, bm25_index, embeddings_norm, nlp,
        ste_ids, ste_names, ste_categories, ste_id_to_idx, pop_map,
        max_users=args.max_users,
        queries_per_user=args.queries_per_user,
        top_k=args.top_k,
    )

    save_training_data(X, y, groups, DATA_DIR / "train_pairs.csv")
    model, ndcg = train_catboost(X, y, groups)

    elapsed = time.time() - t0
    logger.info(f"Done in {elapsed:.1f}s | Val NDCG@10={ndcg:.4f}")


if __name__ == "__main__":
    main()
