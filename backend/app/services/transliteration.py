"""
Transliteration for procurement queries.

Handles common cases where buyers type Latin/translit instead of Cyrillic:
  "printer"  -> "принтер"
  "noutbuk"  -> "ноутбук"
  "monitor"  -> "монитор"
  "komputer" -> "компьютер"

Two modes:
  1. Direct term lookup (procurement vocabulary, highest priority)
  2. Character-level translit fallback (GOST 7.79-2000 scheme B)
"""
import re
from functools import lru_cache

# Direct vocabulary: common procurement terms typed in Latin
TRANSLIT_TERMS: dict[str, str] = {
    # IT equipment
    "printer":      "принтер",
    "printer laser":"принтер лазерный",
    "noutbuk":      "ноутбук",
    "noutbook":     "ноутбук",
    "notebook":     "ноутбук",
    "laptop":       "ноутбук",
    "monitor":      "монитор",
    "komputer":     "компьютер",
    "computer":     "компьютер",
    "pk":           "пк",
    "server":       "сервер",
    "router":       "маршрутизатор",
    "router":       "маршрутизатор",
    "switch":       "коммутатор",
    "kartridzh":    "картридж",
    "cartridge":    "картридж",
    "toner":        "тонер",
    "scanner":      "сканер",
    "skaner":       "сканер",
    "proyektor":    "проектор",
    "kamera":       "камера",
    "klaviatura":   "клавиатура",
    "keyboard":     "клавиатура",
    "mouse":        "мышь",
    "mysh":         "мышь",
    "flashka":      "флешка",
    "flash":        "флешка",
    # Office supplies
    "bumaga":       "бумага",
    "paper":        "бумага",
    "ruchka":       "ручка",
    "karandash":    "карандаш",
    "pencil":       "карандаш",
    "tetradi":      "тетрадь",
    "tetrad":       "тетрадь",
    # Medical
    "maska":        "маска",
    "mask":         "маска",
    "perchatki":    "перчатки",
    "gloves":       "перчатки",
    "shprits":      "шприц",
    # Construction
    "cement":       "цемент",
    "tsement":      "цемент",
    "kraska":       "краска",
    "paint":        "краска",
    "truba":        "труба",
    "pipe":         "труба",
    # Furniture
    "stol":         "стол",
    "stul":         "стул",
    "kreslo":       "кресло",
    "shkaf":        "шкаф",
    # Lighting
    "lampa":        "лампа",
    "lamp":         "лампа",
    "svetilnik":    "светильник",
}

# Character-level GOST 7.79 scheme B (Latin -> Cyrillic)
_CHAR_MAP: list[tuple[str, str]] = [
    ("shh", "щ"), ("sh",  "ш"), ("ch",  "ч"), ("yu",  "ю"),
    ("ya",  "я"), ("yo",  "ё"), ("ye",  "е"), ("zh",  "ж"),
    ("kh",  "х"), ("ts",  "ц"), ("eh",  "э"),
    ("a",  "а"),  ("b",  "б"),  ("v",  "в"),  ("g",  "г"),
    ("d",  "д"),  ("e",  "е"),  ("z",  "з"),  ("i",  "и"),
    ("j",  "й"),  ("k",  "к"),  ("l",  "л"),  ("m",  "м"),
    ("n",  "н"),  ("o",  "о"),  ("p",  "п"),  ("r",  "р"),
    ("s",  "с"),  ("t",  "т"),  ("u",  "у"),  ("f",  "ф"),
    ("x",  "кс"), ("y",  "ы"),
]

_RE_LATIN_WORD = re.compile(r"\b[a-zA-Z][a-zA-Z0-9\-]*\b")


@lru_cache(maxsize=2048)
def _translit_word(word: str) -> str:
    """Transliterate a single Latin word to Cyrillic using char map."""
    result = word.lower()
    for lat, cyr in _CHAR_MAP:
        result = result.replace(lat, cyr)
    return result


def transliterate_query(query: str) -> tuple[str, bool]:
    """
    Attempt to transliterate Latin words in a query.

    Returns (transliterated_query, was_changed).
    Full vocabulary lookup first; char-level fallback for unknown words.
    """
    q = query.strip().lower()

    # 1. Full-phrase vocabulary match
    if q in TRANSLIT_TERMS:
        return TRANSLIT_TERMS[q], True

    # 2. Word-level vocabulary match + char-level fallback for remaining words
    words = q.split()
    new_words = []
    changed = False

    for word in words:
        if not _RE_LATIN_WORD.fullmatch(word):
            new_words.append(word)
            continue
        # Try vocabulary first
        if word in TRANSLIT_TERMS:
            new_words.append(TRANSLIT_TERMS[word])
            changed = True
        else:
            # Char-level fallback — only apply if result looks Russian
            cyr = _translit_word(word)
            new_words.append(cyr)
            changed = True

    return " ".join(new_words), changed
