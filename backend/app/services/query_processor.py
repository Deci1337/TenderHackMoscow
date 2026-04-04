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

# Lazy-load pymorphy3 (preferred) or pymorphy2 as fallback
_morph = None


def _get_morph():
    global _morph
    if _morph is None:
        try:
            import pymorphy3 as pymorphy2
            _morph = pymorphy2.MorphAnalyzer()
            log.info("pymorphy3 MorphAnalyzer loaded")
        except ImportError:
            try:
                import pymorphy2
                _morph = pymorphy2.MorphAnalyzer()
                log.info("pymorphy2 MorphAnalyzer loaded (fallback)")
            except ImportError:
                log.warning("Neither pymorphy3 nor pymorphy2 installed — morphology disabled")
                _morph = False
    return _morph if _morph else None


STOP_WORDS = {
    "и", "в", "на", "с", "по", "для", "из", "или", "а", "но",
    "не", "что", "это", "как", "к", "о", "от", "до", "же",
}

# Boilerplate prefixes common in procurement queries that should be stripped
# "поставка канцтоваров" -> "канцтоваров", "закупка компьютеров" -> "компьютеров"
_PROCUREMENT_BOILERPLATE = re.compile(
    r"^(поставка|поставку|закупка|закупку|закупок|приобретение|приобретению|"
    r"покупка|покупку|снабжение|снабжению|обеспечение|обеспечению|"
    r"услуги?\s+по\s+поставке|услуги?\s+поставки|товар[ыа]?)\s+",
    re.IGNORECASE,
)


def strip_procurement_boilerplate(query: str) -> str:
    """
    Remove boilerplate procurement words from the start of a query.
    'поставка бумаги офисной' -> 'бумаги офисной'
    'закупка компьютеров' -> 'компьютеров'
    Applied iteratively to handle 'поставка товара бумага'.
    """
    cleaned = query.strip()
    for _ in range(3):  # max 3 passes
        new = _PROCUREMENT_BOILERPLATE.sub("", cleaned).strip()
        if new == cleaned:
            break
        cleaned = new
    return cleaned or query  # never return empty string


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
    raw = strip_procurement_boilerplate(raw)
    # Transliterate Latin input before lemmatization
    try:
        from app.services.transliteration import transliterate_query
        raw, _ = transliterate_query(raw)
    except Exception:
        pass
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
