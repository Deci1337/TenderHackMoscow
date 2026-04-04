"""
Rule-based collaborative filtering via SQL co-purchase patterns.

No ML required. Core idea:
  "Users who bought item X also frequently bought item Y"
  -> boost Y in the results when X is in the user's contract history

Algorithm:
  1. Get all STE IDs the user has bought (their "purchase set")
  2. Find other users who bought the same items ("neighbours")
  3. Get what those neighbours also bought (co-purchase set)
  4. Boost co-purchased items that appear in current candidates

This is item-to-item collaborative filtering implemented entirely in SQL.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


async def get_collaborative_boosts(
    db: AsyncSession,
    user_inn: str,
    candidate_ids: list[int],
    max_neighbours: int = 50,
    top_co_items: int = 30,
) -> dict[int, float]:
    """
    Returns {ste_id: boost_score} for candidates that appear in
    co-purchase patterns of similar users.

    boost_score is in [0, 0.4].
    """
    if not candidate_ids or not user_inn:
        return {}

    try:
        # Step 1: items the current user has bought
        user_items = (await db.execute(text("""
            SELECT DISTINCT ste_id FROM contracts
            WHERE customer_inn = :inn AND ste_id IS NOT NULL
            LIMIT 100
        """), {"inn": user_inn})).scalars().all()

        if not user_items:
            return {}

        # Step 2 + 3: find neighbours and their co-purchases in a single query
        # "Customers who bought any of the same items, and what else they bought"
        rows = (await db.execute(text("""
            WITH user_ste AS (
                SELECT DISTINCT ste_id FROM contracts
                WHERE customer_inn = :inn AND ste_id IS NOT NULL
            ),
            neighbours AS (
                SELECT DISTINCT c.customer_inn
                FROM contracts c
                JOIN user_ste u ON u.ste_id = c.ste_id
                WHERE c.customer_inn != :inn
                LIMIT :max_n
            ),
            co_purchases AS (
                SELECT c.ste_id,
                       COUNT(DISTINCT c.customer_inn) AS neighbour_count
                FROM contracts c
                JOIN neighbours n ON n.customer_inn = c.customer_inn
                WHERE c.ste_id = ANY(:cids)
                  AND c.ste_id NOT IN (SELECT ste_id FROM user_ste)
                GROUP BY c.ste_id
                ORDER BY neighbour_count DESC
                LIMIT :top_co
            )
            SELECT ste_id, neighbour_count FROM co_purchases
        """), {
            "inn": user_inn,
            "cids": candidate_ids,
            "max_n": max_neighbours,
            "top_co": top_co_items,
        })).all()

        if not rows:
            return {}

        # Normalise counts to [0, 0.4] boost range
        max_count = max(r[1] for r in rows) or 1
        return {
            r[0]: round(0.4 * (r[1] / max_count), 3)
            for r in rows
        }

    except Exception as e:
        log.debug("Collaborative filter failed (non-critical): %s", e)
        return {}
