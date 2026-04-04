"""
Rule-based personalization service.

Works exclusively from PostgreSQL — no ML required.
Produces ranked STE IDs and explanations based on:
  1. User's contract history (which STE IDs they've purchased)
  2. Category affinity (which categories they buy most)
  3. Session events (clicks, compares — positive; bounces, hides — negative)
"""
from dataclasses import dataclass, field

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contract, Event, UserProfile

# Map declared interest -> STE categories that are RELEVANT (get boost)
INDUSTRY_CATEGORIES: dict[str, list[str]] = {
    "Строительство":        ["Стройматериалы", "Электротехника", "Инструменты", "ЖКХ", "Сантехника", "Металлопрокат"],
    "Образование":          ["Образование", "Канцелярские товары", "Мебель школьная", "Спортивный инвентарь"],
    "Здравоохранение":      ["Медицинские товары", "Медицинское оборудование", "Фармацевтика", "Хозяйственные товары"],
    "IT и связь":           ["IT-оборудование", "Оргтехника", "Электротехника", "Программное обеспечение"],
    "ЖКХ":                  ["ЖКХ", "Электротехника", "Стройматериалы", "Сантехника", "Инструменты"],
    "Промышленность":       ["Стройматериалы", "IT-оборудование", "Инструменты", "Электротехника", "Металлопрокат"],
    "Культура и спорт":     ["Спортивный инвентарь", "Образование", "Канцелярские товары", "Мебель"],
    "Транспорт":            ["IT-оборудование", "Электротехника", "Запчасти"],
    "Канцелярские товары":  ["Канцелярские товары", "Офисная мебель"],
    "Медицинские товары":   ["Медицинские товары", "Медицинское оборудование", "Фармацевтика"],
    "IT-оборудование":      ["IT-оборудование", "Оргтехника", "Электротехника"],
    "Стройматериалы":       ["Стройматериалы", "Инструменты", "Электротехника", "Сантехника"],
    "Электротехника":       ["Электротехника", "IT-оборудование", "Инструменты"],
    "Хозяйственные товары": ["Хозяйственные товары", "Канцелярские товары"],
    "Другое":               [],
}

# Categories every organisation needs — never penalise these
UNIVERSAL_CATEGORIES: frozenset[str] = frozenset({
    "IT-оборудование", "Оргтехника", "Канцелярские товары",
    "Хозяйственные товары", "Офисная мебель", "Мебель",
})

# Categories that are domain-specific: maps category -> which interests consider it relevant
# Items in these categories will be penalised if the user's interests don't cover them
DOMAIN_SPECIFIC_CATEGORIES: dict[str, list[str]] = {
    "Медицинские товары":       ["Здравоохранение", "Медицинские товары"],
    "Медицинское оборудование": ["Здравоохранение", "Медицинские товары"],
    "Фармацевтика":             ["Здравоохранение", "Медицинские товары"],
    "Стройматериалы":           ["Строительство", "ЖКХ", "Промышленность", "Стройматериалы"],
    "Сантехника":               ["Строительство", "ЖКХ"],
    "Металлопрокат":            ["Строительство", "Промышленность"],
    "Инструменты":              ["Строительство", "ЖКХ", "Промышленность"],
    "Образование":              ["Образование", "Культура и спорт"],
    "Мебель школьная":          ["Образование"],
    "Спортивный инвентарь":     ["Культура и спорт", "Образование"],
    "Запчасти":                 ["Транспорт", "Промышленность"],
    "Программное обеспечение":  ["IT и связь", "IT-оборудование"],
}


@dataclass
class ScoredSTE:
    ste_id: int
    boost: float = 0.0
    penalty: float = 0.0
    explanations: list[dict] = field(default_factory=list)

    @property
    def net_score(self) -> float:
        return self.boost - self.penalty


async def get_user_boosts(
    db: AsyncSession,
    user_inn: str,
    session_id: str | None,
    candidate_ids: list[int],
) -> dict[int, ScoredSTE]:
    """
    Return per-STE boost/penalty scores and explanation tags for the given user.
    Called with a list of candidate STE IDs from the text/semantic search stage.
    """
    scores: dict[int, ScoredSTE] = {sid: ScoredSTE(ste_id=sid) for sid in candidate_ids}

    # Check if user has any contract history at all
    contract_count: int = (await db.execute(
        select(func.count()).where(Contract.customer_inn == user_inn)
    )).scalar() or 0

    if contract_count > 0:
        # Returning user: use actual purchase history for personalization
        await _apply_contract_history(db, user_inn, candidate_ids, scores)
        await _apply_category_affinity(db, user_inn, candidate_ids, scores)
    else:
        # Cold-start user: use declared industry instead of non-existent history
        await _apply_industry_affinity(db, user_inn, candidate_ids, scores)

    # Always apply mismatch penalty when user has declared interests
    await _apply_profile_mismatch_penalty(db, user_inn, candidate_ids, scores)

    if session_id:
        await _apply_session_events(db, user_inn, session_id, candidate_ids, scores)

    return scores


async def _apply_contract_history(
    db: AsyncSession,
    user_inn: str,
    candidate_ids: list[int],
    scores: dict[int, ScoredSTE],
) -> None:
    """Boost STE IDs the user has already purchased."""
    if not candidate_ids:
        return

    rows = await db.execute(
        select(Contract.ste_id, func.count().label("times"))
        .where(
            Contract.customer_inn == user_inn,
            Contract.ste_id.in_(candidate_ids),
        )
        .group_by(Contract.ste_id)
    )
    for ste_id, times in rows.all():
        if ste_id in scores:
            boost = min(0.5 + times * 0.1, 1.0)
            scores[ste_id].boost += boost
            scores[ste_id].explanations.append({
                "reason": f"Вы уже закупали этот товар ({times} раз)" if times > 1 else "Вы уже закупали этот товар",
                "factor": "history",
                "weight": boost,
            })


async def _apply_category_affinity(
    db: AsyncSession,
    user_inn: str,
    candidate_ids: list[int],
    scores: dict[int, ScoredSTE],
) -> None:
    """
    Boost STE items whose category matches user's top purchased categories.
    Uses a JOIN between ste and contracts by ste_id to get category overlap.
    """
    if not candidate_ids:
        return

    rows = await db.execute(text("""
        WITH user_cats AS (
            SELECT s.category, count(*) AS cnt
            FROM contracts c
            JOIN ste s ON s.id = c.ste_id
            WHERE c.customer_inn = :inn AND s.category IS NOT NULL
            GROUP BY s.category
            ORDER BY cnt DESC
            LIMIT 5
        ),
        candidate_cats AS (
            SELECT s.id, s.category
            FROM ste s
            WHERE s.id = ANY(:ids) AND s.category IS NOT NULL
        )
        SELECT cc.id, cc.category, uc.cnt
        FROM candidate_cats cc
        JOIN user_cats uc ON uc.category = cc.category
    """), {"inn": user_inn, "ids": candidate_ids})

    for ste_id, category, cnt in rows.all():
        if ste_id in scores:
            boost = 0.3
            scores[ste_id].boost += boost
            scores[ste_id].explanations.append({
                "reason": f"Популярно в вашей сфере: «{category}»",
                "factor": "category",
                "weight": boost,
            })


async def _apply_session_events(
    db: AsyncSession,
    user_inn: str,
    session_id: str,
    candidate_ids: list[int],
    scores: dict[int, ScoredSTE],
) -> None:
    """
    Apply real-time session signals:
      - click / compare / like → positive boost
      - bounce / hide          → negative penalty
    """
    if not candidate_ids:
        return

    rows = await db.execute(
        select(Event.ste_id, Event.event_type)
        .where(
            Event.user_inn == user_inn,
            Event.session_id == session_id,
            Event.ste_id.in_(candidate_ids),
        )
    )

    POSITIVE = {"click": 0.2, "compare": 0.25, "like": 0.3}
    NEGATIVE = {"bounce": -0.4, "hide": -0.8}

    for ste_id, event_type in rows.all():
        if ste_id not in scores:
            continue
        if event_type in POSITIVE:
            w = POSITIVE[event_type]
            scores[ste_id].boost += w
            scores[ste_id].explanations.append({
                "reason": "Вы взаимодействовали с этим товаром",
                "factor": "session",
                "weight": w,
            })
        elif event_type in NEGATIVE:
            w = abs(NEGATIVE[event_type])
            scores[ste_id].penalty += w
            scores[ste_id].explanations.append({
                "reason": "Снижено: вы отклонили похожий товар",
                "factor": "negative",
                "weight": -w,
            })


async def _apply_industry_affinity(
    db: AsyncSession,
    user_inn: str,
    candidate_ids: list[int],
    scores: dict[int, ScoredSTE],
) -> None:
    """
    Cold-start personalization: boost items matching user's declared interests.
    Only called when user has zero contract history.
    Never shows "Вы уже закупали" — only "Соответствует вашим интересам".
    """
    if not candidate_ids:
        return

    profile = await db.get(UserProfile, user_inn)
    if not profile:
        return

    # Collect all declared interests (from profile_data.interests or fallback to industry)
    interests: list[str] = []
    if profile.profile_data and "interests" in profile.profile_data:
        interests = profile.profile_data["interests"]
    elif profile.industry:
        interests = [profile.industry]

    if not interests:
        return

    # Expand interests to relevant STE categories
    relevant_cats: list[str] = []
    for interest in interests:
        relevant_cats.extend(INDUSTRY_CATEGORIES.get(interest, [interest]))
    relevant_cats = list(set(relevant_cats))
    if not relevant_cats:
        return

    rows = await db.execute(text("""
        SELECT id, category FROM ste
        WHERE id = ANY(:ids) AND category = ANY(:cats)
    """), {"ids": candidate_ids, "cats": relevant_cats})

    label = interests[0] if len(interests) == 1 else f"{interests[0]} и др."
    for ste_id, _cat in rows.all():
        if ste_id in scores:
            scores[ste_id].boost += 0.25
            scores[ste_id].explanations.append({
                "reason": f"Соответствует вашим интересам: «{label}»",
                "factor": "category",
                "weight": 0.25,
            })


async def _apply_profile_mismatch_penalty(
    db: AsyncSession,
    user_inn: str,
    candidate_ids: list[int],
    scores: dict[int, ScoredSTE],
) -> None:
    """
    Penalise domain-specific items that do not match the user's declared interests.

    Example: user profile = ['Строительство']
      - toy "Стройка" in category "Игрушки"       → penalised (domain mismatch)
      - "Компьютер" in "IT-оборудование"           → NOT penalised (universal)
      - "Цемент" in "Стройматериалы"               → NOT penalised (relevant)
      - "Бинт" in "Медицинские товары"             → penalised (healthcare, not construction)
    """
    if not candidate_ids:
        return

    profile = await db.get(UserProfile, user_inn)
    if not profile:
        return

    interests: list[str] = []
    if profile.profile_data and "interests" in profile.profile_data:
        interests = profile.profile_data["interests"]
    elif profile.industry:
        interests = [profile.industry]
    if not interests:
        return

    # Build the set of categories that are "safe" for this user
    safe_cats: set[str] = set(UNIVERSAL_CATEGORIES)
    for interest in interests:
        safe_cats.update(INDUSTRY_CATEGORIES.get(interest, [interest]))

    # Collect domain-specific categories that are NOT safe for this user
    penalise_cats = [
        cat for cat, relevant_interests in DOMAIN_SPECIFIC_CATEGORIES.items()
        if cat not in safe_cats
        and not any(i in relevant_interests for i in interests)
    ]
    if not penalise_cats:
        return

    rows = await db.execute(text("""
        SELECT id, category FROM ste
        WHERE id = ANY(:ids) AND category = ANY(:cats)
    """), {"ids": candidate_ids, "cats": penalise_cats})

    for ste_id, category in rows.all():
        if ste_id in scores:
            scores[ste_id].penalty += 0.65
            scores[ste_id].explanations.append({
                "reason": f"Вероятно, не соответствует вашему профилю (категория: {category})",
                "factor": "profile_mismatch",
                "weight": -0.65,
            })
