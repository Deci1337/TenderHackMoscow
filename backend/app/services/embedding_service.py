"""
Embedding Service: generates vector representations using rubert-tiny2.

Uses CLS-token pooling + L2 normalization (compatible with train_ranker.py cache).
312-dim output, ~73M params, ~5ms per sentence on CPU.
Redis cache layer: repeated queries hit cache (~0.1ms) instead of model (~5ms).
"""
import hashlib
import numpy as np
from functools import lru_cache
from loguru import logger

from app.config import get_settings

_CACHE_TTL = 3600


class EmbeddingService:
    def __init__(self):
        self._tokenizer = None
        self._model = None
        self._redis = None

    def initialize(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoTokenizer, AutoModel

        settings = get_settings()
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self._tokenizer = AutoTokenizer.from_pretrained(settings.EMBEDDING_MODEL)
        self._model = AutoModel.from_pretrained(settings.EMBEDDING_MODEL)
        self._model.eval()
        logger.info("Embedding model loaded (CLS pooling, L2 norm)")
        self._init_redis(settings.REDIS_URL)

    def _init_redis(self, redis_url: str):
        try:
            import redis
            self._redis = redis.from_url(redis_url, decode_responses=False)
            self._redis.ping()
            logger.info("Embedding Redis cache connected")
        except Exception:
            self._redis = None
            logger.debug("Redis not available for embedding cache, running without")

    @staticmethod
    def _cache_key(text: str) -> str:
        return "emb:" + hashlib.sha256(text.encode()).hexdigest()[:16]

    def _get_cached(self, text: str) -> np.ndarray | None:
        if self._redis is None:
            return None
        try:
            data = self._redis.get(self._cache_key(text))
            if data:
                return np.frombuffer(data, dtype=np.float32).copy()
        except Exception:
            pass
        return None

    def _set_cached(self, text: str, vec: np.ndarray):
        if self._redis is None:
            return
        try:
            self._redis.setex(self._cache_key(text), _CACHE_TTL, vec.astype(np.float32).tobytes())
        except Exception:
            pass

    def embed(self, texts: list[str]) -> np.ndarray:
        """Encode texts into dense vectors. Returns shape (n, dim)."""
        if self._model is None:
            self.initialize()
        import torch
        with torch.no_grad():
            encoded = self._tokenizer(
                texts, padding=True, truncation=True,
                max_length=128, return_tensors="pt",
            )
            output = self._model(**encoded)
            embeddings = output.last_hidden_state[:, 0]
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        return embeddings.numpy()

    def embed_single(self, text: str) -> np.ndarray:
        """Encode a single text with Redis cache. Returns shape (dim,)."""
        cached = self._get_cached(text)
        if cached is not None:
            return cached
        vec = self.embed([text])[0]
        self._set_cached(text, vec)
        return vec

    def similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        return float(np.dot(vec_a, vec_b))

    def batch_similarity(self, query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
        return np.dot(doc_vecs, query_vec)


@lru_cache
def get_embedding_service() -> EmbeddingService:
    svc = EmbeddingService()
    svc.initialize()
    return svc
