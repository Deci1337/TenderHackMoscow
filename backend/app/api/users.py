from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Contract, UserProfile
from app.schemas import CategoryFacet, OnboardingRequest, UserInterestSummary, UserProfileResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/onboarding", response_model=UserProfileResponse)
async def onboard_user(req: OnboardingRequest, db: AsyncSession = Depends(get_db)):
    """Create or update user profile (cold start / onboarding)."""
    profile = await db.get(UserProfile, req.inn)
    interests = req.interests or ([req.industry] if req.industry else [])
    if profile:
        if req.industry:
            profile.industry = req.industry
        if req.name:
            profile.name = req.name
        if req.region:
            profile.region = req.region
        if interests:
            profile.profile_data = {**(profile.profile_data or {}), "interests": interests}
    else:
        profile = UserProfile(
            inn=req.inn, name=req.name, region=req.region,
            industry=req.industry or (interests[0] if interests else None),
            profile_data={"interests": interests},
        )
        db.add(profile)
    await db.commit()

    stats = await _get_user_stats(db, req.inn)
    return UserProfileResponse(
        inn=profile.inn, name=profile.name, region=profile.region,
        industry=profile.industry, **stats,
    )


@router.get("/{inn}", response_model=UserProfileResponse)
async def get_user(inn: str, db: AsyncSession = Depends(get_db)):
    """Get user profile with aggregated stats."""
    profile = await db.get(UserProfile, inn)
    if not profile:
        raise HTTPException(404, "User not found")
    stats = await _get_user_stats(db, inn)
    return UserProfileResponse(
        inn=profile.inn, name=profile.name, region=profile.region,
        industry=profile.industry, **stats,
    )


@router.get("/{inn}/interests", response_model=UserInterestSummary)
async def get_user_interests(inn: str, db: AsyncSession = Depends(get_db)):
    """Return interest summary for a user: categories, weights, trends, and session activity."""
    from app.services.personalization_service import get_personalization_service
    svc = get_personalization_service()
    data = await svc.get_interest_summary(inn, db)
    return data


_category_counts_cache: dict[str, int] | None = None
_category_counts_ts: float = 0


async def _get_category_counts(db: AsyncSession) -> dict[str, int]:
    """Cached STE category counts (refreshed every 5 min)."""
    import time
    global _category_counts_cache, _category_counts_ts
    now = time.time()
    if _category_counts_cache is not None and now - _category_counts_ts < 300:
        return _category_counts_cache
    rows = await db.execute(text(
        "SELECT category, COUNT(*) AS cnt FROM ste WHERE category IS NOT NULL GROUP BY category"
    ))
    _category_counts_cache = {r.category: int(r.cnt) for r in rows.fetchall()}
    _category_counts_ts = now
    return _category_counts_cache


@router.get("/{inn}/categories", response_model=list[CategoryFacet])
async def get_user_categories(inn: str, db: AsyncSession = Depends(get_db)):
    """
    Return categories relevant to this user with real STE item counts.
    Single query for user data, cached global category counts.
    """
    result = await db.execute(text("""
        SELECT DISTINCT s.category
        FROM contracts c
        JOIN ste s ON c.ste_id = s.id
        WHERE c.customer_inn = :inn AND s.category IS NOT NULL
    """), {"inn": inn})
    contract_cats = [row.category for row in result.fetchall()]

    profile = await db.get(UserProfile, inn)
    industry = profile.industry if profile else None

    from app.services.personalization_service import get_allowed_categories_for_user
    allowed = get_allowed_categories_for_user(industry, contract_cats)
    if not allowed:
        allowed = contract_cats

    cat_counts = await _get_category_counts(db)

    matched: list[CategoryFacet] = []
    used_real: set[str] = set()
    for allowed_name in allowed:
        al = allowed_name.lower()
        best_name: str | None = None
        best_count = 0
        for real_name, cnt in cat_counts.items():
            rl = real_name.lower()
            if rl == al or al in rl or rl in al:
                if real_name not in used_real and cnt > best_count:
                    best_name = real_name
                    best_count = cnt
        if best_name:
            matched.append(CategoryFacet(name=best_name, count=best_count))
            used_real.add(best_name)

    matched.sort(key=lambda f: f.count, reverse=True)
    return matched


async def _get_user_stats(db: AsyncSession, inn: str) -> dict:
    """Aggregate contract history into profile stats."""
    result = await db.execute(
        select(func.count()).where(Contract.customer_inn == inn)
    )
    total = result.scalar() or 0

    # Join with STE to get clean category names from the actual catalog
    cat_result = await db.execute(text("""
        SELECT s.category, COUNT(*) as cnt
        FROM contracts c
        JOIN ste s ON c.ste_id = s.id
        WHERE c.customer_inn = :inn AND s.category IS NOT NULL
        GROUP BY s.category
        ORDER BY cnt DESC
        LIMIT 6
    """), {"inn": inn})
    top_cats = [r[0] for r in cat_result.all() if r[0]]

    return {"total_contracts": total, "top_categories": top_cats}
