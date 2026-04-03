"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import search, events
from app.services.nlp_service import get_nlp_service
from app.services.embedding_service import get_embedding_service
from app.services.search_service import get_search_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: initializing services...")
    nlp = get_nlp_service()
    embedder = get_embedding_service()
    searcher = get_search_service()
    searcher.initialize(nlp, embedder)
    logger.info("All services initialized")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="TenderSearch - Personalized Smart Search",
    description=(
        "Personalized semantic search for the Portal of Suppliers (zakupki.mos.ru). "
        "Combines morphological analysis, typo correction, synonym expansion, "
        "BM25+vector hybrid search, and real-time personalization."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(events.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "TenderSearch"}
