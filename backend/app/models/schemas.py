from pydantic import BaseModel, Field
from datetime import datetime


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    customer_inn: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class STEResult(BaseModel):
    ste_id: int
    name: str
    category: str | None
    attributes: str | None
    relevance_score: float
    explanation: list[str] = []


class TypoCorrection(BaseModel):
    original: str
    corrected: str
    was_corrected: bool


class SearchResponse(BaseModel):
    query: TypoCorrection
    results: list[STEResult]
    total: int
    page: int
    page_size: int
    personalized: bool
    applied_synonyms: list[str] = []


class InteractionEvent(BaseModel):
    customer_inn: str
    ste_id: int
    query_text: str | None = None
    action: str = Field(..., pattern="^(click|view|bounce|add_to_compare|purchase)$")
    dwell_time_ms: int | None = None


class InteractionResponse(BaseModel):
    status: str = "ok"
    profile_updated: bool = False


class UserProfileResponse(BaseModel):
    customer_inn: str
    customer_name: str | None
    region: str | None
    preferred_categories: list[str]
    total_contracts: int
    updated_at: datetime | None


class MetricsResponse(BaseModel):
    metric_name: str
    value: float
    description: str
