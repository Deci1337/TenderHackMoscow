"""
Search Quality Metrics Module.

Metrics selected and justified for personalized procurement search:

1. NDCG@K (Normalized Discounted Cumulative Gain)
   - WHY: The primary metric. Measures ranking quality accounting for graded relevance.
     A user finding the right STE at position 1 is exponentially more valuable than
     position 10. NDCG naturally handles this with logarithmic discount.
   - K values: 5, 10, 20 (typical page sizes in procurement catalogs)

2. MRR (Mean Reciprocal Rank)
   - WHY: Measures how quickly the user finds the FIRST relevant result.
     Critical for procurement -- users often need one specific STE, not a list.
     High MRR = less time wasted scrolling.

3. MAP (Mean Average Precision)
   - WHY: Evaluates precision at each recall level. In procurement, users may need
     multiple relevant STEs (e.g., comparing options). MAP rewards systems that
     cluster relevant results near the top across all relevant items.

4. Precision@K
   - WHY: Simple and interpretable. "Of the top K results, how many are relevant?"
     Directly maps to user experience -- if P@5 = 0.8, 4 out of 5 top results
     are useful. Stakeholders understand this immediately.

5. Click-Through Rate (CTR) delta
   - WHY: Behavioral metric. Measures if personalization increases click rate on
     search results. Positive CTR delta after personalization = system is surfacing
     more relevant items for this specific user.

6. Bounce Rate delta
   - WHY: Negative behavioral signal metric. If a user clicks a result and returns
     quickly (< 3 seconds), the result was misleading. Lower bounce rate =
     better semantic understanding of user intent.

7. Personalization Lift
   - WHY: Compares NDCG of personalized search vs non-personalized baseline.
     Directly measures the value of the personalization layer. If lift < 0,
     personalization is hurting quality and should be disabled for that user.
"""
import numpy as np
from loguru import logger


def dcg_at_k(relevances: list[float], k: int) -> float:
    """Discounted Cumulative Gain at position k."""
    relevances = relevances[:k]
    return sum(rel / np.log2(i + 2) for i, rel in enumerate(relevances))


def ndcg_at_k(relevances: list[float], k: int) -> float:
    """Normalized DCG@K. Returns 0-1 score."""
    actual_dcg = dcg_at_k(relevances, k)
    ideal_dcg = dcg_at_k(sorted(relevances, reverse=True), k)
    return actual_dcg / ideal_dcg if ideal_dcg > 0 else 0.0


def mrr(ranked_relevances: list[list[float]]) -> float:
    """Mean Reciprocal Rank across multiple queries."""
    rrs = []
    for rels in ranked_relevances:
        for i, rel in enumerate(rels):
            if rel > 0:
                rrs.append(1.0 / (i + 1))
                break
        else:
            rrs.append(0.0)
    return np.mean(rrs) if rrs else 0.0


def average_precision(relevances: list[float]) -> float:
    """Average Precision for a single query."""
    hits = 0
    sum_precisions = 0.0
    for i, rel in enumerate(relevances):
        if rel > 0:
            hits += 1
            sum_precisions += hits / (i + 1)
    return sum_precisions / hits if hits > 0 else 0.0


def mean_average_precision(ranked_relevances: list[list[float]]) -> float:
    """MAP across multiple queries."""
    return float(np.mean([average_precision(rels) for rels in ranked_relevances]))


def precision_at_k(relevances: list[float], k: int) -> float:
    """Precision at position k."""
    top_k = relevances[:k]
    return sum(1 for r in top_k if r > 0) / k if k > 0 else 0.0


def personalization_lift(
    ndcg_personalized: float,
    ndcg_baseline: float,
) -> float:
    """Measures relative improvement from personalization."""
    if ndcg_baseline == 0:
        return 0.0
    return (ndcg_personalized - ndcg_baseline) / ndcg_baseline


def evaluate_search(
    relevance_judgments: list[list[float]],
    k_values: list[int] | None = None,
) -> dict[str, float]:
    """Run all metrics on a set of ranked results with relevance judgments."""
    if k_values is None:
        k_values = [5, 10, 20]

    metrics = {}
    for k in k_values:
        ndcgs = [ndcg_at_k(rels, k) for rels in relevance_judgments]
        metrics[f"NDCG@{k}"] = float(np.mean(ndcgs))
        precs = [precision_at_k(rels, k) for rels in relevance_judgments]
        metrics[f"P@{k}"] = float(np.mean(precs))

    metrics["MRR"] = mrr(relevance_judgments)
    metrics["MAP"] = mean_average_precision(relevance_judgments)

    return metrics


METRICS_JUSTIFICATION = {
    "NDCG@K": {
        "name": "Normalized Discounted Cumulative Gain",
        "rationale": (
            "Primary ranking quality metric. Accounts for position-dependent value "
            "of results using logarithmic discounting. Essential for graded relevance "
            "where some STEs are more relevant than others for a given procurement query."
        ),
        "range": "0 to 1 (1 = perfect ranking)",
    },
    "MRR": {
        "name": "Mean Reciprocal Rank",
        "rationale": (
            "Measures how quickly users find the first relevant result. Critical for "
            "procurement search where users often seek a single specific STE. "
            "High MRR means less wasted time."
        ),
        "range": "0 to 1 (1 = first result always relevant)",
    },
    "MAP": {
        "name": "Mean Average Precision",
        "rationale": (
            "Evaluates precision at each recall level. Important when users compare "
            "multiple STEs. Rewards clustering of all relevant results near the top."
        ),
        "range": "0 to 1",
    },
    "Precision@K": {
        "name": "Precision at K",
        "rationale": (
            "Most interpretable metric: fraction of top-K results that are relevant. "
            "Directly measures user-visible quality on a single results page."
        ),
        "range": "0 to 1",
    },
    "CTR_delta": {
        "name": "Click-Through Rate Delta",
        "rationale": (
            "Behavioral metric measuring increased engagement from personalization. "
            "Positive delta confirms the system surfaces more relevant items."
        ),
        "range": "Negative to positive percentage",
    },
    "Bounce_rate_delta": {
        "name": "Bounce Rate Delta",
        "rationale": (
            "Negative signal metric. Measures reduction in quick-return behavior. "
            "Lower bounce rate = better semantic match between query intent and results."
        ),
        "range": "Negative is better",
    },
    "Personalization_lift": {
        "name": "Personalization Lift",
        "rationale": (
            "Directly measures the incremental value of personalization by comparing "
            "NDCG with and without user profile. If negative, personalization should "
            "be disabled for that user segment."
        ),
        "range": "Percentage improvement over baseline",
    },
}
