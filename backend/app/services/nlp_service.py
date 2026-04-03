"""
NLP Pipeline: morphological analysis, typo correction, synonym expansion.
Uses pymorphy2 for Russian morphology, SymSpell for fast typo correction,
and a curated synonym dictionary for procurement domain terms.
"""
import re
from collections import Counter
from pathlib import Path
from functools import lru_cache

try:
    import pymorphy3 as pymorphy2
except ImportError:
    import pymorphy2
from symspellpy import SymSpell, Verbosity
from loguru import logger

from app.config import get_settings

_STOPWORDS_RU = frozenset({
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а",
    "то", "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же",
    "вы", "за", "бы", "по", "только", "ее", "мне", "было", "вот", "от",
    "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда", "даже",
    "ну", "вдруг", "ли", "если", "уже", "или", "ни", "быть", "был",
    "него", "до", "вас", "нибудь", "опять", "уж", "вам", "ведь", "там",
    "потом", "себя", "ничего", "ей", "может", "они", "тут", "где", "есть",
    "надо", "ней", "для", "мы", "тебя", "их", "чем", "была", "сам", "чтоб",
    "без", "будто", "чего", "раз", "тоже", "себе", "под", "при",
})

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
    "флеш": ["флешка", "usb-накопитель", "флеш-драйв"],
    "лекарство": ["препарат", "медикамент", "лекарственное средство"],
    "учебник": ["книга учебная", "учебное пособие", "методическое пособие"],
}

_REVERSE_SYNONYMS: dict[str, str] = {}
for _main_term, _syns in PROCUREMENT_SYNONYMS.items():
    for _s in _syns:
        _REVERSE_SYNONYMS[_s.lower()] = _main_term

_RE_NON_WORD = re.compile(r"[^\w\sа-яёА-ЯЁ0-9.-]")
_RE_MULTI_SPACE = re.compile(r"\s+")


class NLPService:
    def __init__(self):
        self._morph = pymorphy2.MorphAnalyzer()
        self._symspell = SymSpell(max_dictionary_edit_distance=get_settings().symspell_max_distance)
        self._initialized = False
        self._word_freqs: Counter | None = None

    def initialize(self):
        if self._initialized:
            return
        dict_path = Path(__file__).parent.parent / "data" / "frequency_dict_ru.txt"
        if dict_path.exists():
            self._symspell.load_dictionary(str(dict_path), term_index=0, count_index=1)
            logger.info(f"Loaded frequency dict from {dict_path}")
        else:
            logger.warning("No frequency dict found; will be built from corpus at load_data time")
            self._build_fallback_dict()
        self._initialized = True
        logger.info("NLP service initialized")

    def build_frequency_dict_from_corpus(self, texts: list[str]):
        """Build SymSpell dictionary from actual STE names. Called during data loading."""
        logger.info(f"Building SymSpell frequency dictionary from {len(texts)} texts...")
        word_freq: Counter = Counter()
        for text in texts:
            words = self.normalize_text(text).split()
            for w in words:
                if len(w) >= 2 and w not in _STOPWORDS_RU:
                    word_freq[w] += 1

        for word, freq in word_freq.items():
            self._symspell.create_dictionary_entry(word, freq)

        for main, syns in PROCUREMENT_SYNONYMS.items():
            self._symspell.create_dictionary_entry(main, max(word_freq.get(main, 0), 5000))
            for syn in syns:
                for sw in syn.split():
                    self._symspell.create_dictionary_entry(sw, max(word_freq.get(sw, 0), 1000))

        dict_path = Path(__file__).parent.parent / "data" / "frequency_dict_ru.txt"
        dict_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dict_path, "w", encoding="utf-8") as f:
            for word, freq in word_freq.most_common():
                if freq >= 2:
                    f.write(f"{word} {freq}\n")

        self._word_freqs = word_freq
        logger.info(f"SymSpell dictionary: {len(word_freq)} unique words, saved to {dict_path}")

    def _build_fallback_dict(self):
        for main, syns in PROCUREMENT_SYNONYMS.items():
            for word in main.split():
                self._symspell.create_dictionary_entry(word, 5000)
            for syn in syns:
                for word in syn.split():
                    self._symspell.create_dictionary_entry(word, 1000)

    def normalize_text(self, text: str) -> str:
        text = text.lower().strip()
        text = _RE_NON_WORD.sub(" ", text)
        return _RE_MULTI_SPACE.sub(" ", text).strip()

    def lemmatize(self, text: str) -> list[str]:
        words = self.normalize_text(text).split()
        lemmas = []
        for w in words:
            if w in _STOPWORDS_RU or len(w) < 2:
                continue
            parsed = self._morph.parse(w)
            lemmas.append(parsed[0].normal_form if parsed else w)
        return lemmas

    def correct_typos(self, text: str) -> tuple[str, bool]:
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
                word, Verbosity.CLOSEST,
                max_edit_distance=get_settings().symspell_max_distance,
            )
            if suggestions and suggestions[0].term != word:
                corrected_words.append(suggestions[0].term)
                was_corrected = True
            else:
                corrected_words.append(word)
        return " ".join(corrected_words), was_corrected

    def expand_synonyms(self, text: str) -> tuple[list[str], list[str]]:
        normalized = self.normalize_text(text)
        lemmas = self.lemmatize(text)
        applied = []
        expanded = list(lemmas)

        for lemma in lemmas:
            if lemma in PROCUREMENT_SYNONYMS:
                for syn in PROCUREMENT_SYNONYMS[lemma]:
                    expanded.extend(self.lemmatize(syn))
                applied.append(f"{lemma} -> {', '.join(PROCUREMENT_SYNONYMS[lemma][:3])}")

        if normalized in _REVERSE_SYNONYMS:
            main = _REVERSE_SYNONYMS[normalized]
            expanded.extend(self.lemmatize(main))
            applied.append(f"{normalized} -> {main}")

        return list(set(expanded)), applied

    def process_query(self, raw_query: str) -> dict:
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
