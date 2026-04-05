import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import text

from app.api import events, search, users
from app.api.analytics import router as analytics_router
from app.config import settings
from app.database import Base, async_session, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

_DATA_DIR = Path(__file__).parent / "data"


async def _build_ml_indexes():
    """Background task: build BM25 + FAISS + user profiles from DB data."""
    try:
        from collections import defaultdict
        from app.services.nlp_service import get_nlp_service
        from app.services.embedding_service import get_embedding_service
        from app.services.search_service import get_search_service, STEDocument
        from app.services.personalization_service import get_personalization_service

        loop = asyncio.get_event_loop()
        _executor = ThreadPoolExecutor(max_workers=2)

        nlp = await loop.run_in_executor(_executor, get_nlp_service)
        await asyncio.sleep(0)
        embedder = await loop.run_in_executor(_executor, get_embedding_service)
        await asyncio.sleep(0)
        searcher = get_search_service()
        searcher.initialize(nlp, embedder)

        async with async_session() as db:
            rows = (await db.execute(
                text("SELECT id, name, category, attributes FROM ste ORDER BY id")
            )).mappings().all()

        if not rows:
            logger.warning("No STE data in DB -- ML search unavailable")
            return

        logger.info(f"Building ML indexes for {len(rows)} STEs...")

        # --- NLP document cache -------------------------------------------
        # Avoids re-processing 537k rows on every restart (~4 min → instant)
        nlp_cache_path = _DATA_DIR / "ste_nlp_cache.pkl"
        documents: list = []
        texts: list[str] = []

        def _load_nlp_cache(path, expected_len: int):
            import pickle
            with open(path, "rb") as f:
                data = pickle.load(f)
            # Allow small mismatch: if only a few rows were added via API,
            # reuse the cache and process only the delta below.
            if len(data) > expected_len:
                return None
            return data

        def _save_nlp_cache(path, data):
            import pickle
            with open(path, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

        def _process_rows_nlp(rows_batch):
            """CPU-heavy: normalize + lemmatize each row."""
            import pickle  # noqa: F401 (imported for type clarity)
            result = []
            for row in rows_batch:
                name = row["name"] or ""
                if not name:
                    continue
                result.append({
                    "ste_id": row["id"],
                    "name": name,
                    "category": row["category"],
                    "attributes": str(row["attributes"]) if row["attributes"] else None,
                    "name_normalized": nlp.normalize_text(name),
                    "lemmas": nlp.lemmatize(name),
                })
            return result

        cached_nlp = None
        if nlp_cache_path.exists():
            try:
                cached_nlp = await loop.run_in_executor(
                    _executor, _load_nlp_cache, nlp_cache_path, len(rows)
                )
                if cached_nlp:
                    logger.info(f"Loaded {len(cached_nlp)} NLP-processed docs from cache")
            except Exception as e:
                logger.warning(f"NLP cache load failed, will recompute: {e}")
                cached_nlp = None

        if cached_nlp is None:
            logger.info("NLP processing 537k docs in background thread (first run only)...")
            chunk_size = 20000
            raw_docs: list[dict] = []
            for chunk_start in range(0, len(rows), chunk_size):
                chunk = rows[chunk_start:chunk_start + chunk_size]
                batch = await loop.run_in_executor(_executor, _process_rows_nlp, chunk)
                raw_docs.extend(batch)
                logger.info(f"  NLP: {min(chunk_start + chunk_size, len(rows))}/{len(rows)}")
                await asyncio.sleep(0)
            await loop.run_in_executor(_executor, _save_nlp_cache, nlp_cache_path, raw_docs)
            logger.info("NLP cache saved to disk")
            cached_nlp = raw_docs
        elif len(cached_nlp) < len(rows):
            delta_rows = rows[len(cached_nlp):]
            logger.info(f"NLP cache has {len(cached_nlp)} docs, processing {len(delta_rows)} new...")
            delta = await loop.run_in_executor(_executor, _process_rows_nlp, list(delta_rows))
            cached_nlp.extend(delta)
            await loop.run_in_executor(_executor, _save_nlp_cache, nlp_cache_path, cached_nlp)
            logger.info(f"NLP cache updated (+{len(delta)})")

        def _build_docs_and_texts(cached_data):
            docs, txts = [], []
            for d in cached_data:
                docs.append(STEDocument(
                    ste_id=d["ste_id"], name=d["name"], category=d["category"],
                    attributes=d["attributes"], name_normalized=d["name_normalized"],
                    lemmas=d["lemmas"],
                ))
                txts.append(d["name"])
            return docs, txts

        documents, texts = await loop.run_in_executor(
            _executor, _build_docs_and_texts, cached_nlp
        )
        await asyncio.sleep(0)

        cache_path = _DATA_DIR / "ste_embeddings_cache.npy"
        embs = None
        if cache_path.exists():
            cached = await loop.run_in_executor(
                _executor, lambda: np.load(str(cache_path))
            )
            diff = len(documents) - cached.shape[0]
            if diff == 0:
                embs = cached
                logger.info(f"Loaded {len(embs)} cached embeddings from disk")
            elif 0 < diff <= 500:
                logger.info(
                    f"Embedding cache has {cached.shape[0]} rows, need {len(documents)} "
                    f"({diff} new). Embedding only the delta."
                )
                new_texts = texts[cached.shape[0]:]
                new_embs = await loop.run_in_executor(
                    _executor, embedder.embed, new_texts
                )
                embs = np.vstack([cached, new_embs])
                await loop.run_in_executor(
                    _executor, lambda: np.save(str(cache_path), embs)
                )
                logger.info(f"Delta embeddings computed and cache updated (+{diff})")
            else:
                logger.warning(
                    f"Embedding cache size mismatch ({cached.shape[0]} vs {len(documents)}), "
                    "will recompute"
                )

        if embs is None:
            logger.info(f"Computing embeddings for {len(texts)} documents (may take minutes)...")
            batch_size = 256
            parts = []
            for i in range(0, len(texts), batch_size):
                batch = await loop.run_in_executor(
                    _executor, embedder.embed, texts[i : i + batch_size]
                )
                parts.append(batch)
                if (i // batch_size) % 20 == 0:
                    logger.info(f"  embeddings: {min(i + batch_size, len(texts))}/{len(texts)}")
                await asyncio.sleep(0)
            embs = np.vstack(parts)
            await loop.run_in_executor(
                _executor, lambda: np.save(str(cache_path), embs)
            )
            logger.info("Embeddings computed and cached to disk")

        def _assign_embeddings(docs, embeddings):
            for i, doc in enumerate(docs):
                doc.embedding = embeddings[i]

        await loop.run_in_executor(_executor, _assign_embeddings, documents, embs)
        await asyncio.sleep(0)

        # BM25 build in small chunks so the GIL is released between each,
        # keeping the event loop responsive for health checks and SQL-fallback searches.
        chunk = 50000
        from collections import Counter
        import math

        bm25 = searcher._bm25
        bm25.doc_count = len(documents)
        total_len = 0
        doc_freqs: dict[str, int] = {}
        raw_postings: dict[str, list] = {}
        doc_lens: dict[int, int] = {}

        for ci in range(0, len(documents), chunk):
            def _bm25_pass1(docs_slice):
                _tl = 0
                _df: dict[str, int] = {}
                _rp: dict[str, list] = {}
                _dl: dict[int, int] = {}
                for doc in docs_slice:
                    dl = len(doc.lemmas)
                    _dl[doc.ste_id] = dl
                    _tl += dl
                    tf = Counter(doc.lemmas)
                    for term in tf:
                        _df[term] = _df.get(term, 0) + 1
                        _rp.setdefault(term, []).append((doc.ste_id, tf[term]))
                return _tl, _df, _rp, _dl

            sl = documents[ci:ci + chunk]
            tl, df, rp, dl = await loop.run_in_executor(_executor, _bm25_pass1, sl)
            total_len += tl
            doc_lens.update(dl)
            for t, c in df.items():
                doc_freqs[t] = doc_freqs.get(t, 0) + c
            for t, ps in rp.items():
                raw_postings.setdefault(t, []).extend(ps)
            await asyncio.sleep(0)

        bm25.avg_dl = total_len / max(bm25.doc_count, 1)

        def _bm25_pass2(k1, b, avg_dl, dc, d_freqs, r_post, d_lens):
            inv = {}
            for term, postings in r_post.items():
                dff = d_freqs[term]
                idf = math.log((dc - dff + 0.5) / (dff + 0.5) + 1.0)
                scored = []
                for ste_id, tf in postings:
                    dl = d_lens[ste_id]
                    num = tf * (k1 + 1)
                    den = tf + k1 * (1 - b + b * dl / avg_dl)
                    scored.append((ste_id, idf * num / den))
                inv[term] = scored
            return inv

        bm25._inv = await loop.run_in_executor(
            _executor, _bm25_pass2,
            bm25.k1, bm25.b, bm25.avg_dl, bm25.doc_count,
            doc_freqs, raw_postings, doc_lens,
        )
        logger.info(f"BM25 inverted index: {bm25.doc_count} docs, "
                     f"{len(bm25._inv)} unique terms, avg_dl={bm25.avg_dl:.1f}")
        await asyncio.sleep(0)

        def _build_faiss(search_svc, docs):
            docs_with_emb = [d for d in docs if d.embedding is not None]
            if docs_with_emb:
                ste_ids = [d.ste_id for d in docs_with_emb]
                matrix = np.array([d.embedding for d in docs_with_emb], dtype=np.float32)
                search_svc._faiss.build(ste_ids, matrix)
            search_svc._documents = {d.ste_id: d for d in docs}
            search_svc._initialized = True

        await loop.run_in_executor(_executor, _build_faiss, searcher, documents)
        logger.info(f"BM25 + FAISS indexes ready ({len(documents)} docs)")

        def _build_emb_map(docs):
            return {d.ste_id: d.embedding for d in docs if d.embedding is not None}

        ste_emb_map = await loop.run_in_executor(_executor, _build_emb_map, documents)
        await asyncio.sleep(0)

        async with async_session() as db:
            contract_rows = (await db.execute(text(
                "SELECT c.customer_inn, c.ste_id, s.category "
                "FROM contracts c JOIN ste s ON s.id = c.ste_id "
                "WHERE c.customer_inn IS NOT NULL AND c.ste_id IS NOT NULL"
            ))).all()

        def _build_profiles(rows, emb_map):
            ps = get_personalization_service()
            ud: dict = defaultdict(lambda: {"ste_ids": [], "categories": []})
            for inn, ste_id, category in rows:
                ud[str(inn)]["ste_ids"].append(ste_id)
                if category:
                    ud[str(inn)]["categories"].append(category)
            for inn, data in ud.items():
                ps.build_profile_from_contracts(
                    customer_inn=inn, categories=data["categories"],
                    ste_embeddings=emb_map, purchased_ste_ids=data["ste_ids"],
                )
            return len(ud)

        n_users = await loop.run_in_executor(
            _executor, _build_profiles, contract_rows, ste_emb_map
        )
        logger.info(f"User profiles built: {n_users} users")

    except Exception as e:
        logger.warning(f"ML index build failed (search will use SQL fallback): {e}")
        import traceback
        logger.debug(traceback.format_exc())


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    ml_task = asyncio.create_task(_build_ml_indexes())

    yield

    ml_task.cancel()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Personalized semantic search for the Portal of Suppliers (zakupki.mos.ru). "
        "Combines morphological analysis, typo correction, synonym expansion, "
        "BM25+vector hybrid search, CatBoost LTR ranking, and real-time personalization."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix=settings.API_V1_PREFIX)
app.include_router(events.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health():
    info = {"status": "ok", "version": settings.VERSION}
    try:
        from app.services.search_service import get_search_service
        from app.services.ranking_service import get_ranking_service
        info["ml_search"] = get_search_service()._initialized
        info["ranker_backend"] = get_ranking_service().get_backend_info()["backend"]
    except Exception:
        info["ml_search"] = False
        info["ranker_backend"] = "unavailable"
    return info
