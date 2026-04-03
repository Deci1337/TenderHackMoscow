"""
Explainability Service: provides human-readable reasons for search ranking.

Two levels:
  1. Rule-based: generated from feature values and personalization signals
  2. SHAP-based: feature importance from the CatBoost model (when available)

Every search result carries an 'explanations' list visible to the user.
"""
import numpy as np
from loguru import logger

from app.services.search_service import SearchResult
from app.services.ranking_service import RankingService, FEATURE_NAMES


FEATURE_EXPLANATIONS = {
    "bm25_score": "Exact keyword match in product name",
    "semantic_score": "Semantic meaning similarity to your query",
    "category_match": "Product category matches your purchase history",
    "category_weight": "Frequently purchased product category",
    "profile_similarity": "Similar to products you've bought before",
    "popularity_score": "Popular product among all buyers",
    "name_length": "Specific product description",
    "is_previously_purchased": "You have purchased this product before",
    "is_negative_signal": "You previously showed disinterest in this product",
    "total_user_contracts": "Adjusted for your experience level",
    "session_click_count": "Adjusted based on your current session activity",
}


class ExplainabilityService:
    def __init__(self):
        self._shap_explainer = None

    def explain_result(
        self,
        result: SearchResult,
        features: np.ndarray | None = None,
        ranker: RankingService | None = None,
    ) -> list[str]:
        """Generate human-readable explanations for a single result."""
        explanations = list(result.explanations)

        if features is not None:
            if ranker and ranker._model is not None:
                shap_explanations = self._shap_explain(features, ranker)
                explanations.extend(shap_explanations)
            else:
                rule_explanations = self._rule_explain(features)
                explanations.extend(rule_explanations)

        return list(dict.fromkeys(explanations))

    def _rule_explain(self, features: np.ndarray) -> list[str]:
        """Rule-based explanations from feature values."""
        explanations = []
        for i, (fname, fval) in enumerate(zip(FEATURE_NAMES, features)):
            if fname == "is_negative_signal" and fval > 0.5:
                explanations.append(FEATURE_EXPLANATIONS[fname])
                continue
            if fval > 0.5 and fname in FEATURE_EXPLANATIONS:
                explanations.append(FEATURE_EXPLANATIONS[fname])
        return explanations

    def _shap_explain(self, features: np.ndarray, ranker: RankingService) -> list[str]:
        """SHAP-based explanations from CatBoost model."""
        try:
            import shap
            if self._shap_explainer is None:
                self._shap_explainer = shap.TreeExplainer(ranker._model)
            shap_values = self._shap_explainer.shap_values(features.reshape(1, -1))
            top_indices = np.argsort(np.abs(shap_values[0]))[-3:][::-1]
            explanations = []
            for idx in top_indices:
                fname = FEATURE_NAMES[idx]
                direction = "positive" if shap_values[0][idx] > 0 else "negative"
                if fname in FEATURE_EXPLANATIONS:
                    prefix = "+" if direction == "positive" else "-"
                    explanations.append(f"{prefix} {FEATURE_EXPLANATIONS[fname]}")
            return explanations
        except Exception as e:
            logger.debug(f"SHAP explanation failed: {e}")
            return self._rule_explain(features)

    def compare_sessions(
        self,
        results_before: list[SearchResult],
        results_after: list[SearchResult],
    ) -> list[str]:
        """Explain why results differ between two sessions (before/after interaction)."""
        changes = []
        before_ids = [r.ste_id for r in results_before[:10]]
        after_ids = [r.ste_id for r in results_after[:10]]

        new_in_top = set(after_ids) - set(before_ids)
        dropped = set(before_ids) - set(after_ids)

        if new_in_top:
            names_map = {r.ste_id: r.name for r in results_after}
            for sid in list(new_in_top)[:3]:
                name = names_map.get(sid, str(sid))
                changes.append(f"'{name}' moved up based on your recent activity")

        if dropped:
            names_map = {r.ste_id: r.name for r in results_before}
            for sid in list(dropped)[:3]:
                name = names_map.get(sid, str(sid))
                changes.append(f"'{name}' ranked lower due to negative interaction signal")

        return changes


_explainability_service: ExplainabilityService | None = None


def get_explainability_service() -> ExplainabilityService:
    global _explainability_service
    if _explainability_service is None:
        _explainability_service = ExplainabilityService()
    return _explainability_service
