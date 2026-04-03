from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import RankingExplanation, SearchRequest, SearchResponse, STEResult, SuggestResponse
from app.services.personalization import get_user_boosts
from app.services.query_processor import process_query
from app.services.session_index import get_session_adjustments, get_session_change_reason

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_ste(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    """
    Hybrid personalized search pipeline:
      Stage 1: Query preprocessing — lemmatization via pymorphy2
      Stage 2: Candidate retrieval — pg_trgm + tsvector (Dev 2 adds semantic here)
      Stage 3: Personalization boosts — SQL contract history + category affinity
      Stage 4: Session adjustments — Redis dynamic indexing
      Stage 5: Re-rank + build response with per-item explanations
    """
    # --- Stage 1: Query preprocessing ---
    pq = process_query(req.query)

    # --- Stage 2: Candidate retrieval ---
    fetch_limit = req.limit * 3
    candidates_sql = text("""
        SELECT id, name, category, attributes,
               similarity(name, :orig)                                  AS trgm_score,
               ts_rank(name_tsv, to_tsquery('russian', :tsq))          AS ts_score_orig,
               ts_rank(name_tsv, plainto_tsquery('russian', :lemma))   AS ts_score_lemma
        FROM ste
        WHERE name % :orig
           OR name_tsv @@ to_tsquery('russian', :tsq)
           OR name_tsv @@ plainto_tsquery('russian', :lemma)
        ORDER BY trgm_score DESC
        LIMIT :lim
    """)
    rows = (await db.execute(candidates_sql, {
        "orig": req.query,
        "tsq": pq.ts_query,
        "lemma": pq.lemmatized,
        "lim": fetch_limit,
    })).mappings().all()

    if not rows:
        return SearchResponse(query=req.query, total=0, results=[])

    candidate_ids = [r["id"] for r in rows]
    base_scores = {
        r["id"]: (
            float(r["trgm_score"] or 0) * 0.5
            + float(r["ts_score_orig"] or 0) * 0.3
            + float(r["ts_score_lemma"] or 0) * 0.2
        )
        for r in rows
    }

    # --- Stage 3: Personalization ---
    boosts = await get_user_boosts(db, req.user_inn, req.session_id, candidate_ids)

    # --- Stage 4: Session adjustments (Redis dynamic indexing) ---
    session_deltas: dict[int, float] = {}
    if req.session_id:
        session_deltas = await get_session_adjustments(req.user_inn, req.session_id, candidate_ids)

    # --- Stage 5: Re-rank ---
    scored = [
        (r["id"], base_scores[r["id"]] + boosts[r["id"]].net_score + session_deltas.get(r["id"], 0.0), r, boosts[r["id"]].explanations)
        for r in rows
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    page = scored[req.offset: req.offset + req.limit]

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

    corrected = pq.lemmatized if pq.lemmatized != req.query else None

    return SearchResponse(
        query=req.query,
        corrected_query=corrected,
        did_you_mean=ranking_change_reason,
        total=total,
        results=results,
    )


@router.get("/suggest", response_model=SuggestResponse)
async def suggest(q: str, db: AsyncSession = Depends(get_db)):
    """
    Fast autocomplete: returns up to 8 STE name suggestions for a prefix query.
    Uses pg_trgm for fuzzy prefix matching — sub-50ms on indexed data.
    """
    if not q or len(q.strip()) < 2:
        return SuggestResponse(suggestions=[])

    pq = process_query(q)
    rows = (await db.execute(text("""
        SELECT DISTINCT name
        FROM ste
        WHERE name % :q OR name ILIKE :prefix
        ORDER BY similarity(name, :q) DESC
        LIMIT 8
    """), {"q": pq.lemmatized, "prefix": f"{q.strip()}%"})).scalars().all()

    return SuggestResponse(suggestions=list(rows))
