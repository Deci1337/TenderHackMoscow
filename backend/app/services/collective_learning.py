"""
Collective learning: aggregate user click behavior per query to improve search.

When N users search for "бумага для подарков" and click on "Бумага упаковочная",
the system learns that this query should boost wrapping paper in future searches.

Data flow:
  1. Events table stores (query, ste_id, event_type) per user interaction
  2. This service periodically aggregates: query -> {product_name: click_count}
  3. Products clicked by 2+ distinct users for a query get promoted as "learned rewrites"
  4. The NLP pipeline uses these rewrites to expand queries at search time
  5. The ranking pipeline adds a "collective" boost factor to these products
"""
import logging
import threading
import time
from collections import defaultdict

log = logging.getLogger(__name__)

_MIN_USERS = 2
_CACHE_TTL = 300  # 5 minutes
_cache: dict = {}
_cache_ts: float = 0.0
_lock = threading.Lock()


def _normalize_query(q: str) -> str:
    return q.strip().lower()


def get_learned_rewrites(query: str) -> list[str]:
    """Return product name tokens that users collectively chose for this query."""
    q = _normalize_query(query)
    if not _cache or (time.time() - _cache_ts > _CACHE_TTL):
        return []
    entry = _cache.get(q)
    if not entry:
        return []
    return [name for name, _count in sorted(entry.items(), key=lambda x: -x[1])[:3]]


async def get_collective_insights(query: str) -> list[dict]:
    """Return detailed collective insights for display in ThinkingModal."""
    q = _normalize_query(query)
    if not _cache:
        return []
    entry = _cache.get(q)
    if not entry:
        return []
    return [
        {"product_name": name, "user_count": count}
        for name, count in sorted(entry.items(), key=lambda x: -x[1])[:5]
    ]


async def get_collective_boost(query: str, candidate_ids: list[int], db) -> dict[int, float]:
    """Return {ste_id: score_boost} for candidates that match collectively learned names."""
    from sqlalchemy import text as sa_text
    q = _normalize_query(query)
    if not _cache:
        return {}
    entry = _cache.get(q)
    if not entry:
        return {}

    learned_names = list(entry.keys())[:5]
    if not learned_names or not candidate_ids:
        return {}

    try:
        placeholders = ", ".join(f":n{i}" for i in range(len(learned_names)))
        rows = (await db.execute(
            sa_text(f"""
                SELECT id, name FROM ste
                WHERE id = ANY(:ids) AND name IN ({placeholders})
            """),
            {"ids": candidate_ids, **{f"n{i}": n for i, n in enumerate(learned_names)}},
        )).all()

        boosts = {}
        for ste_id, name in rows:
            count = entry.get(name, 0)
            boosts[ste_id] = min(count * 0.15, 0.6)
        return boosts
    except Exception as e:
        log.debug("Collective boost query failed: %s", e)
        return {}


async def rebuild_cache(db) -> int:
    """Rebuild the collective learning cache from the events table.

    Aggregates: for each distinct query, which products did 2+ distinct users click?
    """
    global _cache, _cache_ts
    from sqlalchemy import text as sa_text

    try:
        rows = (await db.execute(sa_text("""
            SELECT e.query, s.name, COUNT(DISTINCT e.user_inn) AS user_cnt
            FROM events e
            JOIN ste s ON s.id = e.ste_id
            WHERE e.event_type IN ('click', 'like')
              AND e.query IS NOT NULL
              AND e.query != ''
              AND e.query != '*'
            GROUP BY e.query, s.name
            HAVING COUNT(DISTINCT e.user_inn) >= :min_users
            ORDER BY user_cnt DESC
        """), {"min_users": _MIN_USERS})).all()

        new_cache: dict[str, dict[str, int]] = defaultdict(dict)
        for query, product_name, user_cnt in rows:
            q = _normalize_query(query)
            new_cache[q][product_name] = int(user_cnt)

        with _lock:
            _cache = dict(new_cache)
            _cache_ts = time.time()

        log.info("Collective learning cache rebuilt: %d query patterns from %d rows",
                 len(new_cache), len(rows))
        return len(new_cache)
    except Exception as e:
        log.warning("Collective learning rebuild failed: %s", e)
        return 0


def get_cache_stats() -> dict:
    """Return stats about the collective learning cache for display."""
    return {
        "total_patterns": len(_cache),
        "cache_age_seconds": int(time.time() - _cache_ts) if _cache_ts > 0 else -1,
        "sample_patterns": [
            {"query": q, "top_product": max(v.items(), key=lambda x: x[1])[0], "users": max(v.values())}
            for q, v in list(_cache.items())[:5]
        ] if _cache else [],
    }
