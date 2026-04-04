"""
Personalization & Dynamic Indexing Service.

Maintains per-user profiles built from:
  1. Contract history (static baseline)
  2. Real-time behavioral signals (dynamic adjustment)

User profile is represented as:
  - Category preference vector (weighted distribution of purchased categories)
  - Embedding centroid (average embedding of interacted STEs)
  - Negative signal set (STEs the user bounced from)

Dynamic indexing: after each interaction event, the profile is updated in-place
and the next search reflects the change immediately.
"""
import json
import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from loguru import logger

from app.config import get_settings
from app.services.search_service import SearchResult


ACTION_WEIGHTS = {
    "purchase": 5.0,
    "add_to_compare": 3.0,
    "click": 1.0,
    "view": 0.5,
    "bounce": -2.0,
}


@dataclass
class UserContext:
    customer_inn: str
    category_weights: dict[str, float] = field(default_factory=dict)
    profile_embedding: np.ndarray | None = None
    negative_ste_ids: set[int] = field(default_factory=set)
    positive_ste_ids: set[int] = field(default_factory=set)
    interaction_count: int = 0
    session_clicks: list[int] = field(default_factory=list)


class PersonalizationService:
    def __init__(self):
        self._profiles: dict[str, UserContext] = {}

    def get_or_create_profile(self, customer_inn: str) -> UserContext:
        if customer_inn not in self._profiles:
            self._profiles[customer_inn] = UserContext(customer_inn=customer_inn)
        return self._profiles[customer_inn]

    def build_profile_from_contracts(
        self,
        customer_inn: str,
        categories: list[str],
        ste_embeddings: dict[int, np.ndarray],
        purchased_ste_ids: list[int],
    ):
        """Initialize user profile from historical contract data."""
        ctx = self.get_or_create_profile(customer_inn)

        cat_counts: dict[str, float] = defaultdict(float)
        for cat in categories:
            if cat:
                cat_counts[cat] += 1.0
        total = sum(cat_counts.values()) or 1.0
        ctx.category_weights = {k: v / total for k, v in cat_counts.items()}

        vecs = [ste_embeddings[sid] for sid in purchased_ste_ids if sid in ste_embeddings]
        if vecs:
            centroid = np.mean(vecs, axis=0)
            ctx.profile_embedding = centroid / (np.linalg.norm(centroid) + 1e-9)

        ctx.positive_ste_ids = set(purchased_ste_ids)
        ctx.interaction_count = len(purchased_ste_ids)
        logger.debug(f"Profile built for {customer_inn}: {len(ctx.category_weights)} categories")

    def record_interaction(
        self,
        customer_inn: str,
        ste_id: int,
        action: str,
        ste_embedding: np.ndarray | None = None,
        ste_category: str | None = None,
    ):
        """Update profile in real-time based on behavioral signal."""
        ctx = self.get_or_create_profile(customer_inn)
        weight = ACTION_WEIGHTS.get(action, 0.0)

        if action == "bounce":
            ctx.negative_ste_ids.add(ste_id)
            ctx.session_clicks = [sid for sid in ctx.session_clicks if sid != ste_id]
        elif action in ("click", "add_to_compare", "purchase"):
            ctx.positive_ste_ids.add(ste_id)
            ctx.session_clicks.append(ste_id)
            ctx.negative_ste_ids.discard(ste_id)

        if ste_category and weight > 0:
            current = ctx.category_weights.get(ste_category, 0.0)
            ctx.category_weights[ste_category] = current + weight * 0.1
            total = sum(ctx.category_weights.values()) or 1.0
            ctx.category_weights = {k: v / total for k, v in ctx.category_weights.items()}

        if ste_embedding is not None and weight > 0:
            if ctx.profile_embedding is not None:
                decay = 0.9
                new_vec = decay * ctx.profile_embedding + (1 - decay) * ste_embedding
                ctx.profile_embedding = new_vec / (np.linalg.norm(new_vec) + 1e-9)
            else:
                ctx.profile_embedding = ste_embedding

        ctx.interaction_count += 1

    def rerank(
        self,
        results: list[SearchResult],
        customer_inn: str | None,
        ste_embeddings: dict[int, np.ndarray] | None = None,
    ) -> list[SearchResult]:
        """Apply personalization boost/penalty to base search results."""
        if not customer_inn:
            return results

        ctx = self._profiles.get(customer_inn)
        if not ctx or ctx.interaction_count == 0:
            return results

        settings = get_settings()
        boost = settings.PERSONALIZATION_BOOST

        for r in results:
            p_score = 0.0
            reasons = []

            if r.category and r.category in ctx.category_weights:
                cat_boost = ctx.category_weights[r.category] * boost
                p_score += cat_boost
                pct = int(ctx.category_weights[r.category] * 100)
                reasons.append(f"Matches your frequent category '{r.category}' ({pct}% of purchases)")

            if ctx.profile_embedding is not None and ste_embeddings and r.ste_id in ste_embeddings:
                profile_sim = float(np.dot(ctx.profile_embedding, ste_embeddings[r.ste_id]))
                p_score += profile_sim * boost * 0.5
                if profile_sim > 0.5:
                    reasons.append("Similar to your purchase history profile")

            if r.ste_id in ctx.positive_ste_ids:
                p_score += boost * 0.3
                reasons.append("Previously purchased item")

            if r.ste_id in ctx.negative_ste_ids:
                p_score -= boost * settings.NEGATIVE_SIGNAL_DECAY
                reasons.append("Ranked lower: you quickly returned from this item")

            r.personalization_score = p_score
            r.final_score += p_score
            r.explanations.extend(reasons)

        results.sort(key=lambda r: r.final_score, reverse=True)
        return results

    def get_profile_summary(self, customer_inn: str) -> dict:
        ctx = self._profiles.get(customer_inn)
        if not ctx:
            return self._db_fallback_summary(customer_inn)
        top_cats = sorted(ctx.category_weights.items(), key=lambda x: -x[1])[:5]
        return {
            "customer_inn": customer_inn,
            "status": "active",
            "top_categories": [{"category": k, "weight": round(v, 3)} for k, v in top_cats],
            "total_categories": len(ctx.category_weights),
            "interaction_count": ctx.interaction_count,
            "positive_items": len(ctx.positive_ste_ids),
            "negative_signals": len(ctx.negative_ste_ids),
            "session_clicks": len(ctx.session_clicks),
            "has_embedding": ctx.profile_embedding is not None,
        }

    @staticmethod
    def _db_fallback_summary(customer_inn: str) -> dict:
        """Try loading profile from DB when not in memory (cold start fallback)."""
        try:
            from app.database import SessionLocal
            from app.models import Contract
            from sqlalchemy import func, select
            import asyncio

            async def _load():
                async with SessionLocal() as session:
                    q = (
                        select(
                            func.count(Contract.id).label("cnt"),
                            Contract.customer_region,
                        )
                        .where(Contract.customer_inn == customer_inn)
                        .group_by(Contract.customer_region)
                    )
                    result = await session.execute(q)
                    rows = result.all()
                    if not rows:
                        return None
                    total = sum(r.cnt for r in rows)
                    region = rows[0].customer_region if rows else None
                    return {"total": total, "region": region}

            loop = asyncio.get_event_loop()
            if loop.is_running():
                return {"customer_inn": customer_inn, "status": "no_profile"}
            data = loop.run_until_complete(_load())
            if data:
                return {
                    "customer_inn": customer_inn,
                    "status": "db_fallback",
                    "interaction_count": data["total"],
                    "region": data["region"],
                }
        except Exception:
            pass
        return {"customer_inn": customer_inn, "status": "no_profile"}


_personalization_service: PersonalizationService | None = None


def get_personalization_service() -> PersonalizationService:
    global _personalization_service
    if _personalization_service is None:
        _personalization_service = PersonalizationService()
    return _personalization_service
