"""
Learning-to-Rank Service with CatBoost.

Feature set for the ranker:
  User features:
    - category_match (bool): query result category in user's top categories
    - category_weight (float): weight of the category in user profile
    - profile_similarity (float): cosine sim between user profile embedding and STE embedding
    - total_contracts (int): user's total contract count (experience indicator)

  Item features:
    - popularity_score (float): global popularity of the STE
    - name_length (int): length of the STE name (longer = more specific)

  Query-Item features:
    - bm25_score (float): normalized BM25 score
    - semantic_score (float): normalized semantic similarity
    - is_previously_purchased (bool): user bought this before
    - is_negative_signal (bool): user bounced from this

  Interaction features:
    - session_click_rank (int): position in session click sequence (-1 if not clicked)
"""
import numpy as np
from dataclasses import dataclass
from loguru import logger

from app.services.search_service import SearchResult
from app.services.personalization_service import UserContext


FEATURE_NAMES = [
    "bm25_score",
    "semantic_score",
    "category_match",
    "category_weight",
    "profile_similarity",
    "popularity_score",
    "name_length",
    "is_previously_purchased",
    "is_negative_signal",
    "total_user_contracts",
    "session_click_count",
]


class RankingService:
    """
    Lightweight LTR ranker. In production, this would use a trained CatBoost model.
    For the hackathon MVP, we use a weighted linear combination that can be
    replaced with CatBoost once training data is collected.
    """

    def __init__(self):
        self._model = None
        self._feature_weights = np.array([
            0.25,   # bm25_score
            0.30,   # semantic_score
            0.10,   # category_match
            0.08,   # category_weight
            0.10,   # profile_similarity
            0.05,   # popularity_score
            0.02,   # name_length (normalized)
            0.05,   # is_previously_purchased
            -0.10,  # is_negative_signal
            0.02,   # total_user_contracts (normalized)
            0.03,   # session_click_count (normalized)
        ])

    def extract_features(
        self,
        result: SearchResult,
        user_ctx: UserContext | None,
        ste_embedding: np.ndarray | None = None,
        popularity: float = 0.0,
    ) -> np.ndarray:
        """Extract feature vector for a single (query, user, item) triple."""
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
            result.bm25_score,
            result.semantic_score,
            cat_match,
            cat_weight,
            profile_sim,
            min(popularity, 1.0),
            min(len(result.name) / 100.0, 1.0),
            is_purchased,
            is_negative,
            total_contracts,
            session_clicks,
        ])

    def score(self, features: np.ndarray) -> float:
        """Score a single feature vector."""
        if self._model is not None:
            return float(self._model.predict([features])[0])
        return float(np.dot(self._feature_weights, features))

    def rerank(
        self,
        results: list[SearchResult],
        user_ctx: UserContext | None,
        ste_embeddings: dict[int, np.ndarray] | None = None,
        popularity_map: dict[int, float] | None = None,
    ) -> list[SearchResult]:
        """Apply LTR model to rerank search results."""
        if not results:
            return results

        for r in results:
            emb = ste_embeddings.get(r.ste_id) if ste_embeddings else None
            pop = popularity_map.get(r.ste_id, 0.0) if popularity_map else 0.0
            features = self.extract_features(r, user_ctx, emb, pop)
            ltr_score = self.score(features)
            r.final_score = ltr_score

        results.sort(key=lambda r: r.final_score, reverse=True)
        return results

    def train_catboost(self, X: np.ndarray, y: np.ndarray, groups: np.ndarray):
        """
        Train CatBoost ranker on collected interaction data.
        X: feature matrix (n_samples, n_features)
        y: relevance labels (0-4 scale)
        groups: query group sizes
        """
        try:
            from catboost import CatBoostRanker, Pool
            train_pool = Pool(data=X, label=y, group_id=groups)
            model = CatBoostRanker(
                iterations=300,
                learning_rate=0.05,
                depth=6,
                loss_function="YetiRank",
                verbose=50,
            )
            model.fit(train_pool)
            self._model = model
            logger.info("CatBoost ranker trained successfully")
        except ImportError:
            logger.warning("CatBoost not available, using linear weights fallback")


_ranking_service: RankingService | None = None


def get_ranking_service() -> RankingService:
    global _ranking_service
    if _ranking_service is None:
        _ranking_service = RankingService()
    return _ranking_service
