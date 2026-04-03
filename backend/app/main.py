import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import events, search, users
from app.config import settings
from app.database import Base, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    # Initialize Dev2 ML services if available
    try:
        from app.services.nlp_service import get_nlp_service
        from app.services.embedding_service import get_embedding_service
        from app.services.search_service import get_search_service
        nlp = get_nlp_service()
        embedder = get_embedding_service()
        searcher = get_search_service()
        searcher.initialize(nlp, embedder)
        logger.info("ML services initialized successfully")
    except Exception as e:
        logger.warning(f"ML services not available, running in SQL-only mode: {e}")

    yield
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Personalized semantic search for the Portal of Suppliers (zakupki.mos.ru). "
        "Combines morphological analysis, typo correction, synonym expansion, "
        "BM25+vector hybrid search, and real-time personalization."
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
    return {"status": "ok", "version": settings.VERSION}
