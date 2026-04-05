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


    async def get_interest_summary(self, inn: str, db) -> dict:
        """
        Build user interest summary from contract history + live session + decay.
        Used by GET /users/{inn}/interests.
        """
        from sqlalchemy import text
        from datetime import datetime, timezone

        ctx = self._profiles.get(inn)
        now = datetime.now(timezone.utc)

        result = await db.execute(text("""
            SELECT s.category, COUNT(*) AS cnt
            FROM contracts c
            JOIN ste s ON c.ste_id = s.id
            WHERE c.customer_inn = :inn AND s.category IS NOT NULL
            GROUP BY s.category
            ORDER BY cnt DESC
            LIMIT 10
        """), {"inn": inn})
        contract_counts = {row.category: int(row.cnt) for row in result.fetchall()}

        result2 = await db.execute(text("""
            SELECT s.category, MAX(e.created_at) AS last_at
            FROM events e
            JOIN ste s ON e.ste_id = s.id
            WHERE e.user_inn = :inn AND s.category IS NOT NULL
            GROUP BY s.category
        """), {"inn": inn})
        last_interactions = {row.category: row.last_at for row in result2.fetchall()}

        all_cats = set(contract_counts.keys())
        if ctx:
            all_cats |= set(ctx.category_weights.keys())

        categories = []
        for cat in all_cats:
            contract_cnt = contract_counts.get(cat, 0)
            session_weight = ctx.category_weights.get(cat, 0.0) if ctx else 0.0

            last_dt = last_interactions.get(cat)
            if last_dt:
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                days_ago = (now - last_dt).days
            else:
                days_ago = 999

            base = min(contract_cnt / 50.0, 1.0)
            decay = max(0.0, 1.0 - days_ago / 30.0)
            weight = min(1.0, base * 0.6 + session_weight * 0.4) * (0.3 + 0.7 * decay)

            if session_weight > 0.3 and days_ago < 1:
                trend = "rising"
            elif days_ago > 14:
                trend = "fading"
            else:
                trend = "stable"

            categories.append({
                "category": cat,
                "click_count": 0,
                "contract_count": contract_cnt,
                "weight": round(weight, 3),
                "trend": trend,
                "last_interaction_days": days_ago if days_ago < 999 else -1,
            })

        categories.sort(key=lambda x: x["weight"], reverse=True)

        active = [c["category"] for c in categories if c["weight"] > 0.3]
        fading = [c["category"] for c in categories if c["trend"] == "fading"]

        recent_query = None
        try:
            import redis.asyncio as aioredis
            from app.config import get_settings
            _r = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
            recent_query = await _r.lindex(f"user_queries:{inn}", 0)
            await _r.aclose()
        except Exception:
            pass

        from app.models import UserProfile
        profile = await db.get(UserProfile, inn)

        return {
            "inn": inn,
            "label": profile.name if profile else None,
            "top_categories": categories[:8],
            "session_clicks_total": ctx.interaction_count if ctx else 0,
            "recent_query": recent_query,
            "active_interests": active[:3],
            "fading_interests": fading[:2],
            "last_updated": now.isoformat(),
        }

    async def rebuild_from_db(self, inn: str, db) -> None:
        """Rebuild in-memory profile for a user from their DB contracts."""
        from sqlalchemy import text
        result = await db.execute(text("""
            SELECT s.category, s.id AS ste_id
            FROM contracts c
            JOIN ste s ON c.ste_id = s.id
            WHERE c.customer_inn = :inn AND s.category IS NOT NULL
        """), {"inn": inn})
        rows = result.fetchall()
        categories = [r.category for r in rows]
        ste_ids = [r.ste_id for r in rows]
        try:
            from app.services.search_service import get_search_service
            ss = get_search_service()
            emb_map = {sid: ss._documents[sid].embedding for sid in ste_ids if sid in ss._documents} if ss._initialized else {}
        except Exception:
            emb_map = {}
        self.build_profile_from_contracts(inn, categories, emb_map, ste_ids)


# --- Industry → category mapping for GET /users/{inn}/categories ---

INDUSTRY_ALLOWED_CATEGORIES: dict[str, list[str]] = {
    "Образование": [
        "Канцелярские товары", "Мебель", "Мебель офисная", "IT-оборудование",
        "Компьютеры", "Спортивный инвентарь", "Хозяйственные товары", "Книги",
    ],
    "Медицина": [
        "Медицинские товары", "Расходные материалы", "Мебель медицинская",
        "Хозяйственные товары", "IT-оборудование", "Спецодежда",
    ],
    "Стройматериалы": [
        "Стройматериалы", "Электротехника", "Инструменты", "Крепёж",
        "Хозяйственные товары", "Мебель", "Спецодежда",
    ],
    "Электротехника": [
        "Электротехника", "IT-оборудование", "Инструменты", "Кабели",
    ],
    "IT-оборудование": [
        "IT-оборудование", "Компьютеры", "Сетевое оборудование",
        "Канцелярские товары", "Мебель офисная",
    ],
    "ЖКХ": [
        "ЖКХ", "Стройматериалы", "Электротехника", "Хозяйственные товары", "Инструменты",
    ],
    "Транспорт": [
        "Транспортные средства", "Запчасти", "Электротехника", "ЖКХ",
    ],
    "Хозяйственные товары": [
        "Хозяйственные товары", "Стройматериалы", "ЖКХ",
    ],
    "Канцелярские товары": [
        "Канцелярские товары", "Мебель офисная", "IT-оборудование",
    ],
}


def get_allowed_categories_for_user(
    industry: str | None,
    contract_categories: list[str],
) -> list[str]:
    """Merge industry-allowed categories with user's own contract categories."""
    allowed = set(contract_categories)
    if industry and industry in INDUSTRY_ALLOWED_CATEGORIES:
        allowed |= set(INDUSTRY_ALLOWED_CATEGORIES[industry])
    return sorted(allowed) if allowed else []


_personalization_service: PersonalizationService | None = None


def get_personalization_service() -> PersonalizationService:
    global _personalization_service
    if _personalization_service is None:
        _personalization_service = PersonalizationService()
    return _personalization_service
