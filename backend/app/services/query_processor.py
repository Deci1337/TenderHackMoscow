"""
Query preprocessing pipeline.

Runs before the search SQL hits PostgreSQL:
  1. Lowercase + strip
  2. Lemmatize each token with pymorphy2 (Russian morphology)
  3. Build tsquery-compatible string (AND of lemmas)
  4. Return original, lemmatized, and tsquery forms

This gives us proper handling of:
  "ноутбуков"  -> "ноутбук"
  "школьных парт" -> "школьный парта"
  so PostgreSQL tsvector index matches correctly.
"""
import logging
import re
from functools import lru_cache

log = logging.getLogger(__name__)

# Lazy-load pymorphy2 to avoid import cost at startup if library missing
_morph = None


def _get_morph():
    global _morph
    if _morph is None:
        try:
            import pymorphy2
            _morph = pymorphy2.MorphAnalyzer()
            log.info("pymorphy2 MorphAnalyzer loaded")
        except ImportError:
            log.warning("pymorphy2 not installed — morphology disabled")
            _morph = False
    return _morph if _morph else None


STOP_WORDS = {
    "и", "в", "на", "с", "по", "для", "из", "или", "а", "но",
    "не", "что", "это", "как", "к", "о", "от", "до", "же",
}


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[\s\-/,;]+", text.strip().lower()) if len(t) > 1]


@lru_cache(maxsize=4096)
def _lemmatize_word(word: str) -> str:
    morph = _get_morph()
    if morph is None:
        return word
    parsed = morph.parse(word)
    if not parsed:
        return word
    return parsed[0].normal_form


def process_query(raw: str) -> "ProcessedQuery":
    """
    Returns a ProcessedQuery with all forms needed by the search endpoint.
    Cached at the word level so repeated tokens are free.
    """
    tokens = _tokenize(raw)
    if not tokens:
        return ProcessedQuery(original=raw, lemmatized=raw, ts_query=raw)

    lemmas = [
        _lemmatize_word(t)
        for t in tokens
        if t not in STOP_WORDS
    ] or tokens  # fall back to original tokens if all were stop-words

    lemmatized = " ".join(lemmas)

    # Build tsquery: each lemma as a separate OR so partial matches work
    # e.g. "школьная парта" -> "школьный | парта"
    ts_query = " | ".join(lemmas)

    return ProcessedQuery(original=raw, lemmatized=lemmatized, ts_query=ts_query)


class ProcessedQuery:
    __slots__ = ("original", "lemmatized", "ts_query")

    def __init__(self, original: str, lemmatized: str, ts_query: str):
        self.original = original
        self.lemmatized = lemmatized
        self.ts_query = ts_query

    def __repr__(self) -> str:
        return f"ProcessedQuery(orig={self.original!r}, lemma={self.lemmatized!r})"
