# -*- coding: utf-8 -*-
"""
Products API: create supplier products, manage promotions, list own products.
Promotion boosts search ranking via promotion_boost column.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["products"])


class CreateProductRequest(BaseModel):
    name: str
    category: str
    tags: list[str] = []
    description: str = ""
    creator_user_id: str


class PromoteRequest(BaseModel):
    days: int
    creator_user_id: str


async def _ensure_product_columns(db: AsyncSession) -> None:
    """Add sprint-2 columns to ste table if they don't exist yet."""
    await db.execute(text("""
        ALTER TABLE ste
            ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS description TEXT,
            ADD COLUMN IF NOT EXISTS promoted_until TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS promotion_boost NUMERIC DEFAULT 0,
            ADD COLUMN IF NOT EXISTS creator_user_id TEXT,
            ADD COLUMN IF NOT EXISTS order_count BIGINT DEFAULT 0
    """))
    await db.commit()


@router.post("", response_model=dict)
async def create_product(req: CreateProductRequest, db: AsyncSession = Depends(get_db)):
    """Supplier creates a new product listing in the catalog."""
    await _ensure_product_columns(db)
    row = await db.execute(text("""
        INSERT INTO ste (name, category, attributes, tags, description, creator_user_id, order_count,
                         promotion_boost, name_tsv)
        VALUES (:name, :cat, '{}', :tags, :desc, :uid, 0, 0,
                to_tsvector('russian', :name || ' ' || :tagstr))
        RETURNING id, name, category, tags, order_count, promotion_boost,
                  promoted_until, creator_user_id
    """), {
        "name": req.name.strip(),
        "cat": req.category.strip(),
        "tags": req.tags,
        "desc": req.description.strip(),
        "uid": req.creator_user_id,
        "tagstr": " ".join(req.tags),
    })
    await db.commit()
    r = row.fetchone()
    return _row_to_dict(r)


@router.get("", response_model=list)
async def list_my_products(
    creator_user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """List all products created by a specific user."""
    await _ensure_product_columns(db)
    rows = await db.execute(text("""
        SELECT id, name, category, tags, order_count, promotion_boost,
               promoted_until, creator_user_id
        FROM ste
        WHERE creator_user_id = :uid
        ORDER BY id DESC
        LIMIT 100
    """), {"uid": creator_user_id})
    return [_row_to_dict(r) for r in rows.fetchall()]


@router.post("/{product_id}/promote", response_model=dict)
async def activate_promotion(
    product_id: int,
    req: PromoteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Activate paid promotion for a product, extending promoted_until and setting boost."""
    await _ensure_product_columns(db)
    check = await db.execute(text("""
        SELECT id, creator_user_id FROM ste WHERE id = :id
    """), {"id": product_id})
    row = check.fetchone()
    if not row:
        raise HTTPException(404, "Product not found")
    if row.creator_user_id and row.creator_user_id != req.creator_user_id:
        raise HTTPException(403, "Not your product")

    days = max(1, min(req.days, 30))
    boost = round(min(0.10 + days * 0.02, 0.50), 2)
    until = datetime.now(timezone.utc) + timedelta(days=days)

    updated = await db.execute(text("""
        UPDATE ste
        SET promoted_until = :until, promotion_boost = :boost
        WHERE id = :id
        RETURNING id, name, category, tags, order_count, promotion_boost,
                  promoted_until, creator_user_id
    """), {"id": product_id, "until": until, "boost": boost})
    await db.commit()
    r = updated.fetchone()
    return _row_to_dict(r)


def _row_to_dict(r) -> dict:
    now = datetime.now(timezone.utc)
    promoted_until = r.promoted_until
    if promoted_until and promoted_until.tzinfo is None:
        promoted_until = promoted_until.replace(tzinfo=timezone.utc)
    is_promoted = promoted_until is not None and promoted_until > now
    return {
        "id": r.id,
        "name": r.name,
        "category": r.category,
        "tags": r.tags or [],
        "order_count": r.order_count or 0,
        "promotion_boost": float(r.promotion_boost or 0),
        "is_promoted": is_promoted,
        "promoted_until": promoted_until.isoformat() if promoted_until else None,
    }
