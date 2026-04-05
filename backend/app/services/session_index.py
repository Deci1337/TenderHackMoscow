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
    """Push a user interaction event into the session index in Redis.

    Each (ste_id, signal_type) pair is capped at 3 to prevent score inflation
    from repeated clicks.
    """
    key = _session_key(user_inn, session_id)
    try:
        r = await get_redis()
        field = "boosted" if event_type in {"click", "compare", "like", "view"} else "penalized"
        field_key = f"{field}:{ste_id}"
        current = int(await r.hget(key, field_key) or 0)
        if current < 3:
            async with r.pipeline(transaction=True) as pipe:
                await pipe.hincrby(key, field_key, 1)
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


async def flush_to_profile(
    user_inn: str,
    session_id: str,
    db,  # AsyncSession
) -> None:
    """
    Persist strong session signals (2+ interactions) into user_profiles.profile_data.
    This enables cross-session memory that survives Redis TTL.
    """
    from sqlalchemy import select, update
    from app.models import UserProfile

    key = _session_key(user_inn, session_id)
    try:
        r = await get_redis()
        data = await r.hgetall(key)
        await r.aclose()
    except Exception:
        return

    liked: list[int] = []
    hidden: list[int] = []
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
        if count >= 2:  # only strong signals (seen 2+ times)
            if signal_type == "boosted":
                liked.append(ste_id)
            elif signal_type == "penalized":
                hidden.append(ste_id)

    if not liked and not hidden:
        return

    try:
        profile = (await db.execute(
            select(UserProfile).where(UserProfile.inn == user_inn)
        )).scalar_one_or_none()

        if not profile:
            return

        pd = dict(profile.profile_data or {})
        existing_liked: list[int] = pd.get("liked_ids", [])
        existing_hidden: list[int] = pd.get("hidden_ids", [])

        merged_liked = list(set(existing_liked + liked))[-200:]
        merged_hidden = list(set(existing_hidden + hidden))[-200:]

        pd["liked_ids"] = merged_liked
        pd["hidden_ids"] = merged_hidden
        profile.profile_data = pd
        await db.commit()
        log.debug("Flushed %d liked / %d hidden for %s", len(liked), len(hidden), user_inn)
    except Exception as e:
        log.warning("Cross-session flush failed: %s", e)


async def get_cross_session_adjustments(
    user_inn: str,
    candidate_ids: list[int],
    db,  # AsyncSession
) -> dict[int, float]:
    """
    Load persisted liked/hidden signals from user_profiles and apply as score adjustments.
    """
    from sqlalchemy import select
    from app.models import UserProfile

    if not candidate_ids:
        return {}

    try:
        profile = (await db.execute(
            select(UserProfile).where(UserProfile.inn == user_inn)
        )).scalar_one_or_none()

        if not profile or not profile.profile_data:
            return {}

        pd = profile.profile_data
        liked_set = set(pd.get("liked_ids", []))
        hidden_set = set(pd.get("hidden_ids", []))

        result: dict[int, float] = {}
        for sid in candidate_ids:
            if sid in hidden_set:
                result[sid] = result.get(sid, 0.0) - 0.5   # persistent hide penalty
            elif sid in liked_set:
                result[sid] = result.get(sid, 0.0) + 0.2   # persistent like boost
        return result
    except Exception as e:
        log.warning("Cross-session load failed: %s", e)
        return {}


async def record_category_click(
    user_inn: str,
    session_id: str,
    category: str,
) -> None:
    """Track categories clicked within a session for momentum drift."""
    key = f"momentum:{user_inn}:{session_id}"
    try:
        r = await get_redis()
        async with r.pipeline(transaction=True) as pipe:
            await pipe.hincrby(key, category, 1)
            await pipe.expire(key, TTL_SECONDS)
            await pipe.execute()
        await r.aclose()
    except Exception as e:
        log.warning("Redis momentum record failed: %s", e)


async def get_momentum_boosts(
    user_inn: str,
    session_id: str,
    candidates: list[dict],
) -> dict[int, float]:
    """
    If user clicked 2+ items in category X this session, boost other candidates
    from that category. Simulates a "session intent drift" signal.
    """
    key = f"momentum:{user_inn}:{session_id}"
    try:
        r = await get_redis()
        raw = await r.hgetall(key)
        await r.aclose()
    except Exception:
        return {}

    if not raw:
        return {}

    # Normalize category click counts to a 0..0.3 boost
    max_clicks = max(int(v) for v in raw.values()) or 1
    boosts: dict[int, float] = {}
    for c in candidates:
        cat = c.get("category")
        if cat and cat in raw:
            strength = int(raw[cat]) / max_clicks
            boosts[c["id"]] = round(strength * 0.3, 3)

    return boosts


async def record_like_dislike(user_inn: str, ste_id: int, action: str) -> None:
    """Persist like or dislike as a fixed-score Redis signal with 7-day TTL.

    Uses ZADD (set) not ZINCRBY (increment) so repeated clicks don't accumulate.
    """
    ttl = 86400 * 7
    try:
        r = await get_redis()
        if action == "like":
            like_key = f"user:{user_inn}:likes"
            dislike_key = f"user:{user_inn}:dislikes"
            await r.zadd(like_key, {str(ste_id): 1.5})
            await r.zrem(dislike_key, str(ste_id))
            await r.expire(like_key, ttl)
        elif action == "dislike":
            dislike_key = f"user:{user_inn}:dislikes"
            like_key = f"user:{user_inn}:likes"
            await r.zadd(dislike_key, {str(ste_id): 1.0})
            await r.zrem(like_key, str(ste_id))
            await r.expire(dislike_key, ttl)
        await r.aclose()
    except Exception as e:
        log.warning("Redis like/dislike record failed (non-critical): %s", e)


async def get_like_dislike_boosts(user_inn: str, ste_ids: list[int]) -> dict[int, float]:
    """
    Returns {ste_id: score_delta} based on persistent like/dislike signals.
    Likes give +1.5, dislikes give -1.5 per accumulated signal point.
    """
    if not ste_ids or not user_inn:
        return {}
    try:
        r = await get_redis()
        like_key = f"user:{user_inn}:likes"
        dislike_key = f"user:{user_inn}:dislikes"
        boosts: dict[int, float] = {}
        for sid in ste_ids:
            like_score = await r.zscore(like_key, str(sid)) or 0.0
            dislike_score = await r.zscore(dislike_key, str(sid)) or 0.0
            delta = like_score * 1.5 - dislike_score * 1.5
            if delta != 0:
                boosts[sid] = delta
        await r.aclose()
        return boosts
    except Exception as e:
        log.warning("Redis like/dislike read failed (non-critical): %s", e)
        return {}


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
