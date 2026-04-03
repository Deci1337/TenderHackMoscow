"""
NLP Pipeline: morphological analysis, typo correction, synonym expansion.
Uses pymorphy2 for Russian morphology, SymSpell for fast typo correction,
and a curated synonym dictionary for procurement domain terms.
"""
import re
import json
from pathlib import Path
from functools import lru_cache

import pymorphy2
from symspellpy import SymSpell, Verbosity
from loguru import logger

from app.config import get_settings

_STOPWORDS_RU = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а",
    "то", "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же",
    "вы", "за", "бы", "по", "только", "ее", "мне", "было", "вот", "от",
    "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда", "даже",
    "ну", "вдруг", "ли", "если", "уже", "или", "ни", "быть", "был",
    "него", "до", "вас", "нибудь", "опять", "уж", "вам", "ведь", "там",
    "потом", "себя", "ничего", "ей", "может", "они", "тут", "где", "есть",
    "надо", "ней", "для", "мы", "тебя", "их", "чем", "была", "сам", "чтоб",
    "без", "будто", "чего", "раз", "тоже", "себе", "под", "при",
}

PROCUREMENT_SYNONYMS: dict[str, list[str]] = {
    "бумага": ["бумага офисная", "бумага для принтера", "бумага а4"],
    "ручка": ["ручка шариковая", "ручка гелевая", "ручка канцелярская"],
    "картридж": ["тонер-картридж", "картридж для принтера", "расходный материал"],
    "компьютер": ["пк", "персональный компьютер", "системный блок", "эвм"],
    "ноутбук": ["лэптоп", "портативный компьютер", "ноут"],
    "монитор": ["дисплей", "экран"],
    "принтер": ["мфу", "печатающее устройство"],
    "стол": ["стол офисный", "стол письменный", "рабочий стол"],
    "стул": ["кресло", "кресло офисное", "стул офисный"],
    "шкаф": ["шкаф для документов", "шкаф офисный", "тумба"],
    "лампа": ["светильник", "лампа настольная", "осветительный прибор"],
    "кабель": ["провод", "шнур", "кабель сетевой"],
    "маска": ["маска медицинская", "маска защитная", "респиратор"],
    "перчатки": ["перчатки медицинские", "перчатки латексные", "перчатки нитриловые"],
    "салфетки": ["салфетки бумажные", "салфетки влажные"],
    "мыло": ["мыло жидкое", "мыло хозяйственное", "моющее средство"],
    "дверь": ["дверь межкомнатная", "дверь входная", "дверной блок"],
    "окно": ["окно пвх", "стеклопакет", "оконный блок"],
    "краска": ["краска водоэмульсионная", "лкм", "эмаль"],
    "труба": ["труба стальная", "труба пвх", "трубопровод"],
    "насос": ["насос центробежный", "помпа", "насосная станция"],
    "клапан": ["вентиль", "задвижка", "запорная арматура"],
}

_REVERSE_SYNONYMS: dict[str, str] = {}
for main_term, syns in PROCUREMENT_SYNONYMS.items():
    for s in syns:
        _REVERSE_SYNONYMS[s.lower()] = main_term


class NLPService:
    def __init__(self):
        self._morph = pymorphy2.MorphAnalyzer()
        self._symspell = SymSpell(max_dictionary_edit_distance=get_settings().symspell_max_distance)
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        pkg_path = Path(__file__).parent.parent / "data" / "frequency_dict_ru.txt"
        if pkg_path.exists():
            self._symspell.load_dictionary(str(pkg_path), term_index=0, count_index=1)
        else:
            logger.warning("Russian frequency dict not found, building from scratch")
            self._build_fallback_dict()
        self._initialized = True
        logger.info("NLP service initialized")

    def _build_fallback_dict(self):
        """Build a minimal dictionary from synonym keys + common procurement terms."""
        all_terms: list[str] = []
        for main, syns in PROCUREMENT_SYNONYMS.items():
            all_terms.append(main)
            all_terms.extend(syns)
        for term in all_terms:
            for word in term.split():
                self._symspell.create_dictionary_entry(word, 1000)

    def normalize_text(self, text: str) -> str:
        """Lowercase, strip punctuation, collapse whitespace."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\sа-яёА-ЯЁ0-9-]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def lemmatize(self, text: str) -> list[str]:
        """Morphological lemmatization of Russian text."""
        words = self.normalize_text(text).split()
        lemmas = []
        for w in words:
            if w in _STOPWORDS_RU or len(w) < 2:
                continue
            parsed = self._morph.parse(w)
            lemma = parsed[0].normal_form if parsed else w
            lemmas.append(lemma)
        return lemmas

    def correct_typos(self, text: str) -> tuple[str, bool]:
        """Correct typos using SymSpell. Returns (corrected_text, was_corrected)."""
        if not self._initialized:
            self.initialize()
        words = self.normalize_text(text).split()
        corrected_words = []
        was_corrected = False
        for word in words:
            if len(word) <= 2 or word in _STOPWORDS_RU:
                corrected_words.append(word)
                continue
            suggestions = self._symspell.lookup(
                word, Verbosity.CLOSEST, max_edit_distance=get_settings().symspell_max_distance,
            )
            if suggestions and suggestions[0].term != word:
                corrected_words.append(suggestions[0].term)
                was_corrected = True
                logger.debug(f"Typo correction: {word} -> {suggestions[0].term}")
            else:
                corrected_words.append(word)
        return " ".join(corrected_words), was_corrected

    def expand_synonyms(self, text: str) -> tuple[list[str], list[str]]:
        """Expand query with synonyms. Returns (expanded_terms, applied_synonyms)."""
        normalized = self.normalize_text(text)
        lemmas = self.lemmatize(text)
        applied = []

        expanded = list(lemmas)

        for lemma in lemmas:
            if lemma in PROCUREMENT_SYNONYMS:
                syn_lemmas = []
                for syn in PROCUREMENT_SYNONYMS[lemma]:
                    syn_lemmas.extend(self.lemmatize(syn))
                expanded.extend(syn_lemmas)
                applied.append(f"{lemma} -> {', '.join(PROCUREMENT_SYNONYMS[lemma][:3])}")

        if normalized in _REVERSE_SYNONYMS:
            main = _REVERSE_SYNONYMS[normalized]
            expanded.extend(self.lemmatize(main))
            applied.append(f"{normalized} -> {main}")

        return list(set(expanded)), applied

    def process_query(self, raw_query: str) -> dict:
        """Full NLP pipeline: normalize -> correct typos -> lemmatize -> expand synonyms."""
        if not self._initialized:
            self.initialize()

        corrected, was_corrected = self.correct_typos(raw_query)
        lemmas = self.lemmatize(corrected)
        expanded_terms, applied_synonyms = self.expand_synonyms(corrected)

        return {
            "original": raw_query,
            "corrected": corrected,
            "was_corrected": was_corrected,
            "lemmas": lemmas,
            "expanded_terms": expanded_terms,
            "applied_synonyms": applied_synonyms,
        }


@lru_cache
def get_nlp_service() -> NLPService:
    svc = NLPService()
    svc.initialize()
    return svc
