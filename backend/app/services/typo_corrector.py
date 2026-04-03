"""
Typo correction using SymSpell + custom procurement vocabulary.
No external APIs, no LLMs -- only local dictionary.
"""
import logging
import os
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

_corrector = None

PROCUREMENT_VOCAB = [
    "бумага", "офисная", "офисный", "канцелярский", "канцелярские",
    "картридж", "тонер", "принтер", "лазерный", "струйный",
    "компьютер", "ноутбук", "монитор", "клавиатура", "мышь",
    "мебель", "стол", "стул", "кресло", "шкаф", "полка",
    "медицинский", "медицинская", "маска", "перчатки", "антисептик",
    "бахилы", "халат", "аптечка", "градусник", "шприц",
    "строительный", "стройматериалы", "цемент", "краска", "труба",
    "дверь", "окно", "плитка", "кирпич", "песок", "щебень",
    "электрический", "кабель", "провод", "лампа", "светильник",
    "ручка", "карандаш", "степлер", "скрепки", "папка", "файл",
    "калькулятор", "ножницы", "клей", "скотч", "линейка",
    "учебник", "парта", "доска", "проектор", "экран",
    "насос", "счетчик", "вентиль", "кран", "радиатор",
    "огнетушитель", "порошковый", "углекислотный",
    "салфетки", "мыло", "моющий", "средство", "тряпка",
    "сетевой", "флеш", "накопитель", "жесткий", "диск",
    "нитриловые", "латексные", "хирургические",
    "водоэмульсионная", "акриловая", "масляная",
    "канализационная", "полипропиленовая", "металлическая",
    "двухстворчатое", "трехстворчатое", "однокамерное",
    "школьная", "двухместная", "трехместная",
    "маркерная", "магнитная", "меловая",
    "мультимедийный", "интерактивный",
    "циркуляционный", "погружной", "дренажный",
    "бытовой", "промышленный", "коммерческий",
    "поставщик", "закупка", "контракт", "тендер", "аукцион",
    "госзакупки", "заказчик", "подрядчик", "субподрядчик",
    "спецификация", "техническое", "задание",
]


def _get_corrector():
    global _corrector
    if _corrector is not None:
        return _corrector

    try:
        from symspellpy import SymSpell, Verbosity

        sym = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

        dict_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "ru_freq_dict.txt"
        )
        if os.path.exists(dict_path):
            sym.load_dictionary(dict_path, 0, 1, separator=" ")
            log.info("SymSpell: loaded frequency dictionary from %s", dict_path)
        else:
            log.info("SymSpell: no frequency dict, using procurement vocabulary only")

        for word in PROCUREMENT_VOCAB:
            sym.create_dictionary_entry(word, 100_000)

        _corrector = sym
        log.info("SymSpell initialized with %d procurement terms", len(PROCUREMENT_VOCAB))
        return sym

    except ImportError:
        log.warning("symspellpy not installed, typo correction disabled")
        _corrector = False
        return None


def correct_query(raw: str) -> tuple[str, bool]:
    """
    Returns (corrected_query, was_corrected).
    Corrects each word independently using SymSpell.
    """
    sym = _get_corrector()
    if not sym:
        return raw, False

    from symspellpy import Verbosity

    words = raw.strip().lower().split()
    corrected = []
    changed = False

    for word in words:
        if len(word) <= 2:
            corrected.append(word)
            continue

        suggestions = sym.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)
        if suggestions and suggestions[0].term != word:
            corrected.append(suggestions[0].term)
            changed = True
        else:
            corrected.append(word)

    result = " ".join(corrected)
    return result, changed
