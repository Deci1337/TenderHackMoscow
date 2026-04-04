import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import text

from app.api import events, search, users
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
        documents, texts, ids = [], [], []
        for row in rows:
            name = row["name"] or ""
            if not name:
                continue
            cat = row["category"]
            attrs = row["attributes"]
            doc = STEDocument(
                ste_id=row["id"], name=name, category=cat,
                attributes=str(attrs) if attrs else None,
                name_normalized=nlp.normalize_text(name),
                lemmas=nlp.lemmatize(name),
            )
            documents.append(doc)
            texts.append(name)
            ids.append(row["id"])

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
