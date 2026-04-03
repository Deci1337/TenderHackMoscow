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
    The Redis write enables dynamic indexing within the same session.
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

    # Non-blocking Redis write for real-time dynamic indexing
    if event.session_id:
        await record_event(event.user_inn, event.session_id, event.ste_id, event.event_type)

    return EventResponse(id=db_event.id, created_at=db_event.created_at)
