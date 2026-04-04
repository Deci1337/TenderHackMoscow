import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    CategoryFacet, FacetsResponse, PopularQueriesResponse, PopularQuery,
    RankingExplanation, SearchRequest, SearchResponse, STEResult, SuggestResponse,
)
from app.services.personalization import get_user_boosts
from app.services.query_processor import process_query
from app.services.session_index import get_session_adjustments, get_session_change_reason

log = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_ste(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """
    Hybrid personalized search pipeline:
      1. NLP preprocessing (typo correction, synonyms, lemmatization)
      2. Candidate retrieval (BM25+semantic hybrid OR SQL fallback)
      3. SQL personalization boosts (contract history + category affinity)
      4. Redis session adjustments
      5. CatBoost LTR re-rank (always applied when model is loaded)
      6. Build response with explanations
    """
    try:
        import redis.asyncio as aioredis
        from app.config import get_settings
        _r = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
        await _r.zincrby("popular_queries", 1, req.query.strip().lower())
        await _r.aclose()
    except Exception:
        pass

    # --- Stage 1: Query preprocessing ---
    corrected_query = req.query
    was_corrected = False
    applied_synonyms: list[str] = []

    # Primary industry for context-aware NLP (first declared interest)
    user_industry = req.interests[0] if req.interests else None

    try:
        from app.services.nlp_service import get_nlp_service
        nlp = get_nlp_service()
        query_data = nlp.process_query(req.query, user_industry=user_industry)
        corrected_query = query_data.get("corrected", corrected_query)
        was_corrected = query_data.get("was_corrected", False)
        applied_synonyms = query_data.get("applied_synonyms", [])
    except Exception:
        pass

    pq = process_query(corrected_query)

    # --- Stage 2: Candidate retrieval with zero-result cascade ---
    candidates = await _get_candidates(req, pq, corrected_query, db)

    # Cascade 1: category filter too strict -> retry without it
    if not candidates and req.category:
        log.debug("Zero results with category filter, retrying without")
        relaxed = req.model_copy(update={"category": None})
        candidates = await _get_candidates(relaxed, pq, corrected_query, db)

    # Cascade 2: multi-word query too specific -> retry with only the most meaningful word
    if not candidates and len(pq.lemmatized.split()) > 1:
        # Use the longest lemma (most specific content word)
        core_word = max(pq.lemmatized.split(), key=len)
        log.debug("Zero results for '%s', retrying with core word '%s'", corrected_query, core_word)
        core_pq = process_query(core_word)
        relaxed2 = req.model_copy(update={"category": None})
        candidates = await _get_candidates(relaxed2, core_pq, core_word, db)

    if not candidates:
        return SearchResponse(query=req.query, total=0, results=[])

    candidate_ids = [c["id"] for c in candidates]

    # --- Stage 3: SQL personalization boosts ---
    boosts = await get_user_boosts(db, req.user_inn, req.session_id, candidate_ids)

    # --- Stage 4: Redis session adjustments ---
    session_deltas: dict[int, float] = {}
    if req.session_id:
        session_deltas = await get_session_adjustments(req.user_inn, req.session_id, candidate_ids)

    # --- Stage 5: CatBoost LTR re-rank ---
    scored = _apply_catboost_rerank(candidates, boosts, session_deltas, req.user_inn)

    if req.sort_by == "name":
        scored.sort(key=lambda x: x[2]["name"] or "")
    elif req.sort_by == "popularity":
        scored.sort(key=lambda x: x[1], reverse=True)
    else:
        scored.sort(key=lambda x: x[1], reverse=True)

    page = scored[req.offset : req.offset + req.limit]

    # --- Stage 6: Build response ---
    results = [
        STEResult(
            id=sid,
            name=row["name"],
            category=row["category"],
            attributes=row["attributes"] if isinstance(row["attributes"], dict) else None,
            score=round(score, 4),
            explanations=[RankingExplanation(**e) for e in explanations],
        )
        for sid, score, row, explanations in page
    ]

    ranking_change_reason = None
    if req.session_id:
        ranking_change_reason = await get_session_change_reason(req.user_inn, req.session_id)

    return SearchResponse(
        query=req.query,
        corrected_query=corrected_query if was_corrected else None,
        did_you_mean=ranking_change_reason,
        total=len(candidates),
        results=results,
    )


def _apply_catboost_rerank(
    candidates: list[dict],
    boosts: dict,
    session_deltas: dict[int, float],
    user_inn: str,
) -> list[tuple]:
    """
    Apply CatBoost reranking to candidates. Falls back to linear scoring
    if the model or services are unavailable.
    """
    try:
        from app.services.ranking_service import get_ranking_service
        from app.services.search_service import SearchResult
        from app.services.personalization_service import get_personalization_service

        ranker = get_ranking_service()
        user_ctx = get_personalization_service()._profiles.get(user_inn)

        sr_list = [
            SearchResult(
                ste_id=c["id"],
                name=c["name"],
                category=c["category"],
                attributes=str(c["attributes"]) if c["attributes"] else None,
                bm25_score=c.get("bm25_score", 0.0),
                semantic_score=c.get("semantic_score", 0.0),
                final_score=c["base_score"],
            )
            for c in candidates
        ]

        ste_emb_map = None
        try:
            from app.services.search_service import get_search_service
            ss = get_search_service()
            if ss._initialized:
                ste_emb_map = {
                    doc.ste_id: doc.embedding
                    for doc in ss._documents.values()
                    if doc.embedding is not None
                }
        except Exception:
            pass

        reranked = ranker.rerank(sr_list, user_ctx, ste_embeddings=ste_emb_map)
        reranked_map = {r.ste_id: r.final_score for r in reranked}

        scored = []
        for c in candidates:
            sid = c["id"]
            base = c["base_score"]
            boost_obj = boosts[sid]
            session_d = session_deltas.get(sid, 0.0)

            catboost_score = reranked_map.get(sid, base)
            combined = catboost_score + boost_obj.net_score * 0.5 + session_d * 0.3

            scored.append((sid, combined, c, boost_obj.explanations))
        return scored

    except Exception as e:
        log.debug("CatBoost rerank unavailable, using base scores: %s", e)

    scored = []
    for c in candidates:
        sid = c["id"]
        base = c["base_score"]
        boost_obj = boosts[sid]
        session_d = session_deltas.get(sid, 0.0)
        total = base + boost_obj.net_score + session_d
        scored.append((sid, total, c, boost_obj.explanations))
    return scored


async def _get_candidates(req, pq, corrected_query: str, db: AsyncSession) -> list[dict]:
    """
    Try hybrid ML search (BM25 + semantic) first.
    Fall back to SQL pg_trgm + tsvector if ML services are not ready.
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
                    "id": r.ste_id,
                    "name": r.name,
                    "category": r.category,
                    "attributes": r.attributes,
                    "base_score": float(r.final_score),
                    "bm25_score": r.bm25_score,
                    "semantic_score": r.semantic_score,
                }
                for r in ml_results
            ]
    except Exception as e:
        log.debug("ML search unavailable, falling back to SQL: %s", e)

    # SQL fallback
    fetch_limit = req.limit * 3
    category_clause = "AND s.category = :category" if req.category else ""
    await db.execute(text("SET pg_trgm.similarity_threshold = 0.1"))
    rows = (
        await db.execute(
            text(f"""
        WITH pop AS (
            SELECT ste_id, COUNT(*) AS contract_cnt
            FROM contracts
            GROUP BY ste_id
        )
        SELECT s.id, s.name, s.category, s.attributes,
               similarity(s.name, :orig)                                  AS trgm_score,
               ts_rank(s.name_tsv, to_tsquery('russian', :tsq))           AS ts_score_orig,
               ts_rank(s.name_tsv, plainto_tsquery('russian', :lemma))    AS ts_score_lemma,
               COALESCE(p.contract_cnt, 0)                                AS popularity
        FROM ste s
        LEFT JOIN pop p ON p.ste_id = s.id
        WHERE (s.name % :orig
           OR s.name_tsv @@ to_tsquery('russian', :tsq)
           OR s.name_tsv @@ plainto_tsquery('russian', :lemma)
           OR s.name ILIKE :ilike)
           {category_clause}
        ORDER BY trgm_score DESC
        LIMIT :lim
    """),
            {
                "orig": req.query,
                "tsq": pq.ts_query,
                "lemma": pq.lemmatized,
                "lim": fetch_limit,
                "ilike": f"%{req.query.strip()}%",
                **({"category": req.category} if req.category else {}),
            },
        )
    ).mappings().all()

    # Normalise popularity to [0, 0.2] so it can nudge but not dominate text score
    max_pop = max((r["popularity"] for r in rows), default=1) or 1
    candidates = [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "attributes": r["attributes"],
            "base_score": (
                float(r["trgm_score"] or 0) * 0.45
                + float(r["ts_score_orig"] or 0) * 0.25
                + float(r["ts_score_lemma"] or 0) * 0.15
                + (float(r["popularity"]) / max_pop) * 0.15   # popularity signal
            ),
            "bm25_score": float(r["trgm_score"] or 0),
            "semantic_score": 0.0,
            "popularity": int(r["popularity"]),
        }
        for r in rows
    ]

    if candidates:
        try:
            from app.services.embedding_service import get_embedding_service
            embedder = get_embedding_service()
            q_vec = embedder.embed_single(corrected_query)
            names = [c["name"] for c in candidates]
            doc_vecs = embedder.embed(names)
            sims = doc_vecs @ q_vec
            for i, c in enumerate(candidates):
                c["semantic_score"] = max(float(sims[i]), 0.0)
        except Exception:
            pass

    return candidates


@router.get("/suggest")
async def suggest(q: str = "", db: AsyncSession = Depends(get_db)):
    try:
        if not q or len(q.strip()) < 2:
            return {"suggestions": []}
        clean = q.strip()
        rows = (
            await db.execute(
                text("SELECT DISTINCT name FROM ste WHERE name ILIKE :prefix ORDER BY name LIMIT 8"),
                {"prefix": f"%{clean}%"},
            )
        ).scalars().all()
        return {"suggestions": list(rows)}
    except Exception:
        log.exception("Suggest error")
        return {"suggestions": []}


@router.get("/facets", response_model=FacetsResponse)
async def get_facets(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            text("""
        SELECT category, COUNT(*) AS cnt FROM ste
        WHERE category IS NOT NULL GROUP BY category ORDER BY cnt DESC LIMIT 30
    """)
        )
    ).mappings().all()
    return FacetsResponse(categories=[CategoryFacet(name=r["category"], count=r["cnt"]) for r in rows])


@router.get("/popular", response_model=PopularQueriesResponse)
async def get_popular_queries():
    try:
        import redis.asyncio as aioredis
        from app.config import get_settings
        s = get_settings()
        r = aioredis.from_url(s.REDIS_URL, decode_responses=True)
        pairs = await r.zrevrange("popular_queries", 0, 9, withscores=True)
        await r.aclose()
        return PopularQueriesResponse(
            queries=[PopularQuery(query=q, count=int(score)) for q, score in pairs]
        )
    except Exception:
        return PopularQueriesResponse(queries=[])
