"""
Offline evaluation: BM25-only vs Semantic-only vs Hybrid vs Hybrid+CatBoost.

Uses real STE data + contract history to build ground-truth sets.
For each test query (a purchased item name), relevant items are:
  - Other items purchased by the same user (strongest signal)
  - Items from the same category (weaker signal)

Outputs a comparison table for the hackathon presentation.
"""
import sys
import time
import argparse
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

STE_COLS = ["ste_id", "name", "category", "attributes"]
CONTRACT_COLS = [
    "purchase_name", "contract_id", "ste_id", "contract_date",
    "contract_cost", "customer_inn", "customer_name", "customer_region",
    "supplier_inn", "supplier_name", "supplier_region",
]
DATA_DIR = Path(__file__).parent.parent / "app" / "data"


def ndcg_at_k(ranked_ids: list[int], relevant_map: dict[int, float], k: int = 10) -> float:
    """NDCG@K with graded relevance."""
    rels = [relevant_map.get(sid, 0.0) for sid in ranked_ids[:k]]
    dcg = sum(r / np.log2(i + 2) for i, r in enumerate(rels))
    ideal_rels = sorted(relevant_map.values(), reverse=True)[:k]
    idcg = sum(r / np.log2(i + 2) for i, r in enumerate(ideal_rels))
    return dcg / idcg if idcg > 0 else 0.0


def mrr(ranked_ids: list[int], relevant_ids: set[int]) -> float:
    for i, sid in enumerate(ranked_ids):
        if sid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def precision_at_k(ranked_ids: list[int], relevant_ids: set[int], k: int = 5) -> float:
    hits = sum(1 for sid in ranked_ids[:k] if sid in relevant_ids)
    return hits / k


def build_test_queries(ste_df, contracts_df, n_queries=50, seed=123):
    """Build test queries from real purchase data with graded relevance."""
    rng = np.random.default_rng(seed)

    ste_categories = dict(zip(ste_df["ste_id_int"], ste_df["category"].fillna("")))
    ste_names = dict(zip(ste_df["ste_id_int"], ste_df["name"].fillna("")))

    user_purchases = defaultdict(set)
    for _, row in contracts_df.iterrows():
        inn = str(row["customer_inn"]).strip()
        try:
            sid = int(row["ste_id"])
        except (ValueError, TypeError):
            continue
        if inn and inn != "nan" and sid in ste_names:
            user_purchases[inn].add(sid)

    eligible = [(inn, sids) for inn, sids in user_purchases.items() if 10 <= len(sids) <= 500]
    if not eligible:
        logger.warning("No eligible users for test queries")
        return []

    rng.shuffle(eligible)
    queries = []

    for inn, purchased in eligible[:n_queries * 2]:
        purchased_list = list(purchased)
        query_sid = rng.choice(purchased_list)
        q_name = ste_names.get(query_sid, "")
        q_cat = ste_categories.get(query_sid, "")
        if not q_name or len(q_name) < 5:
            continue

        relevant_map = {}
        relevant_ids = set()
        for sid in purchased:
            if sid == query_sid:
                continue
            relevant_map[sid] = 3.0
            relevant_ids.add(sid)

        cat_group = ste_df[ste_df["category"] == q_cat] if q_cat else pd.DataFrame()
        for sid in cat_group["ste_id_int"].values[:100]:
            if sid not in relevant_map and sid != query_sid:
                relevant_map[sid] = 1.0
                relevant_ids.add(sid)

        if len(relevant_ids) < 3:
            continue

        queries.append({
            "query": q_name,
            "query_ste_id": query_sid,
            "relevant_map": relevant_map,
            "relevant_ids": relevant_ids,
            "category": q_cat,
            "customer_inn": inn,
        })

        if len(queries) >= n_queries:
            break

    logger.info(f"Built {len(queries)} test queries with graded relevance")
    return queries


def evaluate_bm25(bm25_index, tokenized_names, nlp, ste_ids, queries, k=10):
    results = []
    for q in queries:
        tokens = nlp.lemmatize(q["query"])
        if not tokens:
            continue
        scores = bm25_index.get_scores(tokens)
        top_idxs = np.argsort(scores)[-k:][::-1]
        ranked = [int(ste_ids[i]) for i in top_idxs if scores[i] > 0]

        results.append({
            "ndcg@10": ndcg_at_k(ranked, q["relevant_map"], k),
            "mrr": mrr(ranked, q["relevant_ids"]),
            "p@5": precision_at_k(ranked, q["relevant_ids"], 5),
        })
    return _agg(results)


def evaluate_semantic(embeddings_norm, nlp, ste_ids, queries, k=10):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("cointegrated/rubert-tiny2")

    results = []
    for q in queries:
        q_emb = model.encode([q["query"]], normalize_embeddings=True)[0]
        scores = embeddings_norm @ q_emb
        top_idxs = np.argsort(scores)[-k:][::-1]
        ranked = [int(ste_ids[i]) for i in top_idxs]

        results.append({
            "ndcg@10": ndcg_at_k(ranked, q["relevant_map"], k),
            "mrr": mrr(ranked, q["relevant_ids"]),
            "p@5": precision_at_k(ranked, q["relevant_ids"], 5),
        })
    return _agg(results)


def evaluate_hybrid(bm25_index, embeddings_norm, nlp, ste_ids, queries, k=10, alpha=0.5):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("cointegrated/rubert-tiny2")

    results = []
    for q in queries:
        tokens = nlp.lemmatize(q["query"])
        if not tokens:
            continue

        bm25_scores = bm25_index.get_scores(tokens)
        bm25_max = bm25_scores.max() or 1.0
        bm25_norm = bm25_scores / bm25_max

        q_emb = model.encode([q["query"]], normalize_embeddings=True)[0]
        sem_scores = embeddings_norm @ q_emb

        hybrid = alpha * bm25_norm + (1 - alpha) * sem_scores
        top_idxs = np.argsort(hybrid)[-k:][::-1]
        ranked = [int(ste_ids[i]) for i in top_idxs]

        results.append({
            "ndcg@10": ndcg_at_k(ranked, q["relevant_map"], k),
            "mrr": mrr(ranked, q["relevant_ids"]),
            "p@5": precision_at_k(ranked, q["relevant_ids"], 5),
        })
    return _agg(results)


def evaluate_hybrid_catboost(
    bm25_index, embeddings_norm, nlp, ste_ids, ste_categories,
    ste_id_to_idx, pop_map, queries, k=10, alpha=0.5,
):
    from sentence_transformers import SentenceTransformer
    from catboost import CatBoostRanker

    model_path = DATA_DIR / "catboost_ranker.cbm"
    if not model_path.exists():
        logger.warning("No CatBoost model found, skipping")
        return None

    ranker = CatBoostRanker()
    ranker.load_model(str(model_path))
    st_model = SentenceTransformer("cointegrated/rubert-tiny2")

    results = []
    for q in queries:
        tokens = nlp.lemmatize(q["query"])
        if not tokens:
            continue

        bm25_scores = bm25_index.get_scores(tokens)
        bm25_max = bm25_scores.max() or 1.0
        bm25_norm = bm25_scores / bm25_max

        q_emb = st_model.encode([q["query"]], normalize_embeddings=True)[0]
        sem_scores = embeddings_norm @ q_emb

        hybrid = alpha * bm25_norm + (1 - alpha) * sem_scores
        candidate_idxs = np.argsort(hybrid)[-(k * 5):][::-1]

        features_batch = []
        candidate_sids = []
        for c_idx in candidate_idxs:
            c_sid = int(ste_ids[c_idx])
            c_cat = ste_categories.get(c_sid, "")
            bm25_f = float(bm25_norm[c_idx])
            sem_f = float(sem_scores[c_idx])
            pop = float(pop_map.get(str(c_sid), 0.0))
            name_len = min(len(str(c_sid)) / 100.0, 1.0)

            features_batch.append([
                bm25_f, sem_f, 0.0, 0.0, 0.0,
                min(pop, 1.0), name_len,
                0.0, 0.0, 0.0, 0.0,
            ])
            candidate_sids.append(c_sid)

        if not features_batch:
            continue

        cb_scores = ranker.predict(np.array(features_batch, dtype=np.float32))
        reranked_order = np.argsort(-cb_scores)[:k]
        ranked = [candidate_sids[i] for i in reranked_order]

        results.append({
            "ndcg@10": ndcg_at_k(ranked, q["relevant_map"], k),
            "mrr": mrr(ranked, q["relevant_ids"]),
            "p@5": precision_at_k(ranked, q["relevant_ids"], 5),
        })
    return _agg(results)


def _agg(results):
    if not results:
        return {"ndcg@10": 0.0, "mrr": 0.0, "p@5": 0.0}
    return {
        "ndcg@10": float(np.mean([r["ndcg@10"] for r in results])),
        "mrr": float(np.mean([r["mrr"] for r in results])),
        "p@5": float(np.mean([r["p@5"] for r in results])),
    }


def print_table(all_results: dict[str, dict]):
    header = f"{'Strategy':<30} {'NDCG@10':>8} {'MRR':>8} {'P@5':>8}"
    sep = "=" * len(header)
    logger.info(sep)
    logger.info(header)
    logger.info("-" * len(header))
    for strategy, metrics in all_results.items():
        if metrics is None:
            continue
        logger.info(
            f"{strategy:<30} {metrics['ndcg@10']:>8.4f} {metrics['mrr']:>8.4f} {metrics['p@5']:>8.4f}"
        )
    logger.info(sep)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ste-file", required=True)
    parser.add_argument("--contracts-file", required=True)
    parser.add_argument("--n-queries", type=int, default=50)
    args = parser.parse_args()

    t0 = time.time()

    logger.info("Loading data...")
    ste_df = pd.read_csv(args.ste_file, sep=";", header=None, names=STE_COLS, dtype={"ste_id": str})
    ste_df = ste_df.drop_duplicates(subset="ste_id", keep="first")
    ste_df["ste_id_int"] = ste_df["ste_id"].astype(int)
    ste_df["name"] = ste_df["name"].fillna("")

    contracts_df = pd.read_csv(
        args.contracts_file, sep=";", header=None, names=CONTRACT_COLS,
        dtype={"ste_id": str, "customer_inn": str}, low_memory=False,
    )

    ste_ids = ste_df["ste_id_int"].values
    ste_names = ste_df["name"].values.tolist()
    ste_categories = dict(zip(ste_df["ste_id_int"], ste_df["category"].fillna("")))
    ste_id_to_idx = {sid: i for i, sid in enumerate(ste_ids)}

    pop_counts = contracts_df["ste_id"].value_counts()
    max_pop = pop_counts.max() or 1
    pop_map = (pop_counts / max_pop).to_dict()

    logger.info("Initializing NLP...")
    from app.services.nlp_service import NLPService
    nlp = NLPService()
    nlp.initialize()

    logger.info("Building BM25 index...")
    from rank_bm25 import BM25Okapi
    tokenized = [nlp.lemmatize(name) or [""] for name in ste_names]
    bm25_index = BM25Okapi(tokenized)

    logger.info("Loading embeddings...")
    emb_cache = DATA_DIR / "ste_embeddings_cache.npy"
    if emb_cache.exists():
        embeddings_norm = np.load(emb_cache)
        logger.info(f"Loaded cached embeddings: {embeddings_norm.shape}")
    else:
        logger.warning("No cached embeddings. Run train_ranker.py first to compute them.")
        embeddings_norm = None

    test_queries = build_test_queries(ste_df, contracts_df, n_queries=args.n_queries)
    if not test_queries:
        logger.error("No test queries generated")
        return

    all_results = {}

    logger.info("Evaluating BM25-only...")
    all_results["BM25 only"] = evaluate_bm25(bm25_index, tokenized, nlp, ste_ids, test_queries)

    if embeddings_norm is not None:
        logger.info("Evaluating Semantic-only...")
        all_results["Semantic only"] = evaluate_semantic(embeddings_norm, nlp, ste_ids, test_queries)

        logger.info("Evaluating Hybrid (alpha=0.5)...")
        all_results["Hybrid (a=0.5)"] = evaluate_hybrid(
            bm25_index, embeddings_norm, nlp, ste_ids, test_queries, alpha=0.5,
        )

        logger.info("Evaluating Hybrid (alpha=0.7, BM25-heavy)...")
        all_results["Hybrid (a=0.7)"] = evaluate_hybrid(
            bm25_index, embeddings_norm, nlp, ste_ids, test_queries, alpha=0.7,
        )

        logger.info("Evaluating Hybrid + CatBoost...")
        cb_results = evaluate_hybrid_catboost(
            bm25_index, embeddings_norm, nlp, ste_ids, ste_categories,
            ste_id_to_idx, pop_map, test_queries,
        )
        if cb_results:
            all_results["Hybrid + CatBoost"] = cb_results

    print_table(all_results)
    logger.info(f"Evaluation done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
