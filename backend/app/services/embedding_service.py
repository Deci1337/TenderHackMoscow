"""
Embedding Service: generates vector representations using rubert-tiny2.
Chosen rationale:
  - 312-dim output (small storage, fast similarity)
  - 73M params (lightweight, ~300MB)
  - Trained on Russian text, solid semantic quality
  - Inference ~5ms per sentence on CPU
"""
import numpy as np
from functools import lru_cache
from loguru import logger

from app.config import get_settings


class EmbeddingService:
    def __init__(self):
        self._model = None

    def initialize(self):
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer
        settings = get_settings()
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        self._model = SentenceTransformer(settings.embedding_model)
        logger.info(f"Model loaded. Embedding dim: {self._model.get_sentence_embedding_dimension()}")

    def embed(self, texts: list[str]) -> np.ndarray:
        """Encode texts into dense vectors. Returns shape (n, 312)."""
        if self._model is None:
            self.initialize()
        return self._model.encode(
            texts,
            batch_size=128,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

    def embed_single(self, text: str) -> np.ndarray:
        """Encode a single text. Returns shape (312,)."""
        return self.embed([text])[0]

    def similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Cosine similarity between two normalized vectors."""
        return float(np.dot(vec_a, vec_b))

    def batch_similarity(self, query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
        """Cosine similarities between query and multiple docs."""
        return np.dot(doc_vecs, query_vec)


@lru_cache
def get_embedding_service() -> EmbeddingService:
    svc = EmbeddingService()
    svc.initialize()
    return svc
