from datetime import datetime

from pydantic import BaseModel, Field


# --- Search ---

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    user_inn: str
    session_id: str | None = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    sort_by: str = Field("relevance", pattern="^(relevance|popularity|name)$")
    category: str | None = None
    # Declared user interests — used to steer NLP synonym expansion and personalization
    interests: list[str] = []


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
    snippet: str | None = None      # ts_headline excerpt with <<matched>> markers
    avg_price: float | None = None  # average historical contract price
    price_trend: str | None = None  # "up" | "down" | "stable"
    tags: list[str] = []
    is_promoted: bool = False
    promotion_boost: float = 0.0
    creator_user_id: str | None = None


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
    event_type: str = Field(..., pattern="^(click|view|compare|like|dislike|bounce|hide)$")
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
    interests: list[str] = []


class UserProfileResponse(BaseModel):
    inn: str
    name: str | None = None
    region: str | None = None
    industry: str | None = None
    top_categories: list[str] = []
    total_contracts: int = 0


class CategoryFacet(BaseModel):
    name: str
    count: int


class FacetsResponse(BaseModel):
    categories: list[CategoryFacet]


class PopularQuery(BaseModel):
    query: str
    count: int


class PopularQueriesResponse(BaseModel):
    queries: list[PopularQuery]



# --- Thinking / Ranking explanation (Sprint 2) ---

class ThinkingFactor(BaseModel):
    name: str
    score: float
    type: str  # "text" | "popularity" | "promotion" | "personalization"


class ThinkingResponse(BaseModel):
    ste_id: int
    name: str
    query: str
    corrected_query: str
    applied_synonyms: list[str]
    was_corrected: bool
    factors: list[ThinkingFactor]
    is_promoted: bool
    promotion_boost: float
    tags: list[str]


# --- Analytics / Supplier Dashboard (Sprint 2+) ---

class ProductAnalyticsResponse(BaseModel):
    product_id: int
    name: str
    total_views: int
    total_clicks: int
    total_likes: int
    total_dislikes: int
    total_compares: int
    top_search_queries: list[str]
    avg_price: float | None
    price_trend: str | None
    order_count: int


class RankCheckResponse(BaseModel):
    product_id: int
    query: str
    position: int | None       # 1-based rank in results, None = not found in top-100
    score: float | None
    intent: str
    intent_description: str
    is_promoted: bool


class PriceBenchmarkResponse(BaseModel):
    ste_id: int
    name: str
    avg_price: float | None
    min_price: float | None
    max_price: float | None
    recent_avg: float | None   # last 6 months
    price_trend: str           # "up" | "down" | "stable"
    contract_count: int
    recent_count: int


class HotItemResponse(BaseModel):
    id: int
    name: str
    category: str | None
    hot_score: float
    recent_views: int
    recent_contracts: int
    price_drop: bool


# --- User Interest Summary (Sprint 3) ---

class CategoryInterest(BaseModel):
    category: str
    click_count: int
    contract_count: int
    weight: float
    trend: str                  # "rising" | "stable" | "fading"
    last_interaction_days: int  # 0 = today, -1 = never


class UserInterestSummary(BaseModel):
    inn: str
    label: str | None = None
    top_categories: list[CategoryInterest]
    session_clicks_total: int
    recent_query: str | None = None
    active_interests: list[str]
    fading_interests: list[str]
    last_updated: str
