"""
Hybrid Search Service: combines BM25 (lexical) with vector similarity (semantic).
Architecture:
  1. NLP pipeline preprocesses query (typos, morphology, synonyms)
  2. BM25 scores via inverted index on lemmatized STE names (O(Q * avg_postings))
  3. Semantic scores via FAISS approximate nearest neighbor (O(log N))
  4. Linear combination: score = alpha * bm25 + (1-alpha) * semantic
  5. Personalization boost applied on top
  6. Explainability tags generated
"""
import math
import numpy as np
from collections import Counter
from dataclasses import dataclass, field
from loguru import logger

from app.config import get_settings
from app.services.nlp_service import NLPService
from app.services.embedding_service import EmbeddingService


@dataclass
class STEDocument:
    ste_id: int
    name: str
    category: str | None
    attributes: str | None
    name_normalized: str
    lemmas: list[str]
    embedding: np.ndarray | None = None


@dataclass
class SearchResult:
    ste_id: int
    name: str
    category: str | None
    attributes: str | None
    bm25_score: float = 0.0
    semantic_score: float = 0.0
    personalization_score: float = 0.0
    final_score: float = 0.0
    explanations: list[str] = field(default_factory=list)


class BM25Index:
    """Inverted-index BM25. Scoring is O(Q * avg_postings) instead of O(N * Q)."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_count = 0
        self.avg_dl = 0.0
        self._inv: dict[str, list[tuple[int, float]]] = {}
        self._id_to_idx: dict[int, int] = {}

    def build(self, documents: list[STEDocument]):
        self.doc_count = len(documents)
        total_len = 0
        doc_freqs: dict[str, int] = {}
        raw_postings: dict[str, list[tuple[int, int]]] = {}
        doc_lens: dict[int, int] = {}

        for doc in documents:
            dl = len(doc.lemmas)
            doc_lens[doc.ste_id] = dl
            total_len += dl
            tf = Counter(doc.lemmas)
            for term in tf:
                doc_freqs[term] = doc_freqs.get(term, 0) + 1
                raw_postings.setdefault(term, []).append((doc.ste_id, tf[term]))

        self.avg_dl = total_len / max(self.doc_count, 1)

        self._inv = {}
        for term, postings in raw_postings.items():
            df = doc_freqs[term]
            idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)
            scored = []
            for ste_id, tf in postings:
                dl = doc_lens[ste_id]
                num = tf * (self.k1 + 1)
                den = tf + self.k1 * (1 - self.b + self.b * dl / self.avg_dl)
                scored.append((ste_id, idf * num / den))
            self._inv[term] = scored

        logger.info(
            f"BM25 inverted index: {self.doc_count} docs, "
            f"{len(self._inv)} unique terms, avg_dl={self.avg_dl:.1f}"
        )

    def score(self, query_lemmas: list[str], top_k: int = 500) -> dict[int, float]:
        """Score documents via inverted index lookup. Returns top_k {ste_id: score}."""
        acc: dict[int, float] = {}
        for term in query_lemmas:
            postings = self._inv.get(term)
            if not postings:
                continue
            for ste_id, s in postings:
                acc[ste_id] = acc.get(ste_id, 0.0) + s
        if len(acc) <= top_k:
            return acc
        threshold = sorted(acc.values(), reverse=True)[top_k - 1]
        return {k: v for k, v in acc.items() if v >= threshold}


class FAISSIndex:
    """FAISS-backed approximate nearest neighbor index for semantic search."""

    def __init__(self):
        self._index = None
        self._ste_ids: np.ndarray | None = None

    def build(self, ste_ids: list[int], embeddings: np.ndarray):
        import faiss
        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings.astype(np.float32))
        self._ste_ids = np.array(ste_ids, dtype=np.int64)
        logger.info(f"FAISS index built: {self._index.ntotal} vectors, dim={dim}")

    def search(self, query_vec: np.ndarray, top_k: int = 200) -> dict[int, float]:
        if self._index is None:
            return {}
        q = query_vec.reshape(1, -1).astype(np.float32)
        scores, indices = self._index.search(q, top_k)
        result = {}
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                result[int(self._ste_ids[idx])] = float(score)
        return result


class HybridSearchService:
    def __init__(self):
        self._nlp: NLPService | None = None
        self._embedder: EmbeddingService | None = None
        self._bm25 = BM25Index()
        self._faiss = FAISSIndex()
        self._documents: dict[int, STEDocument] = {}
        self._initialized = False

    def initialize(self, nlp: NLPService, embedder: EmbeddingService):
        self._nlp = nlp
        self._embedder = embedder

    def index_documents(self, documents: list[STEDocument]):
        """Build all search indexes from STE documents."""
        self._documents = {d.ste_id: d for d in documents}
        self._bm25.build(documents)

        docs_with_emb = [d for d in documents if d.embedding is not None]
        if docs_with_emb:
            ste_ids = [d.ste_id for d in docs_with_emb]
            matrix = np.array([d.embedding for d in docs_with_emb], dtype=np.float32)
            self._faiss.build(ste_ids, matrix)

        self._initialized = True
        logger.info(f"Hybrid search indexed {len(documents)} documents")

    def search(
        self,
        query_data: dict,
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """Execute hybrid search using inverted BM25 + FAISS semantic."""
        settings = get_settings()
        top_k = top_k or settings.search_top_k

        lemmas = query_data["expanded_terms"]
        corrected = query_data["corrected"]

        bm25_scores = self._bm25.score(lemmas, top_k=top_k * 5)

        semantic_scores: dict[int, float] = {}
        if self._embedder:
            q_vec = self._embedder.embed_single(corrected)
            semantic_scores = self._faiss.search(q_vec, top_k=top_k * 5)

        all_ids = set(bm25_scores.keys()) | set(semantic_scores.keys())
        max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0
        max_sem = max(semantic_scores.values()) if semantic_scores else 1.0
        alpha = settings.bm25_weight

        results: list[SearchResult] = []
        for ste_id in all_ids:
            doc = self._documents.get(ste_id)
            if not doc:
                continue
            bm25_norm = bm25_scores.get(ste_id, 0.0) / max(max_bm25, 1e-9)
            sem_norm = semantic_scores.get(ste_id, 0.0) / max(max_sem, 1e-9)
            combined = alpha * bm25_norm + (1 - alpha) * sem_norm

            explanations = []
            if bm25_norm > 0.3:
                explanations.append("High lexical match with query terms")
            if sem_norm > 0.5:
                explanations.append("Strong semantic similarity to query")

            results.append(SearchResult(
                ste_id=ste_id,
                name=doc.name,
                category=doc.category,
                attributes=doc.attributes,
                bm25_score=bm25_norm,
                semantic_score=sem_norm,
                final_score=combined,
                explanations=explanations,
            ))

        results.sort(key=lambda r: r.final_score, reverse=True)
        return results[:top_k]


_search_service: HybridSearchService | None = None


def get_search_service() -> HybridSearchService:
    global _search_service
    if _search_service is None:
        _search_service = HybridSearchService()
    return _search_service
