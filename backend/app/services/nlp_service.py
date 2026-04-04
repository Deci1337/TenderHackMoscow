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
    # --- Канцелярия ---
    "бумага": ["бумага офисная", "бумага для принтера", "бумага а4"],
    "ручка": ["ручка шариковая", "ручка гелевая", "ручка канцелярская"],
    "карандаш": ["карандаш чернографитный", "карандаш цветной", "карандаш механический"],
    "степлер": ["степлер канцелярский", "скобы для степлера", "сшиватель"],
    "скрепка": ["скрепка канцелярская", "зажим для бумаг", "биндер"],
    "папка": ["папка-регистратор", "папка-скоросшиватель", "папка на кольцах"],
    "конверт": ["конверт почтовый", "конверт с4", "конверт а4"],
    "скотч": ["клейкая лента", "лента канцелярская", "скотч упаковочный"],
    # --- IT оборудование ---
    "компьютер": ["пк", "персональный компьютер", "системный блок", "эвм"],
    "ноутбук": ["лэптоп", "портативный компьютер", "ноут", "нб"],
    "монитор": ["дисплей", "экран", "монитор жк"],
    "принтер": ["мфу", "печатающее устройство", "многофункциональное устройство"],
    "картридж": ["тонер-картридж", "картридж для принтера", "расходный материал"],
    "мфу": ["принтер", "сканер", "копир", "многофункциональное устройство"],
    "пк": ["персональный компьютер", "системный блок", "компьютер"],
    "нб": ["ноутбук", "лэптоп", "портативный компьютер"],
    "сервер": ["сервер вычислительный", "серверное оборудование", "блейд-сервер"],
    "коммутатор": ["свитч", "коммутатор сетевой", "switch"],
    "маршрутизатор": ["роутер", "маршрутизатор сетевой", "router"],
    "ибп": ["источник бесперебойного питания", "упс", "ups"],
    "флеш": ["флешка", "usb-накопитель", "флеш-драйв"],
    "кабель": ["провод", "шнур", "кабель сетевой", "патч-корд"],
    "сзи": ["средство защиты информации", "антивирус", "криптопро"],
    # --- Мебель ---
    "стол": ["стол офисный", "стол письменный", "рабочий стол"],
    "стул": ["кресло", "кресло офисное", "стул офисный"],
    "шкаф": ["шкаф для документов", "шкаф офисный", "тумба"],
    "тумба": ["тумба прикроватная", "тумба офисная", "подставка"],
    # --- Освещение ---
    "лампа": ["светильник", "лампа настольная", "осветительный прибор", "лампа светодиодная"],
    "светильник": ["люминесцентный светильник", "светильник потолочный", "лампа"],
    # --- Медицина ---
    "маска": ["маска медицинская", "маска защитная", "респиратор"],
    "перчатки": ["перчатки медицинские", "перчатки латексные", "перчатки нитриловые"],
    "шприц": ["шприц одноразовый", "шприц инъекционный", "инструмент медицинский"],
    "бинт": ["бинт марлевый", "бинт эластичный", "перевязочный материал"],
    "лекарство": ["препарат", "медикамент", "лекарственное средство"],
    "антисептик": ["дезинфицирующее средство", "антисептик для рук", "хлоргексидин"],
    "катетер": ["катетер мочевой", "катетер внутривенный", "зонд"],
    # --- Хозтовары / бытовая химия ---
    "салфетки": ["салфетки бумажные", "салфетки влажные"],
    "мыло": ["мыло жидкое", "мыло хозяйственное", "моющее средство"],
    "порошок": ["порошок стиральный", "моющее средство", "чистящее средство"],
    "дезсредство": ["дезинфицирующее средство", "антисептик", "средство дезинфекции"],
    # --- Стройматериалы ---
    "дверь": ["дверь межкомнатная", "дверь входная", "дверной блок"],
    "окно": ["окно пвх", "стеклопакет", "оконный блок"],
    "краска": ["краска водоэмульсионная", "лкм", "эмаль"],
    "труба": ["труба стальная", "труба пвх", "трубопровод"],
    "цемент": ["цемент м500", "смесь цементная", "вяжущее"],
    "кирпич": ["кирпич керамический", "кирпич силикатный", "блок стеновой"],
    "плитка": ["плитка керамическая", "кафель", "керамогранит"],
    "гвоздь": ["гвозди строительные", "метизы", "крепеж"],
    "саморез": ["саморез по дереву", "саморез по металлу", "метизы", "крепеж"],
    # --- Инженерия ---
    "насос": ["насос центробежный", "помпа", "насосная станция"],
    "клапан": ["вентиль", "задвижка", "запорная арматура"],
    "фильтр": ["фильтр воздушный", "фильтр масляный", "элемент фильтрующий"],
    "электродвигатель": ["электромотор", "двигатель асинхронный", "привод"],
    # --- Образование ---
    "учебник": ["книга учебная", "учебное пособие", "методическое пособие"],
    "тетрадь": ["тетрадь школьная", "тетрадь общая", "блокнот"],
    "доска": ["доска интерактивная", "доска маркерная", "доска школьная"],
    # --- Продовольствие ---
    "молоко": ["молоко пастеризованное", "молоко стерилизованное", "молочная продукция"],
    "хлеб": ["хлеб пшеничный", "хлебобулочные изделия", "батон"],
    "мясо": ["мясо говядина", "мясо свинина", "мясная продукция"],
    "масло": ["масло подсолнечное", "масло сливочное", "жиры растительные"],
    "сахар": ["сахар-песок", "сахар рафинад", "сахар-сырец"],
    "крупа": ["крупа гречневая", "крупа рисовая", "крупа манная", "бакалея"],
    # --- Транспорт / ГСМ ---
    "автомобиль": ["транспортное средство", "автотранспорт", "машина", "авто"],
    "топливо": ["бензин", "дизельное топливо", "гсм", "дт", "аи-92", "аи-95"],
    "шина": ["шина автомобильная", "покрышка", "резина", "колесо"],
    "масло моторное": ["масло трансмиссионное", "смазочный материал", "смазка"],
    "запчасть": ["запасная часть", "деталь автомобиля", "автозапчасть", "узел"],
    # --- Охрана / безопасность ---
    "охрана": ["охранная услуга", "охрана объекта", "физическая охрана", "чоп"],
    "видеонаблюдение": ["камера видеонаблюдения", "система видеонаблюдения", "скуд", "кмз"],
    "сигнализация": ["охранная сигнализация", "пожарная сигнализация", "аупс"],
    "огнетушитель": ["средство пожаротушения", "порошковый огнетушитель", "углекислотный огнетушитель"],
    # --- Связь / телекоммуникации ---
    "телефон": ["телефон ip", "телефонный аппарат", "телефон офисный", "вокс"],
    "сим": ["сим-карта", "sim", "мобильная связь", "тариф"],
    "интернет": ["услуга интернет", "доступ в интернет", "широкополосный доступ"],
    "по": ["программное обеспечение", "лицензия", "программа", "приложение"],
    "лицензия": ["лицензия по", "лицензионный ключ", "программное обеспечение"],
    # --- Коммунальные услуги ---
    "электроэнергия": ["электричество", "потребление электроэнергии", "квтч"],
    "теплоснабжение": ["тепловая энергия", "теплоноситель", "отопление"],
    "водоснабжение": ["водоотведение", "канализация", "вода питьевая"],
    # --- Спецодежда / СИЗ ---
    "спецодежда": ["форменная одежда", "костюм рабочий", "комбинезон", "сиз"],
    "каска": ["каска защитная", "шлем защитный", "средство защиты головы"],
    "перчатки рабочие": ["перчатки защитные", "рукавицы", "средства защиты рук"],
}

_REVERSE_SYNONYMS: dict[str, str] = {}
for _main_term, _syns in PROCUREMENT_SYNONYMS.items():
    for _s in _syns:
        _REVERSE_SYNONYMS[_s.lower()] = _main_term

_RE_NON_WORD = re.compile(r"[^\w\sа-яёА-ЯЁ0-9.-]")
_RE_MULTI_SPACE = re.compile(r"\s+")
_RE_UNIT = re.compile(
    r"(\d+)\s*(кг|г|мг|л|мл|шт|уп|рул|пач|м|мм|см|км|т)\b",
    re.IGNORECASE,
)


class NLPService:
    def __init__(self):
        self._morph = pymorphy2.MorphAnalyzer()
        self._symspell = SymSpell(max_dictionary_edit_distance=get_settings().SYMSPELL_MAX_DISTANCE)
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

    @staticmethod
    def normalize_units(text: str) -> str:
        """Strip numeric values before units: '2 кг' -> 'кг', '100 шт' -> 'шт'."""
        return _RE_UNIT.sub(r"\2", text)

    def normalize_text(self, text: str) -> str:
        text = text.lower().strip()
        text = self.normalize_units(text)
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
                max_edit_distance=get_settings().SYMSPELL_MAX_DISTANCE,
            )
            if suggestions and suggestions[0].term != word:
                corrected_words.append(suggestions[0].term)
                was_corrected = True
            else:
                corrected_words.append(word)
        return " ".join(corrected_words), was_corrected

    def expand_synonyms(
        self, text: str, user_industry: str | None = None,
    ) -> tuple[list[str], list[str]]:
        from app.services.homograph_service import resolve_homograph

        normalized = self.normalize_text(text)
        lemmas = self.lemmatize(text)
        applied = []
        expanded = list(lemmas)

        for lemma in lemmas:
            homograph_expansions = resolve_homograph(lemma, user_industry)
            if homograph_expansions:
                for he in homograph_expansions:
                    expanded.extend(self.lemmatize(he))
                applied.append(f"{lemma} ~> {', '.join(homograph_expansions[:3])} (context)")
                # When a context-specific homograph resolution exists, skip the generic
                # synonym expansion for this lemma to avoid polluting results with the
                # wrong interpretation (e.g. don't add pen synonyms for a builder).
                continue

            if lemma in PROCUREMENT_SYNONYMS:
                for syn in PROCUREMENT_SYNONYMS[lemma]:
                    expanded.extend(self.lemmatize(syn))
                applied.append(f"{lemma} -> {', '.join(PROCUREMENT_SYNONYMS[lemma][:3])}")

        if normalized in _REVERSE_SYNONYMS:
            main = _REVERSE_SYNONYMS[normalized]
            expanded.extend(self.lemmatize(main))
            applied.append(f"{normalized} -> {main}")

        return list(set(expanded)), applied

    def process_query(self, raw_query: str, user_industry: str | None = None) -> dict:
        if not self._initialized:
            self.initialize()
        corrected, was_corrected = self.correct_typos(raw_query)
        lemmas = self.lemmatize(corrected)
        expanded_terms, applied_synonyms = self.expand_synonyms(corrected, user_industry)
        n = len(lemmas)
        query_type = "short" if n <= 1 else ("long" if n > 3 else "medium")
        return {
            "original": raw_query,
            "corrected": corrected,
            "was_corrected": was_corrected,
            "lemmas": lemmas,
            "expanded_terms": expanded_terms,
            "applied_synonyms": applied_synonyms,
            "query_type": query_type,
        }


@lru_cache
def get_nlp_service() -> NLPService:
    svc = NLPService()
    svc.initialize()
    return svc
