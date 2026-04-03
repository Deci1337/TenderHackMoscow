"""
Hybrid Search Service: combines BM25 (lexical) with vector similarity (semantic).
Architecture:
  1. NLP pipeline preprocesses query (typos, morphology, synonyms)
  2. BM25 scores computed via TF-IDF on lemmatized STE names
  3. Semantic scores via cosine similarity of query embedding vs STE embeddings
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
from app.services.nlp_service import NLPService, get_nlp_service
from app.services.embedding_service import EmbeddingService, get_embedding_service


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
    """In-memory BM25 index over lemmatized STE names."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_count = 0
        self.avg_dl = 0.0
        self.doc_freqs: dict[str, int] = {}
        self.doc_lens: list[int] = []
        self.term_freqs: list[dict[str, int]] = []
        self.doc_ids: list[int] = []

    def build(self, documents: list[STEDocument]):
        self.doc_count = len(documents)
        total_len = 0
        self.doc_freqs = {}
        self.doc_lens = []
        self.term_freqs = []
        self.doc_ids = []

        for doc in documents:
            tf = Counter(doc.lemmas)
            self.term_freqs.append(dict(tf))
            self.doc_lens.append(len(doc.lemmas))
            self.doc_ids.append(doc.ste_id)
            total_len += len(doc.lemmas)
            for term in set(doc.lemmas):
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        self.avg_dl = total_len / max(self.doc_count, 1)
        logger.info(f"BM25 index built: {self.doc_count} docs, {len(self.doc_freqs)} unique terms")

    def score(self, query_lemmas: list[str]) -> dict[int, float]:
        """Score all documents against query terms. Returns {ste_id: score}."""
        scores: dict[int, float] = {}
        for idx in range(self.doc_count):
            s = 0.0
            dl = self.doc_lens[idx]
            tf_map = self.term_freqs[idx]
            for term in query_lemmas:
                if term not in tf_map:
                    continue
                tf = tf_map[term]
                df = self.doc_freqs.get(term, 0)
                idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avg_dl)
                s += idf * numerator / denominator
            if s > 0:
                scores[self.doc_ids[idx]] = s
        return scores


class HybridSearchService:
    def __init__(self):
        self._nlp: NLPService | None = None
        self._embedder: EmbeddingService | None = None
        self._bm25 = BM25Index()
        self._documents: dict[int, STEDocument] = {}
        self._embeddings_matrix: np.ndarray | None = None
        self._ste_id_order: list[int] = []
        self._initialized = False

    def initialize(self, nlp: NLPService, embedder: EmbeddingService):
        self._nlp = nlp
        self._embedder = embedder

    def index_documents(self, documents: list[STEDocument]):
        """Build the search index from STE documents."""
        self._documents = {d.ste_id: d for d in documents}
        self._bm25.build(documents)

        docs_with_emb = [d for d in documents if d.embedding is not None]
        if docs_with_emb:
            self._ste_id_order = [d.ste_id for d in docs_with_emb]
            self._embeddings_matrix = np.array([d.embedding for d in docs_with_emb])
        self._initialized = True
        logger.info(f"Hybrid search indexed {len(documents)} documents")

    def search(
        self,
        query_data: dict,
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """
        Execute hybrid search.
        query_data comes from NLPService.process_query().
        """
        settings = get_settings()
        top_k = top_k or settings.search_top_k

        lemmas = query_data["expanded_terms"]
        corrected = query_data["corrected"]

        bm25_scores = self._bm25.score(lemmas)

        semantic_scores: dict[int, float] = {}
        if self._embeddings_matrix is not None and self._embedder:
            q_vec = self._embedder.embed_single(corrected)
            sims = self._embedder.batch_similarity(q_vec, self._embeddings_matrix)
            for i, ste_id in enumerate(self._ste_id_order):
                semantic_scores[ste_id] = float(sims[i])

        all_ids = set(bm25_scores.keys()) | set(semantic_scores.keys())

        max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0
        max_sem = max(semantic_scores.values()) if semantic_scores else 1.0

        results: list[SearchResult] = []
        alpha = settings.bm25_weight

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
