"""
Price analytics from historical contract data.

For each STE item computes:
  - avg_price: average contract cost over all history
  - recent_avg: average cost over last 6 months
  - price_trend: "up" | "down" | "stable" based on comparison

This gives buyers real procurement price context — no other
search system on the portal does this.
"""
import logging
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

_RECENT_MONTHS = 6
_TREND_THRESHOLD = 0.10  # 10% change = significant trend


async def get_price_info(
    db: AsyncSession,
    ste_ids: list[int],
) -> dict[int, dict]:
    """
    Returns {ste_id: {"avg_price": float, "price_trend": str}} for given STE IDs.
    Only returns entries where at least 2 contracts exist.
    """
    if not ste_ids:
        return {}

    cutoff = (date.today() - timedelta(days=_RECENT_MONTHS * 30)).isoformat()

    try:
        rows = (await db.execute(text("""
            SELECT
                ste_id,
                AVG(cost)                                          AS avg_all,
                AVG(cost) FILTER (WHERE contract_date >= :cutoff)  AS avg_recent,
                COUNT(*)                                           AS total_cnt,
                COUNT(*) FILTER (WHERE contract_date >= :cutoff)   AS recent_cnt
            FROM contracts
            WHERE ste_id = ANY(:ids)
              AND cost IS NOT NULL AND cost > 0
            GROUP BY ste_id
            HAVING COUNT(*) >= 2
        """), {"ids": ste_ids, "cutoff": cutoff})).all()
    except Exception as e:
        log.debug("price_analytics query failed: %s", e)
        return {}

    result: dict[int, dict] = {}
    for row in rows:
        avg_all = float(row[1]) if row[1] else None
        avg_recent = float(row[2]) if row[2] else None

        trend = "stable"
        if avg_all and avg_recent:
            change = (avg_recent - avg_all) / avg_all
            if change > _TREND_THRESHOLD:
                trend = "up"
            elif change < -_TREND_THRESHOLD:
                trend = "down"

        result[row[0]] = {
            "avg_price": round(avg_all, 2) if avg_all else None,
            "price_trend": trend,
        }

    return result
