"""
Query Intent Detection.

Classifies incoming search queries into semantic intent buckets so the
ranking pipeline can apply intent-specific strategies instead of a
single generic formula.

Intents
-------
reorder        "снова", "ещё раз", "как в прошлый раз" — repeat purchase
price_check    "цена", "стоимость", "сколько" — buyer wants price context
spec_search    query contains digits, ГОСТ, артикул, unit marks — precise spec
category_browse  1-2 generic words without qualifiers — browsing a category
general        everything else
"""
import re
from enum import Enum


class QueryIntent(str, Enum):
    REORDER = "reorder"
    PRICE_CHECK = "price_check"
    SPEC_SEARCH = "spec_search"
    CATEGORY_BROWSE = "category_browse"
    GENERAL = "general"


_REORDER_PATTERNS = re.compile(
    r"\b(снова|ещё раз|опять|повтор|как в прошлый раз|как прошлый раз|заново)\b",
    re.IGNORECASE,
)

_PRICE_PATTERNS = re.compile(
    r"\b(цена|цены|стоимость|стоимости|сколько стоит|почём|расценки|прайс)\b",
    re.IGNORECASE,
)

# Артикул / ГОСТ / ТУ / unit patterns: digits, uppercase letter-digit combos, slashes
_SPEC_PATTERNS = re.compile(
    r"(\d{4,}|гост\s*р?\s*\d|ту\s+\d|\b[A-Z]{2,}\d{2,}|\b\d+[xх]\d+|\b\d+\s*(мм|см|м|л|кг|г|шт|уп)\b)",
    re.IGNORECASE,
)

# Stop words that turn a short query into "general" rather than "browse"
_STOP_WORDS = frozenset({
    "купить", "найти", "заказать", "поставка", "подобрать",
    "нужен", "нужна", "нужны", "требуется", "ищу",
})


def detect_intent(query: str) -> QueryIntent:
    """
    Return the dominant intent for a search query.
    Runs in O(n) with no I/O — safe to call on every request.
    """
    q = query.strip()
    if not q:
        return QueryIntent.GENERAL

    if _REORDER_PATTERNS.search(q):
        return QueryIntent.REORDER

    if _PRICE_PATTERNS.search(q):
        return QueryIntent.PRICE_CHECK

    if _SPEC_PATTERNS.search(q):
        return QueryIntent.SPEC_SEARCH

    words = [w for w in re.split(r"\s+", q.lower()) if len(w) >= 2]
    content_words = [w for w in words if w not in _STOP_WORDS]
    if len(content_words) <= 2 and not any(c.isdigit() for c in q):
        return QueryIntent.CATEGORY_BROWSE

    return QueryIntent.GENERAL


# Intent → ranking strategy hints consumed by search.py
INTENT_STRATEGY: dict[QueryIntent, dict] = {
    QueryIntent.REORDER: {
        "history_weight_multiplier": 2.0,   # double the history boost
        "show_price_context": True,
        "description": "Повторная закупка — ваши прошлые товары выше",
    },
    QueryIntent.PRICE_CHECK: {
        "sort_hint": "price_asc",            # suggest price-sorted view
        "show_price_context": True,
        "description": "Поиск по цене — показываем данные по контрактам",
    },
    QueryIntent.SPEC_SEARCH: {
        "trgm_weight_multiplier": 1.5,       # exact string match matters more
        "ts_weight_multiplier": 0.7,         # semantic matters less
        "description": "Точный поиск по характеристикам",
    },
    QueryIntent.CATEGORY_BROWSE: {
        "popularity_weight_multiplier": 1.8, # popular items first when browsing
        "description": "Просмотр категории — популярные товары выше",
    },
    QueryIntent.GENERAL: {
        "description": "Стандартный поиск",
    },
}
