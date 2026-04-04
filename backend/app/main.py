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

from app.api import events, products, search, users
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

        nlp = get_nlp_service()
        embedder = get_embedding_service()
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

        loop = asyncio.get_event_loop()
        _executor = ThreadPoolExecutor(max_workers=2)

        # --- NLP document cache -------------------------------------------
        # Avoids re-processing 537k rows on every restart (~4 min → instant)
        nlp_cache_path = _DATA_DIR / "ste_nlp_cache.pkl"
        documents: list = []
        texts: list[str] = []

        def _load_nlp_cache(path, expected_len: int):
            import pickle
            with open(path, "rb") as f:
                data = pickle.load(f)
            if len(data) != expected_len:
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

        for d in cached_nlp:
            doc = STEDocument(
                ste_id=d["ste_id"], name=d["name"], category=d["category"],
                attributes=d["attributes"], name_normalized=d["name_normalized"],
                lemmas=d["lemmas"],
            )
            documents.append(doc)
            texts.append(d["name"])

        # --- Embedding cache ----------------------------------------------
        cache_path = _DATA_DIR / "ste_embeddings_cache.npy"
        embs = None
        if cache_path.exists():
            cached = np.load(str(cache_path))
            if cached.shape[0] == len(documents):
                embs = cached
                logger.info(f"Loaded {len(embs)} cached embeddings from disk")
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
                parts.append(embedder.embed(texts[i : i + batch_size]))
                if (i // batch_size) % 20 == 0:
                    logger.info(f"  embeddings: {min(i + batch_size, len(texts))}/{len(texts)}")
                    await asyncio.sleep(0)
            embs = np.vstack(parts)
            np.save(str(cache_path), embs)
            logger.info("Embeddings computed and cached to disk")

        for i, doc in enumerate(documents):
            doc.embedding = embs[i]

        searcher.index_documents(documents)
        logger.info(f"BM25 + FAISS indexes ready ({len(documents)} docs)")

        ste_emb_map = {doc.ste_id: doc.embedding for doc in documents if doc.embedding is not None}

        async with async_session() as db:
            contract_rows = (await db.execute(text(
                "SELECT c.customer_inn, c.ste_id, s.category "
                "FROM contracts c JOIN ste s ON s.id = c.ste_id "
                "WHERE c.customer_inn IS NOT NULL AND c.ste_id IS NOT NULL"
            ))).all()

        user_data: dict = defaultdict(lambda: {"ste_ids": [], "categories": []})
        for inn, ste_id, category in contract_rows:
            user_data[str(inn)]["ste_ids"].append(ste_id)
            if category:
                user_data[str(inn)]["categories"].append(category)

        ps = get_personalization_service()
        for inn, data in user_data.items():
            ps.build_profile_from_contracts(
                customer_inn=inn, categories=data["categories"],
                ste_embeddings=ste_emb_map, purchased_ste_ids=data["ste_ids"],
            )
        logger.info(f"User profiles built: {len(user_data)} users")

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
app.include_router(products.router, prefix=settings.API_V1_PREFIX)


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
