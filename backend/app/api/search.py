import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import RankingExplanation, SearchRequest, SearchResponse, STEResult, SuggestResponse
from app.services.personalization import get_user_boosts
from app.services.query_processor import process_query
from app.services.session_index import get_session_adjustments, get_session_change_reason

log = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_ste(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """
    Hybrid personalized search pipeline:
      Stage 1: Query preprocessing — pymorphy2 lemmatization + Dev2 NLP (typos, synonyms)
      Stage 2: Candidate retrieval — pg_trgm + tsvector fallback
               OR Dev2 hybrid BM25 + semantic search (rubert-tiny2)
      Stage 3: SQL personalization boosts (contract history + category affinity)
      Stage 4: Redis session adjustments (dynamic indexing)
      Stage 5: Dev2 CatBoost LTR re-rank (if available)
      Stage 6: Build response with per-item explanations
    """
    # --- Stage 1: Query preprocessing ---
    pq = process_query(req.query)
    corrected_query = req.query
    was_corrected = False

    # Try Dev2 NLP for richer correction + synonyms
    try:
        from app.services.nlp_service import get_nlp_service
        nlp = get_nlp_service()
        query_data = nlp.process_query(req.query)
        corrected_query = query_data.get("corrected", req.query)
        was_corrected = query_data.get("was_corrected", False)
        log.debug("Dev2 NLP: corrected=%s, synonyms=%s", corrected_query, query_data.get("applied_synonyms"))
    except Exception:
        pass

    # --- Stage 2: Candidate retrieval ---
    candidates = await _get_candidates(req, pq, corrected_query, db)
    if not candidates:
        return SearchResponse(query=req.query, total=0, results=[])

    candidate_ids = [c["id"] for c in candidates]
    base_scores = {c["id"]: c["base_score"] for c in candidates}

    # --- Stage 3: SQL personalization boosts ---
    boosts = await get_user_boosts(db, req.user_inn, req.session_id, candidate_ids)

    # --- Stage 4: Redis session adjustments ---
    session_deltas: dict[int, float] = {}
    if req.session_id:
        session_deltas = await get_session_adjustments(req.user_inn, req.session_id, candidate_ids)

    # --- Stage 5: Combine scores + Dev2 CatBoost re-rank ---
    scored = [
        (
            c["id"],
            base_scores[c["id"]] + boosts[c["id"]].net_score + session_deltas.get(c["id"], 0.0),
            c,
            boosts[c["id"]].explanations,
        )
        for c in candidates
    ]

    try:
        from app.services.personalization_service import get_personalization_service
        from app.services.ranking_service import get_ranking_service
        from app.services.search_service import SearchResult
        user_ctx = get_personalization_service()._profiles.get(req.user_inn)
        if user_ctx:
            ranker = get_ranking_service()
            # Convert to SearchResult for CatBoost ranker
            sr_list = [
                SearchResult(
                    ste_id=sid, name=c["name"], category=c["category"],
                    attributes=c["attributes"], final_score=s,
                )
                for sid, s, c, _ in scored
            ]
            reranked = ranker.rerank(sr_list, user_ctx)
            # Rebuild scored preserving explanations, use reranked order
            reranked_scores = {r.ste_id: r.final_score for r in reranked}
            scored = [(sid, reranked_scores.get(sid, s), c, expl) for sid, s, c, expl in scored]
    except Exception:
        pass

    scored.sort(key=lambda x: x[1], reverse=True)
    page = scored[req.offset: req.offset + req.limit]

    # --- Stage 6: Build response ---
    results = [
        STEResult(
            id=sid, name=row["name"], category=row["category"],
            attributes=row["attributes"], score=round(score, 4),
            explanations=[RankingExplanation(**e) for e in explanations],
        )
        for sid, score, row, explanations in page
    ]

    ranking_change_reason = None
    if req.session_id:
        ranking_change_reason = await get_session_change_reason(req.user_inn, req.session_id)

    count_sql = text("""
        SELECT count(*) FROM ste
        WHERE name % :orig
           OR name_tsv @@ to_tsquery('russian', :tsq)
           OR name_tsv @@ plainto_tsquery('russian', :lemma)
    """)
    total = (await db.execute(count_sql, {
        "orig": req.query, "tsq": pq.ts_query, "lemma": pq.lemmatized,
    })).scalar() or 0

    return SearchResponse(
        query=req.query,
        corrected_query=corrected_query if was_corrected else None,
        did_you_mean=ranking_change_reason,
        total=total,
        results=results,
    )


async def _get_candidates(req, pq, corrected_query: str, db: AsyncSession) -> list[dict]:
    """
    Try Dev2 hybrid search (BM25 + semantic) first.
    Fall back to SQL pg_trgm + tsvector if ML services aren't ready.
    """
    try:
        from app.services.search_service import get_search_service
        from app.services.nlp_service import get_nlp_service
        searcher = get_search_service()
        if searcher._initialized:
            nlp = get_nlp_service()
            query_data = nlp.process_query(req.query)
            ml_results = searcher.search(query_data, top_k=req.limit * 3)
            return [
                {
                    "id": r.ste_id, "name": r.name, "category": r.category,
                    "attributes": r.attributes, "base_score": float(r.final_score),
                }
                for r in ml_results
            ]
    except Exception as e:
        log.debug("Dev2 ML search unavailable, falling back to SQL: %s", e)

    # SQL fallback
    fetch_limit = req.limit * 3
    rows = (await db.execute(text("""
        SELECT id, name, category, attributes,
               similarity(name, :orig)                               AS trgm_score,
               ts_rank(name_tsv, to_tsquery('russian', :tsq))        AS ts_score_orig,
               ts_rank(name_tsv, plainto_tsquery('russian', :lemma)) AS ts_score_lemma
        FROM ste
        WHERE name % :orig
           OR name_tsv @@ to_tsquery('russian', :tsq)
           OR name_tsv @@ plainto_tsquery('russian', :lemma)
        ORDER BY trgm_score DESC
        LIMIT :lim
    """), {
        "orig": req.query, "tsq": pq.ts_query,
        "lemma": pq.lemmatized, "lim": fetch_limit,
    })).mappings().all()

    return [
        {
            "id": r["id"], "name": r["name"], "category": r["category"],
            "attributes": r["attributes"],
            "base_score": (
                float(r["trgm_score"] or 0) * 0.5
                + float(r["ts_score_orig"] or 0) * 0.3
                + float(r["ts_score_lemma"] or 0) * 0.2
            ),
        }
        for r in rows
    ]


@router.get("/suggest", response_model=SuggestResponse)
async def suggest(q: str, db: AsyncSession = Depends(get_db)):
    """Fast autocomplete: up to 8 STE suggestions (pg_trgm, sub-50ms)."""
    if not q or len(q.strip()) < 2:
        return SuggestResponse(suggestions=[])

    pq = process_query(q)
    rows = (await db.execute(text("""
        SELECT DISTINCT name FROM ste
        WHERE name % :q OR name ILIKE :prefix
        ORDER BY similarity(name, :q) DESC
        LIMIT 8
    """), {"q": pq.lemmatized, "prefix": f"{q.strip()}%"})).scalars().all()

    return SuggestResponse(suggestions=list(rows))
