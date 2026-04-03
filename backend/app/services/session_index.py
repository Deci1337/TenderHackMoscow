"""
Dynamic indexing via Redis.

Stores per-user, per-session lightweight state:
  - boosted_ids: STE IDs the user positively interacted with this session
  - penalized_ids: STE IDs to demote (bounces, hides)
  - query_history: last N queries in this session

This layer is on top of the SQL personalization service and provides
sub-millisecond re-ranking adjustments without hitting the DB.
"""
import json
import logging

import redis.asyncio as aioredis

from app.config import settings

log = logging.getLogger(__name__)

TTL_SECONDS = 3600  # session state lives 1 hour


def _session_key(user_inn: str, session_id: str) -> str:
    return f"session:{user_inn}:{session_id}"


async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def record_event(
    user_inn: str,
    session_id: str,
    ste_id: int,
    event_type: str,
) -> None:
    """Push a user interaction event into the session index in Redis."""
    key = _session_key(user_inn, session_id)
    try:
        r = await get_redis()
        async with r.pipeline(transaction=True) as pipe:
            field = "boosted" if event_type in {"click", "compare", "like", "view"} else "penalized"
            await pipe.hincrby(key, f"{field}:{ste_id}", 1)
            await pipe.expire(key, TTL_SECONDS)
            await pipe.execute()
        await r.aclose()
    except Exception as e:
        log.warning("Redis session record failed (non-critical): %s", e)


async def get_session_adjustments(
    user_inn: str,
    session_id: str,
    candidate_ids: list[int],
) -> dict[int, float]:
    """
    Returns {ste_id: delta_score} for candidate IDs based on session state.
    Positive values = boost, negative = penalty.
    """
    if not candidate_ids:
        return {}

    key = _session_key(user_inn, session_id)
    adjustments: dict[int, float] = {}

    try:
        r = await get_redis()
        data = await r.hgetall(key)
        await r.aclose()
    except Exception as e:
        log.warning("Redis session read failed (non-critical): %s", e)
        return adjustments

    for field_name, count_str in data.items():
        parts = field_name.split(":")
        if len(parts) != 2:
            continue
        signal_type, ste_id_str = parts
        try:
            ste_id = int(ste_id_str)
            count = int(count_str)
        except ValueError:
            continue

        if ste_id not in candidate_ids:
            continue

        if signal_type == "boosted":
            adjustments[ste_id] = adjustments.get(ste_id, 0.0) + count * 0.15
        elif signal_type == "penalized":
            adjustments[ste_id] = adjustments.get(ste_id, 0.0) - count * 0.4

    return adjustments


async def get_session_change_reason(
    user_inn: str,
    session_id: str,
) -> str | None:
    """
    Returns a human-readable explanation of why the search results may have
    changed in this session compared to a fresh session.
    """
    key = _session_key(user_inn, session_id)
    try:
        r = await get_redis()
        data = await r.hgetall(key)
        await r.aclose()
    except Exception:
        return None

    boosted = sum(1 for k in data if k.startswith("boosted:"))
    penalized = sum(1 for k in data if k.startswith("penalized:"))

    if not boosted and not penalized:
        return None

    parts = []
    if boosted:
        parts.append(f"вы просмотрели {boosted} товар(ов)")
    if penalized:
        parts.append(f"отклонили {penalized} товар(ов)")

    return "Выдача изменилась, потому что в этой сессии " + " и ".join(parts) + "."
