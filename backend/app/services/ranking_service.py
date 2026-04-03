"""
Learning-to-Rank Service.
Supports three backends (tried in order):
  1. CatBoost (best quality, trained on contract pseudo-labels)
  2. JAX neural ranker (JIT-compiled, fast inference)
  3. Linear weighted fallback (no training required)

Feature set (11 features):
  bm25_score, semantic_score, category_match, category_weight,
  profile_similarity, popularity_score, name_length,
  is_previously_purchased, is_negative_signal,
  total_user_contracts, session_click_count
"""
import numpy as np
from pathlib import Path
from loguru import logger

from app.services.search_service import SearchResult
from app.services.personalization_service import UserContext

FEATURE_NAMES = [
    "bm25_score", "semantic_score", "category_match", "category_weight",
    "profile_similarity", "popularity_score", "name_length",
    "is_previously_purchased", "is_negative_signal",
    "total_user_contracts", "session_click_count",
]

_MODEL_DIR = Path(__file__).parent.parent / "data"


class RankingService:
    def __init__(self):
        self._catboost_model = None
        self._jax_ranker = None
        self._feature_weights = np.array([
            0.25, 0.30, 0.10, 0.08, 0.10,
            0.05, 0.02, 0.05, -0.10, 0.02, 0.03,
        ])
        self._backend = "linear"
        self._try_load_models()

    def _try_load_models(self):
        cbm_path = _MODEL_DIR / "catboost_ranker.cbm"
        if cbm_path.exists():
            try:
                from catboost import CatBoostRanker
                self._catboost_model = CatBoostRanker()
                self._catboost_model.load_model(str(cbm_path))
                self._backend = "catboost"
                logger.info("Loaded CatBoost ranker")
                return
            except Exception as e:
                logger.warning(f"Failed to load CatBoost: {e}")

        jax_path = _MODEL_DIR / "jax_ranker.npz"
        if jax_path.exists():
            try:
                from app.services.jax_ranker import JaxNeuralRanker, JAX_AVAILABLE
                if JAX_AVAILABLE:
                    self._jax_ranker = JaxNeuralRanker()
                    if self._jax_ranker.load(str(jax_path)):
                        self._backend = "jax"
                        logger.info("Loaded JAX neural ranker")
                        return
            except Exception as e:
                logger.warning(f"Failed to load JAX ranker: {e}")

        logger.info("Using linear weight fallback ranker")

    def extract_features(
        self,
        result: SearchResult,
        user_ctx: UserContext | None,
        ste_embedding: np.ndarray | None = None,
        popularity: float = 0.0,
    ) -> np.ndarray:
        cat_match = 0.0
        cat_weight = 0.0
        profile_sim = 0.0
        is_purchased = 0.0
        is_negative = 0.0
        total_contracts = 0.0
        session_clicks = 0.0

        if user_ctx:
            if result.category and result.category in user_ctx.category_weights:
                cat_match = 1.0
                cat_weight = user_ctx.category_weights[result.category]
            if user_ctx.profile_embedding is not None and ste_embedding is not None:
                profile_sim = float(np.dot(user_ctx.profile_embedding, ste_embedding))
            is_purchased = 1.0 if result.ste_id in user_ctx.positive_ste_ids else 0.0
            is_negative = 1.0 if result.ste_id in user_ctx.negative_ste_ids else 0.0
            total_contracts = min(user_ctx.interaction_count / 100.0, 1.0)
            session_clicks = min(len(user_ctx.session_clicks) / 20.0, 1.0)

        return np.array([
            result.bm25_score, result.semantic_score,
            cat_match, cat_weight, profile_sim,
            min(popularity, 1.0), min(len(result.name) / 100.0, 1.0),
            is_purchased, is_negative,
            total_contracts, session_clicks,
        ], dtype=np.float32)

    def score(self, features: np.ndarray) -> float:
        if self._backend == "catboost" and self._catboost_model is not None:
            return float(self._catboost_model.predict([features])[0])
        if self._backend == "jax" and self._jax_ranker is not None:
            return self._jax_ranker.predict(features)
        return float(np.dot(self._feature_weights, features))

    def score_batch(self, features_batch: np.ndarray) -> np.ndarray:
        if self._backend == "catboost" and self._catboost_model is not None:
            return self._catboost_model.predict(features_batch)
        if self._backend == "jax" and self._jax_ranker is not None:
            return self._jax_ranker.predict_batch(features_batch)
        return features_batch @ self._feature_weights

    def rerank(
        self,
        results: list[SearchResult],
        user_ctx: UserContext | None,
        ste_embeddings: dict[int, np.ndarray] | None = None,
        popularity_map: dict[int, float] | None = None,
    ) -> list[SearchResult]:
        if not results:
            return results

        features_batch = np.zeros((len(results), len(FEATURE_NAMES)), dtype=np.float32)
        for i, r in enumerate(results):
            emb = ste_embeddings.get(r.ste_id) if ste_embeddings else None
            pop = popularity_map.get(r.ste_id, 0.0) if popularity_map else 0.0
            features_batch[i] = self.extract_features(r, user_ctx, emb, pop)

        scores = self.score_batch(features_batch)

        for i, r in enumerate(results):
            r.final_score = float(scores[i])
            if self._backend != "linear":
                r.explanations.append(f"Ranked by {self._backend} model")

        results.sort(key=lambda r: r.final_score, reverse=True)
        return results

    def get_backend_info(self) -> dict:
        return {"backend": self._backend, "features": FEATURE_NAMES}


_ranking_service: RankingService | None = None


def get_ranking_service() -> RankingService:
    global _ranking_service
    if _ranking_service is None:
        _ranking_service = RankingService()
    return _ranking_service


