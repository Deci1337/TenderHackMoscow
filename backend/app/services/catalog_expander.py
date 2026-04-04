"""
Data-driven query expansion using the product catalog itself.

Instead of relying only on a manually curated synonym dictionary, this
service queries the actual STE catalog to find words that co-occur with
the query term. This makes expansion work for ANY query, not just the
hardcoded vocabulary.

Two strategies:
  1. ts_stat vocabulary match  — find catalog lexemes with high trigram
     similarity to the query lemma (morphologically aware)
  2. Name-level trigram match  — find product names that partially match,
     extract their other tokens as related terms

The result is a set of extra OR terms that get added to the tsquery,
so a search for "сварка" also finds "сварочный аппарат", "горелка
сварочная" without any manual configuration.
"""
import asyncio
import logging
import re
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# Words shorter than this are too common / ambiguous to expand from
_MIN_WORD_LEN = 4
# Trigram threshold for considering a catalog word "related"
_TRGM_THRESHOLD = 0.35
# Maximum extra terms to add per query token
_MAX_EXTRAS = 3


async def expand_from_catalog(
    db: AsyncSession,
    lemmas: list[str],
) -> list[str]:
    """
    For each query lemma, find similar lexemes in the STE catalog vocabulary.
    Returns list of extra terms to OR into the tsquery.

    Works generically for any Russian word — no hardcoded vocabulary required.
    """
    if not lemmas:
        return []

    extras: list[str] = []
    for lemma in lemmas:
        if len(lemma) < _MIN_WORD_LEN:
            continue
        try:
            # Query ts_stat to get the catalog vocabulary, then filter by
            # trigram similarity. ts_stat returns all lexemes in the tsvector
            # column, which are already stemmed by PostgreSQL's Russian dictionary.
            rows = (await db.execute(text("""
                SELECT word
                FROM ts_stat($$SELECT name_tsv FROM ste$$)
                WHERE similarity(word, :lemma) >= :thresh
                  AND word != :lemma
                  AND length(word) >= :min_len
                ORDER BY similarity(word, :lemma) DESC
                LIMIT :max_extras
            """), {
                "lemma": lemma,
                "thresh": _TRGM_THRESHOLD,
                "min_len": _MIN_WORD_LEN,
                "max_extras": _MAX_EXTRAS,
            })).all()
            extras.extend(r[0] for r in rows)
        except Exception as e:
            log.debug("catalog expand failed for '%s': %s", lemma, e)

    return extras


async def build_expanded_tsquery(
    db: AsyncSession,
    base_lemmas: list[str],
    manual_synonyms: list[str] | None = None,
) -> str:
    """
    Build a rich tsquery OR-ing:
      1. Base lemmas from query processor
      2. Manual synonyms from SYNONYM_MAP (for abbreviations)
      3. Catalog-mined related lexemes

    This ensures generic coverage: known abbreviations handled by manual map,
    all other vocabulary covered by the catalog-driven expansion.
    """
    all_terms = list(base_lemmas)

    if manual_synonyms:
        all_terms.extend(manual_synonyms)

    catalog_terms = await expand_from_catalog(db, base_lemmas)
    all_terms.extend(catalog_terms)

    # Deduplicate preserving order, clean for tsquery
    seen: set[str] = set()
    clean: list[str] = []
    for t in all_terms:
        t = re.sub(r"[^\w\s-]", "", t, flags=re.UNICODE).strip()
        if t and t not in seen:
            seen.add(t)
            clean.append(t)

    if not clean:
        return ""

    return " | ".join(clean)
