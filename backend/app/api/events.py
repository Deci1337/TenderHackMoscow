from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Event
from app.schemas import EventCreate, EventResponse
from app.services.session_index import record_event

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

    # Update Dev2's in-memory personalization profile (non-critical)
    try:
        from app.services.personalization_service import get_personalization_service
        get_personalization_service().record_interaction(
            customer_inn=event.user_inn,
            ste_id=event.ste_id,
            action=event.event_type,
            ste_category=None,
        )
    except Exception:
        pass

    # Update Redis session index for real-time dynamic indexing
    if event.session_id:
        await record_event(event.user_inn, event.session_id, event.ste_id, event.event_type)

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
