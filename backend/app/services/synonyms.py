"""
Synonym expansion for procurement domain.
Manually curated -- no external APIs or LLMs.
Expands user query with domain-specific synonyms so that:
  "компьютер" also matches "ПК", "ПЭВМ", "системный блок"
  "принтер" also matches "МФУ", "печатающее устройство"
"""
import logging
import re

log = logging.getLogger(__name__)

SYNONYM_MAP: dict[str, list[str]] = {
    "компьютер": ["пк", "пэвм", "системный блок", "персональный компьютер", "рабочая станция"],
    "ноутбук": ["лэптоп", "портативный компьютер", "переносной компьютер"],
    "принтер": ["мфу", "печатающее устройство", "принтер лазерный"],
    "мфу": ["принтер", "многофункциональное устройство", "копир"],
    "картридж": ["тонер", "тонер-картридж", "расходный материал"],
    "тонер": ["картридж", "тонер-картридж"],
    "монитор": ["дисплей", "экран"],
    "бумага": ["бумага офисная", "бумага для принтера", "бумага писчая"],
    "ручка": ["ручка шариковая", "ручка гелевая", "ручка перьевая"],
    "стул": ["кресло", "стул офисный", "сиденье"],
    "кресло": ["стул", "кресло офисное", "кресло руководителя"],
    "стол": ["стол офисный", "стол компьютерный", "стол письменный"],
    "маска": ["маска медицинская", "маска защитная", "респиратор"],
    "перчатки": ["перчатки нитриловые", "перчатки латексные", "перчатки медицинские"],
    "антисептик": ["дезинфицирующее средство", "санитайзер", "антисептик для рук"],
    "мыло": ["мыло жидкое", "мыло хозяйственное", "моющее средство"],
    "лампа": ["лампочка", "лампа светодиодная", "лампа накаливания", "led лампа"],
    "кабель": ["провод", "шнур", "кабель сетевой", "патч-корд"],
    "флешка": ["флеш-накопитель", "usb накопитель", "usb флешка"],
    "учебник": ["учебное пособие", "методическое пособие"],
    "парта": ["стол школьный", "парта школьная"],
    "доска": ["доска маркерная", "доска магнитная", "доска меловая", "доска интерактивная"],
    "проектор": ["проектор мультимедийный", "видеопроектор"],
    "огнетушитель": ["огнетушитель порошковый", "средство пожаротушения"],
    "цемент": ["цемент м500", "портландцемент", "вяжущее"],
    "краска": ["краска водоэмульсионная", "эмаль", "лакокрасочный материал"],
    "дверь": ["дверь межкомнатная", "дверной блок"],
    "окно": ["окно пвх", "стеклопакет", "оконный блок"],
}

_reverse_map: dict[str, str] | None = None


def _build_reverse():
    global _reverse_map
    if _reverse_map is not None:
        return
    _reverse_map = {}
    for key, synonyms in SYNONYM_MAP.items():
        for syn in synonyms:
            norm = syn.lower().strip()
            if norm not in _reverse_map:
                _reverse_map[norm] = key


def expand_query(query: str) -> tuple[str, list[str]]:
    """
    Returns (expanded_query, list_of_applied_synonyms).
    Adds synonym terms to the query string for broader matching.
    """
    _build_reverse()
    words = re.split(r"\s+", query.strip().lower())
    expansions: list[str] = []
    expanded_parts = list(words)

    for word in words:
        if word in SYNONYM_MAP:
            top_synonyms = SYNONYM_MAP[word][:2]
            for syn in top_synonyms:
                if syn.lower() not in expanded_parts:
                    expanded_parts.append(syn.lower())
                    expansions.append(f"{word} -> {syn}")

    full = query.strip()
    if words:
        bigram = " ".join(words)
        if bigram in SYNONYM_MAP:
            top_synonyms = SYNONYM_MAP[bigram][:2]
            for syn in top_synonyms:
                expanded_parts.append(syn.lower())
                expansions.append(f"{bigram} -> {syn}")

    if assert_map := _reverse_map:
        for word in words:
            if word in assert_map:
                main = assert_map[word]
                if main not in expanded_parts:
                    expanded_parts.append(main)
                    expansions.append(f"{word} -> {main}")

    expanded = " ".join(expanded_parts)
    return expanded, expansions
