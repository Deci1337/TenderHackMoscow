"""
Interest Decay Service.

Applies exponential decay to category weights so that categories
the user has not interacted with recently lose priority over time.

Half-life: 14 days (a category not viewed for 14 days loses 50% of its weight).
After 30 days the weight is nearly zero.
"""
from datetime import datetime, timezone

DECAY_HALF_LIFE_DAYS = 14


def apply_decay_to_category_weights(
    category_weights: dict[str, float],
    last_seen: dict[str, datetime],
    now: datetime | None = None,
) -> dict[str, float]:
    """
    Apply exponential decay to category weights.

    Parameters
    ----------
    category_weights : mapping of category -> weight (0..1)
    last_seen        : mapping of category -> last interaction datetime
    now              : reference time (defaults to UTC now)

    Returns
    -------
    New dict with decayed weights.  Categories with no last_seen entry
    are returned unchanged (conservative: no data = no penalty).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    decayed: dict[str, float] = {}
    for cat, weight in category_weights.items():
        last = last_seen.get(cat)
        if last is None:
            decayed[cat] = weight
            continue
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days = (now - last).total_seconds() / 86400
        decay_factor = 0.5 ** (days / DECAY_HALF_LIFE_DAYS)
        decayed[cat] = weight * decay_factor

    return decayed
