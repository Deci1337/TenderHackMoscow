import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    CategoryFacet, FacetsResponse, PopularQueriesResponse, PopularQuery,
    RankCheckResponse, RankingExplanation, SearchRequest, SearchResponse,
    STEResult, SuggestResponse, ThinkingFactor, ThinkingResponse,
)
from app.services.personalization import get_user_boosts
from app.services.query_intent import INTENT_STRATEGY, QueryIntent, detect_intent
from app.services.query_processor import process_query
from app.services.session_index import (
    get_like_dislike_boosts,
    get_session_adjustments,
    get_session_change_reason,
)

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

    # --- Query intent detection ---
    intent = detect_intent(corrected_query)
    strategy = INTENT_STRATEGY[intent]

    # --- Stage 2: Candidate retrieval with zero-result cascade ---
    candidates = await _get_candidates(req, pq, corrected_query, db, query_data)

    # Cascade 1: category filter too strict -> retry without it
    if not candidates and req.category:
        log.debug("Zero results with category filter, retrying without")
        relaxed = req.model_copy(update={"category": None})
        candidates = await _get_candidates(relaxed, pq, corrected_query, db, query_data)

    # Cascade 2: multi-word query too specific -> retry with only the most meaningful word
    if not candidates and len(pq.lemmatized.split()) > 1:
        core_word = max(pq.lemmatized.split(), key=len)
        log.debug("Zero results for '%s', retrying with core word '%s'", corrected_query, core_word)
        core_pq = process_query(core_word)
        relaxed2 = req.model_copy(update={"category": None})
        candidates = await _get_candidates(relaxed2, core_pq, core_word, db, query_data)

    if not candidates:
        return SearchResponse(query=req.query, total=0, results=[])

    # --- Exact match pinning ---
    # Pin exact matches, but reduce pin strength for domain-mismatched categories.
    q_lower = corrected_query.strip().lower()
    from app.services.personalization import INDUSTRY_CATEGORIES, DOMAIN_SPECIFIC_CATEGORIES
    user_safe_cats: set[str] = set()
    for interest in (req.interests or []):
        user_safe_cats.update(INDUSTRY_CATEGORIES.get(interest, []))

    for c in candidates:
        if (c.get("name") or "").lower() == q_lower:
            cat = c.get("category") or ""
            # If user has declared interests and this category is domain-specific for OTHER domains
            # (and not in user's safe categories), use a soft pin instead of hard pin
            is_wrong_domain = (
                user_safe_cats
                and cat in DOMAIN_SPECIFIC_CATEGORIES
                and cat not in user_safe_cats
            )
            # Wrong-domain exact matches get a very low pin (0.3) so mismatch penalty can overcome it
            c["base_score"] = 0.3 if is_wrong_domain else 999.0

    candidate_ids = [c["id"] for c in candidates]

    # --- Stage 3: SQL personalization boosts ---
    boosts = await get_user_boosts(db, req.user_inn, req.session_id, candidate_ids,
                                   request_interests=req.interests or [])

    # --- Stage 3b: Collaborative filtering boosts (co-purchase patterns) ---
    try:
        from app.services.collaborative_filter import get_collaborative_boosts
        collab = await get_collaborative_boosts(db, req.user_inn, candidate_ids)
        for ste_id, collab_boost in collab.items():
            if ste_id in boosts:
                boosts[ste_id].boost += collab_boost
                boosts[ste_id].explanations.append({
                    "reason": "Часто берут вместе с вашими прошлыми закупками",
                    "factor": "collaborative",
                    "weight": collab_boost,
                })
    except Exception:
        pass

    # --- Stage 4: Redis session adjustments + cross-session memory ---
    session_deltas: dict[int, float] = {}
    if req.session_id:
        session_deltas = await get_session_adjustments(req.user_inn, req.session_id, candidate_ids)

    # Merge persistent cross-session signals (liked/hidden IDs stored in profile_data)
    if req.user_inn:
        from app.services.session_index import get_cross_session_adjustments, get_momentum_boosts
        cross = await get_cross_session_adjustments(req.user_inn, candidate_ids, db)
        for sid, delta in cross.items():
            session_deltas[sid] = session_deltas.get(sid, 0.0) + delta

        # Session momentum: boost categories the user has been clicking this session
        if req.session_id:
            momentum = await get_momentum_boosts(req.user_inn, req.session_id, candidates)
            for sid, boost in momentum.items():
                session_deltas[sid] = session_deltas.get(sid, 0.0) + boost

    # --- Stage 4b: Like/Dislike persistent signals ---
    if req.user_inn:
        like_boosts = await get_like_dislike_boosts(req.user_inn, candidate_ids)
        for sid, delta in like_boosts.items():
            session_deltas[sid] = session_deltas.get(sid, 0.0) + delta

    # Apply intent-driven multipliers to base scores
    history_mult = strategy.get("history_weight_multiplier", 1.0)
    pop_mult = strategy.get("popularity_weight_multiplier", 1.0)
    if history_mult != 1.0 or pop_mult != 1.0:
        for sid in list(boosts):
            b = boosts[sid]
            # History factor: scale boosts from contract/category factors
            if history_mult != 1.0:
                for ex in b.explanations:
                    if ex.get("factor") in ("history", "category"):
                        ex["weight"] = float(ex["weight"]) * history_mult
                b.boost = sum(e["weight"] for e in b.explanations if float(e["weight"]) > 0)
        if pop_mult != 1.0:
            for c in candidates:
                c["base_score"] = (
                    c["base_score"] * 0.7 + c.get("popularity_norm", 0.0) * pop_mult * 0.3
                )

    # --- Stage 5: CatBoost LTR re-rank ---
    scored = _apply_catboost_rerank(candidates, boosts, session_deltas, req.user_inn, corrected_query)

    def _sort_key(item):
        _sid, score, _row, exps = item
        # Items with profile_mismatch badge always rank below items without it.
        # Within each group results are ordered by score descending.
        has_mismatch = any(e.get("factor") == "profile_mismatch" for e in exps)
        if req.sort_by == "name":
            return (1 if has_mismatch else 0, _row.get("name") or "")
        return (1 if has_mismatch else 0, -score)

    scored.sort(key=_sort_key)

    page = scored[req.offset : req.offset + req.limit]

    # --- Stage 6: Enrich page with price analytics ---
    from app.services.price_analytics import get_price_info
    page_ids = [sid for sid, _, _, _ in page]
    price_data = await get_price_info(db, page_ids)

    from datetime import datetime, timezone
    _now_resp = datetime.now(timezone.utc)

    results = [
        STEResult(
            id=sid,
            name=row["name"],
            category=row["category"],
            attributes=row["attributes"] if isinstance(row["attributes"], dict) else None,
            score=round(score, 4),
            explanations=[RankingExplanation(**e) for e in explanations],
            snippet=row.get("snippet") or None,
            avg_price=price_data.get(sid, {}).get("avg_price"),
            price_trend=price_data.get(sid, {}).get("price_trend"),
            tags=row.get("tags") or [],
            is_promoted=(
                row.get("promoted_until") is not None
                and row["promoted_until"] > _now_resp
            ),
            promotion_boost=float(row.get("promotion_boost") or 0),
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


def _single_token_name_bonus(nl: str, token: str) -> float:
    """
    Match one query token to product name. Strong weight only when the token
    hits the leading product words (title), not a related noun deep in the
    description (e.g. «карандаш» vs «карандашей» in a sharpener title).
    """
    if not token:
        return 0.0
    words = nl.split()
    if not words:
        return 0.0
    if nl.startswith(token + " ") or nl == token:
        return 1.0
    fw = words[0]
    if fw == token:
        return 1.0
    if fw.startswith(token) and len(fw) <= len(token) + 2:
        return 0.95
    if token in fw and len(token) >= 3:
        return 0.88
    if len(words) >= 2:
        w = words[1]
        if w == token or (w.startswith(token) and len(w) <= len(token) + 2):
            return 0.42
    if len(words) >= 3:
        w = words[2]
        if w == token or (w.startswith(token) and len(w) <= len(token) + 2):
            return 0.28
    for w in words[3:14]:
        if w == token or (w.startswith(token) and len(w) <= len(token) + 2):
            return 0.14
    if token in nl:
        return 0.06
    return 0.0


def _name_match_bonus(name: str, query: str) -> float:
    """
    Bonus when query text matches item name. Multi-word queries use the mean
    per-token bonus so «бумага а4» matches names that contain both concepts.
    """
    nl = " ".join(name.lower().split())
    ql = " ".join(query.lower().split())
    if not ql:
        return 0.0
    if ql in nl:
        return 1.0
    tokens = [t for t in ql.split() if len(t) >= 2]
    if len(tokens) <= 1:
        return _single_token_name_bonus(nl, ql)
    return sum(_single_token_name_bonus(nl, t) for t in tokens) / len(tokens)


def _apply_catboost_rerank(
    candidates: list[dict],
    boosts: dict,
    session_deltas: dict[int, float],
    user_inn: str,
    query: str = "",
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

        cb_vals = [reranked_map.get(c["id"], 0.0) for c in candidates]
        cb_min = min(cb_vals) if cb_vals else 0.0
        cb_max = max(cb_vals) if cb_vals else 1.0
        cb_range = (cb_max - cb_min) if cb_max > cb_min else 1.0

        from datetime import datetime, timezone
        _now_cb = datetime.now(timezone.utc)

        scored = []
        for c in candidates:
            sid = c["id"]
            base = c["base_score"]
            boost_obj = boosts[sid]
            session_d = session_deltas.get(sid, 0.0)

            cb_norm = (reranked_map.get(sid, 0.0) - cb_min) / cb_range
            nm = _name_match_bonus(c["name"], query)
            combined = 0.40 * base + 0.10 * cb_norm + 0.50 * nm + boost_obj.net_score * 0.20 + session_d * 0.05

            explanations = list(boost_obj.explanations)
            has_mismatch = any(e.get("factor") == "profile_mismatch" for e in explanations)

            # Promotion boost only for profile-matching items.
            # A promoted pen should not jump to #1 for a builder.
            promoted_until = c.get("promoted_until")
            if promoted_until and promoted_until > _now_cb and not has_mismatch:
                promotion_signal = float(c.get("promotion_boost") or 0)
                combined += promotion_signal
                explanations.append({
                    "reason": "Продвигается",
                    "factor": "promotion",
                    "weight": promotion_signal,
                })

            combined += min(c.get("order_count") or 0, 10000) / 10000 * 0.1

            scored.append((sid, combined, c, explanations))
        return scored

    except Exception as e:
        log.debug("CatBoost rerank unavailable, using base scores: %s", e)

    from datetime import datetime, timezone
    _now = datetime.now(timezone.utc)

    scored = []
    for c in candidates:
        sid = c["id"]
        base = c["base_score"]
        boost_obj = boosts[sid]
        session_d = session_deltas.get(sid, 0.0)
        nm = _name_match_bonus(c["name"], query)
        total = 0.40 * base + 0.50 * nm + boost_obj.net_score * 0.02 + session_d * 0.01

        explanations = list(boost_obj.explanations)
        has_mismatch = any(e.get("factor") == "profile_mismatch" for e in explanations)

        promoted_until = c.get("promoted_until")
        if promoted_until and promoted_until > _now and not has_mismatch:
            promotion_signal = float(c.get("promotion_boost") or 0)
            total += promotion_signal
            explanations.append({
                "reason": "Продвигается",
                "factor": "promotion",
                "weight": promotion_signal,
            })

        total += min(c.get("order_count") or 0, 10000) / 10000 * 0.1

        scored.append((sid, total, c, explanations))
    return scored


async def _get_candidates(req, pq, corrected_query: str, db: AsyncSession,
                          query_data: dict | None = None) -> list[dict]:
    """
    Try hybrid ML search (BM25 + semantic) first.
    Fall back to SQL pg_trgm + tsvector if ML services are not ready.
    """
    try:
        from app.services.search_service import get_search_service
        searcher = get_search_service()
        if searcher._initialized:
            # Reuse query_data from the outer NLP call — avoid double processing
            _qd = query_data or {}
            qtok = [w for w in corrected_query.split() if len(w) >= 2]
            pool = 8 if len(qtok) >= 2 else 3
            ml_results = searcher.search(_qd, top_k=req.limit * pool)
            return [
                {
                    "id": r.ste_id,
                    "name": r.name,
                    "category": r.category,
                    "attributes": r.attributes,
                    "tags": [],
                    "promoted_until": None,
                    "promotion_boost": 0.0,
                    "snippet": "",
                    "base_score": float(r.final_score),
                    "bm25_score": r.bm25_score,
                    "semantic_score": r.semantic_score,
                    "popularity": 0,
                    "order_count": 0,
                }
                for r in ml_results
            ]
    except Exception as e:
        log.debug("ML search unavailable, falling back to SQL: %s", e)

    # SQL fallback
    qtok = [w for w in corrected_query.split() if len(w) >= 2]
    fetch_limit = req.limit * (8 if len(qtok) >= 2 else 3)
    category_clause = "AND s.category = :category" if req.category else ""

    # Use only the lemmatized query for tsquery — no synonym expansion in SQL.
    # Adding adjective synonyms (e.g. шариковая|гелевая for ручка) matches
    # thousands of rows and forces ts_rank over the full hit-set, killing latency.
    # Synonym context is handled by NLP/homograph at query level instead.
    expanded_tsq = pq.ts_query
    # Performance-optimized SQL:
    # - similarity() moved to Python (avoids computing for all WHERE matches)
    # - tags uses @> with GIN index (= ANY doesn't use GIN, causes seqscan)
    # - two tsquery variants OR'd: expanded for recall, plainto for phrase boost
    # - ORDER BY ts_rank uses GIN index efficiently
    q_lower = corrected_query.strip().lower()
    rows = (
        await db.execute(
            text(f"""
        SELECT s.id, s.name, s.category, s.attributes, s.tags,
               s.promoted_until, s.promotion_boost,
               COALESCE(s.order_count, 0)                                      AS order_count,
               ts_rank(s.name_tsv, to_tsquery('russian', :expanded_tsq))       AS ts_score_orig,
               ts_rank(s.name_tsv, plainto_tsquery('russian', :lemma))         AS ts_score_lemma,
               ts_rank(s.name_tsv, phraseto_tsquery('russian', :lemma))        AS ts_score_phrase,
               COALESCE(s.order_count, 0)                                      AS popularity,
               0                                                                AS fresh_cnt
        FROM ste s
        WHERE s.name_tsv @@ plainto_tsquery('russian', :lemma)
           {category_clause}
        ORDER BY ts_rank(s.name_tsv, plainto_tsquery('russian', :lemma)) DESC
        LIMIT :lim
    """),
            {
                "expanded_tsq": expanded_tsq,
                "lemma": pq.lemmatized,
                "lim": fetch_limit,
                **({"category": req.category} if req.category else {}),
            },
        )
    ).mappings().all()

    # Apply negative term filter (post-retrieval)
    # "принтер -лазерный" -> exclude items whose name contains "лазерный"
    if pq.negatives:
        neg_lower = [n.lower() for n in pq.negatives]
        rows = [r for r in rows if not any(n in (r["name"] or "").lower() for n in neg_lower)]

    # trgm_score computed in Python for the top-N rows (avoids SQL seqscan over full match set)
    import difflib
    q_norm = req.query.lower()
    max_pop = max((r["popularity"] for r in rows), default=1) or 1
    candidates = [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "attributes": r["attributes"],
            "tags": r["tags"] or [],
            "promoted_until": r["promoted_until"],
            "promotion_boost": float(r["promotion_boost"] or 0),
            "snippet": "",
            "freshness_norm": 0.0,
            "popularity_norm": float(r["popularity"]) / max_pop,
            "base_score": (
                difflib.SequenceMatcher(None, r["name"].lower(), q_norm).ratio() * 0.37
                + float(r["ts_score_orig"] or 0) * 0.18
                + float(r["ts_score_lemma"] or 0) * 0.08
                + float(r["ts_score_phrase"] or 0) * 0.12
                + (float(r["popularity"]) / max_pop) * 0.18
            ),
            "bm25_score": float(r["ts_score_lemma"] or 0),
            "semantic_score": 0.0,
            "popularity": int(r["popularity"]),
            "order_count": int(r.get("order_count") or r["popularity"]),
        }
        for r in rows
    ]

    if candidates:
        try:
            from app.services.embedding_service import get_embedding_service
            embedder = get_embedding_service()
            q_vec = embedder.embed_single(corrected_query)
            # Only re-embed top-20 by text score to keep latency under 1s on CPU
            ranked = sorted(range(len(candidates)), key=lambda i: candidates[i]["base_score"], reverse=True)
            top_idx = ranked[:20]
            names = [candidates[i]["name"] for i in top_idx]
            doc_vecs = embedder.embed(names)
            sims = doc_vecs @ q_vec
            for rank_pos, orig_i in enumerate(top_idx):
                candidates[orig_i]["semantic_score"] = max(float(sims[rank_pos]), 0.0)
        except Exception:
            pass

    return candidates


@router.get("/thinking/{ste_id}", response_model=ThinkingResponse)
async def get_thinking(
    ste_id: int,
    query: str,
    user_inn: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Explain ranking decision for a specific STE item and query."""
    from datetime import datetime, timezone

    from fastapi import HTTPException

    from app.services.nlp_service import get_nlp_service

    nlp = get_nlp_service()
    query_data = nlp.process_query(query)
    pq = process_query(query_data.get("corrected", query))

    row = (
        await db.execute(
            text("""
                SELECT s.id, s.name, s.category, s.tags, s.promoted_until,
                       s.promotion_boost, s.order_count,
                       COALESCE(sp.contract_cnt, 0) AS contract_cnt,
                       ts_rank(s.name_tsv, plainto_tsquery('russian', :lemma)) AS ts_score,
                       similarity(s.name, :orig) AS trgm_score
                FROM ste s
                LEFT JOIN ste_popularity sp ON sp.ste_id = s.id
                WHERE s.id = :ste_id
            """),
            {"ste_id": ste_id, "lemma": pq.lemmatized, "orig": query},
        )
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="STE not found")

    now = datetime.now(timezone.utc)
    is_promoted = row.promoted_until is not None and row.promoted_until > now

    factors = [
        ThinkingFactor(name="Совпадение по tsvector", score=round(float(row.ts_score), 4), type="text"),
        ThinkingFactor(name="Триграмное сходство", score=round(float(row.trgm_score), 4), type="text"),
        ThinkingFactor(name="Популярность (кол-во контрактов)", score=int(row.contract_cnt), type="popularity"),
    ]
    if is_promoted:
        factors.append(
            ThinkingFactor(
                name="Активное продвижение",
                score=float(row.promotion_boost or 2.0),
                type="promotion",
            )
        )

    return ThinkingResponse(
        ste_id=ste_id,
        name=row.name,
        query=query,
        corrected_query=query_data.get("corrected", query),
        applied_synonyms=query_data.get("applied_synonyms", []),
        was_corrected=query_data.get("was_corrected", False),
        factors=factors,
        is_promoted=is_promoted,
        promotion_boost=float(row.promotion_boost or 0),
        tags=row.tags or [],
    )


@router.get("/rank-check", response_model=RankCheckResponse)
async def rank_check(
    query: str,
    product_id: int,
    user_inn: str = "",
    db: AsyncSession = Depends(get_db),
):
    """
    Return the position and score of a specific product for a given query.
    Useful for suppliers to see how well their product ranks before promotion.
    """
    from app.schemas import SearchRequest

    intent = detect_intent(query)
    strategy = INTENT_STRATEGY[intent]

    req = SearchRequest(
        query=query,
        user_inn=user_inn,
        limit=100,
        offset=0,
    )
    pq = process_query(query)
    candidates = await _get_candidates(req, pq, query, db)
    if not candidates:
        return RankCheckResponse(
            product_id=product_id,
            query=query,
            position=None,
            score=None,
            intent=intent.value,
            intent_description=strategy.get("description", ""),
            is_promoted=False,
        )

    boosts = await get_user_boosts(db, user_inn, None, [c["id"] for c in candidates])
    scored = _apply_catboost_rerank(candidates, boosts, {}, user_inn, query)
    scored.sort(key=lambda x: x[1], reverse=True)

    for pos, (sid, score, row, _) in enumerate(scored, start=1):
        if sid == product_id:
            from datetime import datetime, timezone
            is_promo = (
                row.get("promoted_until") is not None
                and row["promoted_until"] > datetime.now(timezone.utc)
            )
            return RankCheckResponse(
                product_id=product_id,
                query=query,
                position=pos,
                score=round(score, 4),
                intent=intent.value,
                intent_description=strategy.get("description", ""),
                is_promoted=is_promo,
            )

    return RankCheckResponse(
        product_id=product_id,
        query=query,
        position=None,
        score=None,
        intent=intent.value,
        intent_description=strategy.get("description", ""),
        is_promoted=False,
    )


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


@router.get("/debug")
async def debug_query(q: str, db: AsyncSession = Depends(get_db)):
    """
    Explain how any query is processed: lemmatization, synonyms,
    transliteration, catalog expansion, negative terms.
    Useful for testing and transparency — works with any arbitrary query.
    """
    from app.services.synonyms import get_synonyms
    from app.services.catalog_expander import expand_from_catalog

    pq = process_query(q)

    # Manual synonyms from dictionary
    manual_syns: list[str] = []
    for lemma in pq.lemmatized.split():
        manual_syns.extend(get_synonyms(lemma))

    # Catalog-driven expansion
    catalog_terms: list[str] = []
    try:
        catalog_terms = await expand_from_catalog(db, pq.lemmatized.split())
    except Exception as e:
        catalog_terms = [f"error: {e}"]

    # Boilerplate stripping demo
    from app.services.query_processor import strip_procurement_boilerplate
    stripped = strip_procurement_boilerplate(q)

    return {
        "input": q,
        "after_boilerplate_strip": stripped,
        "after_transliteration": pq.original,
        "lemmatized": pq.lemmatized,
        "ts_query_base": pq.ts_query,
        "negative_terms": pq.negatives,
        "manual_synonyms": manual_syns,
        "catalog_expansion": catalog_terms,
        "final_ts_query": " | ".join(
            dict.fromkeys(pq.lemmatized.split() + manual_syns + catalog_terms)
        ),
        "notes": {
            "lemmatization": "generic — works for any Russian word via pymorphy3",
            "synonyms": f"{len(manual_syns)} terms from manual dictionary (abbreviations/jargon)",
            "catalog_expansion": f"{len(catalog_terms)} terms found via trigram similarity in product catalog",
            "negative_queries": "generic — parses '-word' or 'не word' from any query",
            "phrase_search": "generic — phraseto_tsquery works for any multi-word input",
        }
    }


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
