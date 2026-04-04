"""
Supplier Analytics & Buyer Intelligence endpoints.

Provides two groups of routes:

Supplier-facing
---------------
GET /analytics/products/{product_id}
    Views, clicks, likes, dislikes, compares from events table +
    price benchmark + promotion status.

GET /analytics/top-queries?user_id=
    Top search queries whose results included products by this supplier.
    Helps suppliers understand what buyers are looking for.

GET /analytics/hot-items
    Trending STE items with high recent-contract activity (last 30 days).
    Useful for buyer homepage or "what's popular" discovery widget.

GET /analytics/price-benchmark/{ste_id}
    Detailed price stats: min/avg/max, recent avg, trend, contract count.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    HotItemResponse,
    PriceBenchmarkResponse,
    ProductAnalyticsResponse,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

_RECENT_DAYS = 90
_HOT_DAYS = 30


@router.get("/products/{product_id}", response_model=ProductAnalyticsResponse)
async def get_product_analytics(product_id: int, db: AsyncSession = Depends(get_db)):
    """Aggregate interaction stats for a supplier's product."""
    product_row = (
        await db.execute(
            text("""
                SELECT s.id, s.name, s.tags, s.promoted_until,
                       s.promotion_boost, s.order_count,
                       COALESCE(sp.contract_cnt, s.order_count, 0) AS total_orders
                FROM ste s
                LEFT JOIN ste_popularity sp ON sp.ste_id = s.id
                WHERE s.id = :pid
            """),
            {"pid": product_id},
        )
    ).fetchone()

    if not product_row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found")

    event_rows = (
        await db.execute(
            text("""
                SELECT event_type, COUNT(*) AS cnt
                FROM events
                WHERE ste_id = :pid
                GROUP BY event_type
            """),
            {"pid": product_id},
        )
    ).all()

    counters: dict[str, int] = {r[0]: int(r[1]) for r in event_rows}

    query_rows = (
        await db.execute(
            text("""
                SELECT query, COUNT(*) AS cnt
                FROM events
                WHERE ste_id = :pid AND query IS NOT NULL AND query != ''
                GROUP BY query
                ORDER BY cnt DESC
                LIMIT 10
            """),
            {"pid": product_id},
        )
    ).all()

    top_queries = [r[0] for r in query_rows]

    from app.services.price_analytics import get_price_info
    price_data = await get_price_info(db, [product_id])
    pi = price_data.get(product_id, {})

    now = datetime.now(timezone.utc)
    is_promoted = (
        product_row.promoted_until is not None and product_row.promoted_until > now
    )

    return ProductAnalyticsResponse(
        product_id=product_id,
        name=product_row.name,
        total_views=counters.get("view", 0),
        total_clicks=counters.get("click", 0),
        total_likes=counters.get("like", 0),
        total_dislikes=counters.get("dislike", 0),
        total_compares=counters.get("compare", 0),
        top_search_queries=top_queries,
        avg_price=pi.get("avg_price"),
        price_trend=pi.get("price_trend"),
        is_promoted=is_promoted,
        promotion_boost=float(product_row.promotion_boost or 0),
        order_count=int(product_row.total_orders),
    )


@router.get("/top-queries")
async def get_top_queries_for_supplier(user_id: str, db: AsyncSession = Depends(get_db)):
    """Return search queries that surfaced at least one of this supplier's products."""
    rows = (
        await db.execute(
            text("""
                SELECT e.query, COUNT(*) AS cnt
                FROM events e
                JOIN ste s ON s.id = e.ste_id
                WHERE s.creator_user_id = :uid
                  AND e.query IS NOT NULL
                  AND e.query != ''
                GROUP BY e.query
                ORDER BY cnt DESC
                LIMIT 20
            """),
            {"uid": user_id},
        )
    ).all()

    return {
        "user_id": user_id,
        "top_queries": [{"query": r[0], "impressions": int(r[1])} for r in rows],
    }


@router.get("/hot-items", response_model=list[HotItemResponse])
async def get_hot_items(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """
    Items with highest recent contract activity (last 30 days).
    Also flags items that had a price drop vs. 6-month average.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=_HOT_DAYS)).date().isoformat()
    price_cutoff = (datetime.now(timezone.utc) - timedelta(days=180)).date().isoformat()

    rows = (
        await db.execute(
            text("""
                WITH recent AS (
                    SELECT ste_id, COUNT(*) AS recent_cnt
                    FROM contracts
                    WHERE contract_date >= :cutoff
                    GROUP BY ste_id
                ),
                price_stats AS (
                    SELECT
                        ste_id,
                        AVG(cost) FILTER (WHERE contract_date >= :price_cutoff) AS recent_avg,
                        AVG(cost) AS all_avg
                    FROM contracts
                    WHERE cost > 0
                    GROUP BY ste_id
                )
                SELECT s.id, s.name, s.category,
                       COALESCE(r.recent_cnt, 0) AS recent_cnt,
                       ev.view_cnt,
                       ps.recent_avg,
                       ps.all_avg
                FROM ste s
                JOIN recent r ON r.ste_id = s.id
                LEFT JOIN (
                    SELECT ste_id, COUNT(*) AS view_cnt
                    FROM events
                    WHERE event_type = 'view'
                    GROUP BY ste_id
                ) ev ON ev.ste_id = s.id
                LEFT JOIN price_stats ps ON ps.ste_id = s.id
                ORDER BY recent_cnt DESC
                LIMIT :lim
            """),
            {"cutoff": cutoff, "price_cutoff": price_cutoff, "lim": limit},
        )
    ).mappings().all()

    results = []
    for r in rows:
        recent_avg = float(r["recent_avg"]) if r["recent_avg"] else None
        all_avg = float(r["all_avg"]) if r["all_avg"] else None
        price_drop = (
            recent_avg is not None
            and all_avg is not None
            and recent_avg < all_avg * 0.90
        )
        hot_score = round(float(r["recent_cnt"]) * 1.0 + float(r["view_cnt"] or 0) * 0.1, 2)
        results.append(
            HotItemResponse(
                id=r["id"],
                name=r["name"],
                category=r["category"],
                hot_score=hot_score,
                recent_views=int(r["view_cnt"] or 0),
                recent_contracts=int(r["recent_cnt"]),
                price_drop=price_drop,
            )
        )
    return results


@router.get("/price-benchmark/{ste_id}", response_model=PriceBenchmarkResponse)
async def get_price_benchmark(ste_id: int, db: AsyncSession = Depends(get_db)):
    """Detailed price history and trend for a single product."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=180)).date().isoformat()

    name_row = (
        await db.execute(text("SELECT name FROM ste WHERE id = :id"), {"id": ste_id})
    ).fetchone()
    if not name_row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found")

    stats = (
        await db.execute(
            text("""
                SELECT
                    AVG(cost)                                           AS avg_all,
                    MIN(cost)                                           AS min_all,
                    MAX(cost)                                           AS max_all,
                    AVG(cost) FILTER (WHERE contract_date >= :cutoff)   AS recent_avg,
                    COUNT(*)                                            AS total_cnt,
                    COUNT(*) FILTER (WHERE contract_date >= :cutoff)    AS recent_cnt
                FROM contracts
                WHERE ste_id = :sid AND cost IS NOT NULL AND cost > 0
            """),
            {"sid": ste_id, "cutoff": cutoff},
        )
    ).fetchone()

    avg_all = float(stats[0]) if stats and stats[0] else None
    min_all = float(stats[1]) if stats and stats[1] else None
    max_all = float(stats[2]) if stats and stats[2] else None
    recent_avg = float(stats[3]) if stats and stats[3] else None
    total_cnt = int(stats[4]) if stats and stats[4] else 0
    recent_cnt = int(stats[5]) if stats and stats[5] else 0

    trend = "stable"
    if avg_all and recent_avg:
        change = (recent_avg - avg_all) / avg_all
        if change > 0.10:
            trend = "up"
        elif change < -0.10:
            trend = "down"

    return PriceBenchmarkResponse(
        ste_id=ste_id,
        name=name_row[0],
        avg_price=round(avg_all, 2) if avg_all else None,
        min_price=round(min_all, 2) if min_all else None,
        max_price=round(max_all, 2) if max_all else None,
        recent_avg=round(recent_avg, 2) if recent_avg else None,
        price_trend=trend,
        contract_count=total_cnt,
        recent_count=recent_cnt,
    )
