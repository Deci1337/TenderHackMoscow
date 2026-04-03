from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Contract, UserProfile
from app.schemas import OnboardingRequest, UserProfileResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/onboarding", response_model=UserProfileResponse)
async def onboard_user(req: OnboardingRequest, db: AsyncSession = Depends(get_db)):
    """Create or update user profile (cold start / onboarding)."""
    profile = await db.get(UserProfile, req.inn)
    if profile:
        if req.industry:
            profile.industry = req.industry
        if req.name:
            profile.name = req.name
        if req.region:
            profile.region = req.region
    else:
        profile = UserProfile(
            inn=req.inn, name=req.name, region=req.region, industry=req.industry,
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


async def _get_user_stats(db: AsyncSession, inn: str) -> dict:
    """Aggregate contract history into profile stats."""
    result = await db.execute(
        select(func.count()).where(Contract.customer_inn == inn)
    )
    total = result.scalar() or 0

    cat_result = await db.execute(
        select(Contract.purchase_name, func.count().label("cnt"))
        .where(Contract.customer_inn == inn)
        .group_by(Contract.purchase_name)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_cats = [r[0] for r in cat_result.all() if r[0]]

    return {"total_contracts": total, "top_categories": top_cats}
