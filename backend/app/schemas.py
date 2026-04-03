from datetime import datetime

from pydantic import BaseModel, Field


# --- Search ---

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    user_inn: str
    session_id: str | None = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class RankingExplanation(BaseModel):
    reason: str
    factor: str
    weight: float = 0.0


class STEResult(BaseModel):
    id: int
    name: str
    category: str | None = None
    attributes: dict | None = None
    score: float = 0.0
    explanations: list[RankingExplanation] = []


class SearchResponse(BaseModel):
    query: str
    corrected_query: str | None = None
    did_you_mean: str | None = None
    total: int
    results: list[STEResult]


# --- Events ---

class EventCreate(BaseModel):
    user_inn: str
    ste_id: int
    event_type: str = Field(..., pattern="^(click|view|compare|like|bounce|hide)$")
    session_id: str | None = None
    query: str | None = None
    meta: dict | None = None


class EventResponse(BaseModel):
    id: int
    created_at: datetime


# --- Autocomplete ---

class SuggestResponse(BaseModel):
    suggestions: list[str]


# --- User Profile ---

class OnboardingRequest(BaseModel):
    inn: str
    name: str | None = None
    region: str | None = None
    industry: str | None = None


class UserProfileResponse(BaseModel):
    inn: str
    name: str | None = None
    region: str | None = None
    industry: str | None = None
    top_categories: list[str] = []
    total_contracts: int = 0
