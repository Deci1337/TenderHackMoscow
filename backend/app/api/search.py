"""Search API endpoints."""
from fastapi import APIRouter, Depends, Query
from loguru import logger

from app.models.schemas import (
    SearchRequest, SearchResponse, STEResult, TypoCorrection,
    UserProfileResponse, MetricsResponse,
)
from app.services.nlp_service import get_nlp_service, NLPService
from app.services.search_service import get_search_service, HybridSearchService
from app.services.personalization_service import get_personalization_service, PersonalizationService
from app.services.ranking_service import get_ranking_service, RankingService
from app.services.explainability_service import get_explainability_service, ExplainabilityService
from app.utils.metrics import METRICS_JUSTIFICATION

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Main search endpoint.
    Pipeline: NLP -> Hybrid Search -> Personalization -> LTR Rerank -> Explain
    """
    nlp = get_nlp_service()
    searcher = get_search_service()
    personalizer = get_personalization_service()
    ranker = get_ranking_service()
    explainer = get_explainability_service()

    query_data = nlp.process_query(request.query)
    logger.info(
        f"Search: '{request.query}' -> corrected='{query_data['corrected']}', "
        f"lemmas={query_data['lemmas']}, expanded={len(query_data['expanded_terms'])} terms"
    )

    base_results = searcher.search(query_data, top_k=request.page_size * 3)

    personalized = False
    if request.customer_inn:
        base_results = personalizer.rerank(base_results, request.customer_inn)
        personalized = personalizer._profiles.get(request.customer_inn) is not None

    user_ctx = None
    if request.customer_inn:
        user_ctx = personalizer._profiles.get(request.customer_inn)
    if user_ctx:
        base_results = ranker.rerank(base_results, user_ctx)

    for r in base_results:
        r.explanations = explainer.explain_result(r)

    start = (request.page - 1) * request.page_size
    end = start + request.page_size
    page_results = base_results[start:end]

    ste_results = [
        STEResult(
            ste_id=r.ste_id,
            name=r.name,
            category=r.category,
            attributes=r.attributes,
            relevance_score=round(r.final_score, 4),
            explanation=r.explanations[:5],
        )
        for r in page_results
    ]

    return SearchResponse(
        query=TypoCorrection(
            original=request.query,
            corrected=query_data["corrected"],
            was_corrected=query_data["was_corrected"],
        ),
        results=ste_results,
        total=len(base_results),
        page=request.page,
        page_size=request.page_size,
        personalized=personalized,
        applied_synonyms=query_data["applied_synonyms"],
    )


@router.get("/suggest")
async def suggest(
    q: str = Query(..., min_length=1),
    customer_inn: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
):
    """Autocomplete / search suggestions."""
    nlp = get_nlp_service()
    searcher = get_search_service()

    query_data = nlp.process_query(q)
    results = searcher.search(query_data, top_k=limit)

    return {
        "suggestions": [
            {"ste_id": r.ste_id, "name": r.name, "score": round(r.final_score, 3)}
            for r in results
        ],
        "corrected": query_data["corrected"] if query_data["was_corrected"] else None,
    }


@router.get("/profile/{customer_inn}", response_model=None)
async def get_profile(customer_inn: str):
    """Get user profile summary showing personalization state."""
    personalizer = get_personalization_service()
    return personalizer.get_profile_summary(customer_inn)


@router.get("/metrics")
async def get_metrics():
    """Return justified metrics list used for search quality evaluation."""
    return {
        "metrics": [
            {
                "name": k,
                "full_name": v["name"],
                "rationale": v["rationale"],
                "range": v["range"],
            }
            for k, v in METRICS_JUSTIFICATION.items()
        ]
    }
