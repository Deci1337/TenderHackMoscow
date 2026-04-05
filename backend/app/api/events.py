from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Event
from app.schemas import EventCreate, EventResponse
from app.services.session_index import record_event, record_category_click

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventResponse)
async def log_event(event: EventCreate, db: AsyncSession = Depends(get_db)):
    """
    Log a user interaction event.
    Writes to PostgreSQL (persistent history) and Redis (live session index).
    Also updates Dev2's in-memory personalization profile for instant ML re-ranking.
    """
    db_event = Event(
        user_inn=event.user_inn,
        ste_id=event.ste_id,
        event_type=event.event_type,
        session_id=event.session_id,
        query=event.query,
        meta=event.meta,
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)

    # Update in-memory personalization profile with category and embedding
    try:
        from app.services.personalization_service import get_personalization_service
        from app.services.search_service import get_search_service
        ss = get_search_service()
        doc = ss._documents.get(event.ste_id) if ss._initialized else None
        get_personalization_service().record_interaction(
            customer_inn=event.user_inn,
            ste_id=event.ste_id,
            action=event.event_type,
            ste_embedding=doc.embedding if doc else None,
            ste_category=doc.category if doc else None,
        )
    except Exception:
        pass

    # Update Redis session index for real-time dynamic indexing
    if event.session_id:
        await record_event(event.user_inn, event.session_id, event.ste_id, event.event_type)

        # Track category momentum for session drift personalization
        category = (event.meta or {}).get("category")
        if category and event.event_type in {"click", "view", "like"}:
            await record_category_click(event.user_inn, event.session_id, category)

    # Persist last interaction timestamp per category for interest decay
    category = (event.meta or {}).get("category")
    if category and event.event_type in {"click", "view", "like", "compare"}:
        try:
            import redis.asyncio as aioredis
            from app.config import get_settings
            from datetime import datetime
            _r = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
            await _r.set(
                f"last_cat:{event.user_inn}:{category}",
                datetime.utcnow().isoformat(),
                ex=86400 * 60,
            )
            await _r.aclose()
        except Exception:
            pass

    # Persist like/dislike as long-lived Redis signals for ranking (TTL 7 days)
    if event.event_type in {"like", "dislike"}:
        try:
            from app.services.session_index import record_like_dislike
            await record_like_dislike(event.user_inn, event.ste_id, event.event_type)
        except Exception:
            pass

    # Flush strong signals (like / hide) to persistent cross-session profile immediately
    if event.event_type in {"like", "dislike", "hide", "bounce"} and event.session_id:
        try:
            from app.services.session_index import flush_to_profile
            await flush_to_profile(event.user_inn, event.session_id, db)
        except Exception:
            pass

    return EventResponse(id=db_event.id, created_at=db_event.created_at)


@router.get("/history/{user_inn}")
async def get_interaction_history(user_inn: str, limit: int = 50):
    """Recent interaction history for a user (debug/demo)."""
    try:
        from app.services.personalization_service import get_personalization_service
        ctx = get_personalization_service()._profiles.get(user_inn)
        if not ctx:
            return {"interactions": [], "total": 0}
        return {
            "session_clicks": ctx.session_clicks[-limit:],
            "negative_signals": list(ctx.negative_ste_ids)[:limit],
            "positive_signals": list(ctx.positive_ste_ids)[:limit],
            "interaction_count": ctx.interaction_count,
        }
    except Exception:
        return {"interactions": [], "total": 0}
