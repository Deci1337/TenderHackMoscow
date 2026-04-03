"""Event logging API for behavioral signals."""
from fastapi import APIRouter
from loguru import logger

from app.models.schemas import InteractionEvent, InteractionResponse
from app.services.personalization_service import get_personalization_service

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("", response_model=InteractionResponse)
async def log_interaction(event: InteractionEvent):
    """
    Log a user interaction event (click, view, bounce, add_to_compare, purchase).
    This immediately updates the user's personalization profile for dynamic indexing.
    """
    personalizer = get_personalization_service()

    personalizer.record_interaction(
        customer_inn=event.customer_inn,
        ste_id=event.ste_id,
        action=event.action,
        ste_category=None,  # Will be enriched from DB in production
    )

    logger.info(
        f"Event logged: inn={event.customer_inn}, ste={event.ste_id}, "
        f"action={event.action}"
    )

    return InteractionResponse(status="ok", profile_updated=True)


@router.get("/history/{customer_inn}")
async def get_interaction_history(customer_inn: str, limit: int = 50):
    """Get recent interaction history for a user (for debugging/demo)."""
    personalizer = get_personalization_service()
    ctx = personalizer._profiles.get(customer_inn)
    if not ctx:
        return {"interactions": [], "total": 0}
    return {
        "session_clicks": ctx.session_clicks[-limit:],
        "negative_signals": list(ctx.negative_ste_ids)[:limit],
        "positive_signals": list(ctx.positive_ste_ids)[:limit],
        "interaction_count": ctx.interaction_count,
    }
