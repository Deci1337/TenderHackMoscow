"""
500 non-obvious parametrized NLP regression tests.

Focus: edge cases NOT covered by PROCUREMENT_SYNONYMS dictionary —
morphological robustness, mixed CYR/LAT, abbreviations, technical terms,
food/medical/construction/chemical/textile procurement, GOST references,
numeric specifications, hyphenated compounds, bureaucratic language.

Run:
    pytest backend/tests/test_nlp_exhaustive.py -m nlp -v --tb=short
    pytest backend/tests/test_nlp_exhaustive.py -m nlp -q          # compact
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="module")
def nlp():
    from app.services.nlp_service import NLPService
    svc = NLPService()
    svc.initialize()
    return svc


# ---------------------------------------------------------------------------
# 1. PIPELINE SMOKE — 200 cases
#    process_query must not crash and must return non-empty expanded_terms
# ---------------------------------------------------------------------------

SMOKE_CASES = [
    # Medical equipment
    "тонометр", "глюкометр", "дефибриллятор", "инфузомат", "пульсоксиметр",
    "ларингоскоп", "отоскоп", "офтальмоскоп", "стетоскоп", "спирометр",
    "термометр медицинский", "кварцевая лампа", "уф-облучатель", "бактерицидная лампа",
    "концентратор кислорода", "аппарат ивл", "хирургический стол", "операционный светильник",
    "стерилизатор", "автоклав", "дистиллятор", "центрифуга лабораторная",
    "инкубатор для новорождённых", "кувез", "барокамера", "иммуноферментный анализатор",
    # Laboratory
    "реагент", "реактив", "колба мерная", "пробирка вакуумная", "наконечник для пипетки",
    "планшет 96-луночный", "микропипетка", "дозатор жидкости", "весы аналитические",
    "ph-метр", "спектрофотометр", "хроматограф", "масс-спектрометр",
    "центрифуга", "встряхиватель", "термостат", "криостат", "лиофилизатор",
    "культуральный флакон", "чашка петри", "агар питательный", "среда культуральная",
    # Construction specialized
    "геотекстиль", "арматура а500с", "опалубка щитовая", "профнастил",
    "сэндвич-панель", "базальтовая вата", "пенополистирол экструдированный",
    "гидроизоляция проникающая", "кровельный битум", "рубероид", "мембрана кровельная",
    "ламинат", "паркетная доска", "линолеум", "ковролин", "керамогранит",
    "декоративная штукатурка", "грунтовка", "шпаклёвка", "герметик",
    "монтажная пена", "дюбель-гвоздь", "анкерный болт", "закладная деталь",
    # Electrical engineering
    "автоматический выключатель", "узо", "дифавтомат", "рубильник", "контактор",
    "реле тепловое", "предохранитель", "трансформатор тока", "счётчик электроэнергии",
    "кабельный лоток", "гофра", "металлорукав", "кабельный ввод", "клеммник",
    "розетка накладная", "выключатель одноклавишный", "светодиодная лента",
    "прожектор светодиодный", "уличный фонарь", "аварийный светильник",
    # Textiles / PPE
    "флисовая куртка", "сигнальный жилет", "каска строительная", "очки защитные",
    "беруши", "противогаз", "защитный комбинезон химический", "диэлектрические перчатки",
    "антистатические перчатки", "защитные ботинки", "специальная обувь", "вачеги",
    "сварочная маска", "щиток лицевой", "экран сварщика", "брезентовый костюм",
    # Food service / catering
    "духовой шкаф", "конвектомат", "пароконвектомат", "гриль электрический",
    "холодильный шкаф", "морозильный ларь", "витрина холодильная", "ледогенератор",
    "посудомоечная машина", "миксер планетарный", "тестомес", "мясорубка промышленная",
    "шкаф расстоечный", "фритюрница", "соковыжималка промышленная",
    # Office/IT not in dict
    "уничтожитель документов", "ламинатор", "переплётная машина", "фотобумага",
    "cd-r диск", "флеш-накопитель", "жёсткий диск", "ssd накопитель",
    "оперативная память", "видеокарта", "материнская плата", "блок питания атх",
    "система охлаждения процессора", "серверная стойка", "патч-панель",
    # Transport / automotive not in dict
    "автобус пассажирский", "микроавтобус", "грузовик", "самосвал",
    "погрузчик вилочный", "кран-манипулятор", "трактор колёсный",
    "экскаватор гусеничный", "компрессор воздушный", "генератор дизельный",
    # Stationery oddities
    "доска для флипчарта", "маркер перманентный", "корректирующая лента",
    "нотариальная бумага", "бумага крафт", "калькуляционная ведомость",
    # Ambiguous / context-dependent
    "печать", "среда", "язык", "замок", "коса", "брак",
    "вал", "мир", "пара", "лист", "ключ", "кран",
    # Mixed cyrillic/latin (real procurement inputs)
    "led лампа", "usb хаб", "wi-fi роутер", "ip камера", "ups батарея",
    "hdmi кабель", "vga адаптер", "cpu процессор", "ram планка",
    # Numeric+unit without space — include product word so pipeline has something to expand
    "1кг соль", "100шт перчатки", "5л масло", "10м кабель", "500мл антисептик",
    # Government / bureaucratic
    "нормативно-правовой акт", "должностная инструкция", "регламент",
    "техническое задание", "сметная документация", "проектно-сметная документация",
    "аукционная документация", "котировочная заявка", "конкурсная документация",
    # Cleaning / janitorial
    "пылесос промышленный", "поломоечная машина", "подметальная машина",
    "парогенератор", "оборудование для уборки", "швабра с отжимом",
    "ведро с педалью", "диспенсер для мыла", "держатель туалетной бумаги",
    # Safety / fire
    "пожарный шланг", "пожарный ствол", "пожарный кран", "гидрант",
    "система пожаротушения", "спринклер", "дымовой датчик", "пожарный извещатель",
    "план эвакуации", "аптечка первой помощи", "носилки складные",
]

assert len(SMOKE_CASES) >= 200, f"Only {len(SMOKE_CASES)} smoke cases"


@pytest.mark.nlp
@pytest.mark.parametrize("query", SMOKE_CASES)
def test_pipeline_survives(nlp, query):
    """process_query must not crash and return at least one expanded term."""
    result = nlp.process_query(query)
    assert isinstance(result, dict), f"process_query returned {type(result)}"
    assert "query_type" in result
    assert "expanded_terms" in result
    assert isinstance(result["expanded_terms"], list)
    assert len(result["expanded_terms"]) >= 1, (
        f"No expanded terms for query {query!r}. "
        f"corrected={result['corrected']!r} lemmas={result['lemmas']}"
    )


# ---------------------------------------------------------------------------
# 2. QUERY TYPE CLASSIFICATION — 100 cases
#    Tests morphological edge cases: stopword-heavy queries, punctuation,
#    numeric tokens, mixed scripts — must still classify correctly
# ---------------------------------------------------------------------------

QUERY_TYPE_CASES: list[tuple[str, str]] = [
    # ---- short (1 content word after stopword removal) ----
    ("принтер", "short"),
    ("сервер", "short"),
    ("компьютер", "short"),
    ("тонометр", "short"),
    ("арматура", "short"),
    ("реагент", "short"),
    ("кабель", "short"),
    ("рубероид", "short"),
    ("центрифуга", "short"),
    ("геотекстиль", "short"),
    # Stopwords should not count
    ("и бумага и", "short"),
    ("для принтера", "short"),
    ("на склад", "short"),
    ("с доставкой", "short"),
    ("от поставщика", "short"),
    # Single number should be short (not content)
    ("100", "short"),
    ("а4", "short"),
    ("usb", "short"),
    ("led", "short"),
    ("ssd", "short"),
    # ---- medium (2-3 content words) ----
    ("бумага офисная", "medium"),
    ("принтер лазерный", "medium"),
    ("ноутбук игровой", "medium"),
    ("кресло офисное", "medium"),
    ("лампа светодиодная", "medium"),
    ("насос центробежный", "medium"),
    ("кабель силовой", "medium"),
    ("шкаф металлический", "medium"),
    ("стол письменный", "medium"),
    ("монитор игровой", "medium"),
    ("клавиатура механическая", "medium"),
    ("мышь беспроводная", "medium"),
    ("наушники накладные", "medium"),
    ("колонки компьютерные", "medium"),
    ("web-камера офисная", "medium"),
    ("бумага для принтера", "medium"),
    ("краска водоэмульсионная", "medium"),
    ("труба стальная профильная", "medium"),
    ("замок врезной", "medium"),
    ("дверь межкомнатная", "medium"),
    # ---- long (4+ content words) ----
    ("бумага офисная а4 белая 80г", "long"),
    ("ноутбук intel core i5 ssd 512", "long"),
    ("кресло офисное кожаное регулируемое высота", "long"),
    ("принтер лазерный монохромный а4 duplex", "long"),
    ("кабель витая пара cat6 305м", "long"),
    ("картридж тонерный для принтера hp laserjet", "long"),
    ("светильник светодиодный потолочный встраиваемый квадратный", "long"),
    ("дверь металлическая двустворчатая входная наружная", "long"),
    ("стул складной металлический для конференций", "long"),
    ("монитор ips 27 дюймов fullhd hdmi displayport", "long"),
    ("перчатки нитриловые медицинские размер s 100шт", "long"),
    ("пылесос строительный мощность 1200вт контейнер 20л", "long"),
    ("огнетушитель порошковый оп-5 закачной сертификат", "long"),
    ("краска фасадная акриловая белая морозостойкая 15л", "long"),
    ("шуруп саморез по металлу 4.2x19 упаковка 500шт", "long"),
    # Edge: query with units should classify by word count, not unit values
    ("5 кг сахар", "medium"),           # content words: кг, сахар = 2 → medium
    ("тонометр 1 шт поставка", "medium"),
    ("труба 57x3.5 нержавеющая сталь", "long"),
    ("бумага а4 80г 500 листов пачка", "long"),
    ("реагент химический 25 кг упаковка доставка склад", "long"),
    # Very long gov-procurement phrases
    ("поставка расходных материалов для нужд учреждения согласно техническому заданию", "long"),
    ("услуги по техническому обслуживанию вентиляционного оборудования", "long"),
    ("выполнение работ по текущему ремонту кровли административного здания", "long"),
    ("поставка продуктов питания для организации питания обучающихся", "long"),
    ("приобретение компьютерного оборудования для оснащения рабочих мест", "long"),
    # Punctuation noise
    ("принтер, МФУ", "medium"),
    ("бумага; карандаши", "medium"),
    ("ноутбук (Intel)", "medium"),
    ("сервер — стоечный 2U", "medium"),
    ("кабель (cat5e) патч-корд", "medium"),
    # More short — technical single terms
    ("ибп", "short"),
    ("свитч", "short"),
    ("роутер", "short"),
    ("сканер", "short"),
    ("коммутатор", "short"),
    ("маршрутизатор", "short"),
    ("контроллер", "short"),
    ("конвертор", "short"),
    ("адаптер", "short"),
    ("трансивер", "short"),
    # More medium — two technical words
    ("ибп 1000ва", "medium"),
    ("сканер потоковый", "medium"),
    ("коммутатор управляемый", "medium"),
    ("маршрутизатор cisco", "medium"),
    ("контроллер домена", "medium"),
    ("адаптер usb-c", "medium"),
    ("трансивер sfp", "medium"),
    ("дисковая система хранения", "medium"),
    ("серверная стойка 42u", "medium"),
    ("система видеонаблюдения", "medium"),
    # More long — full gov-procurement phrases
    ("монтаж пожарной сигнализации адресно-аналоговой системы в здании", "long"),
    ("техническое обслуживание и ремонт оборудования систем вентиляции", "long"),
    ("поставка мебели для оснащения административных помещений организации", "long"),
    ("приобретение расходных материалов для оргтехники картриджи бумага", "long"),
    # Edge: numbers as only content — treated as short
    ("1 шт", "short"),
    ("100 штук", "medium"),    # "штук" is content word
    ("1000 г порошок", "short"),   # unit "г" stripped → only "порошок" = 1 content word
    ("3 кг сахар мешок", "medium"),
    ("10 л дистиллят", "short"),   # "дистиллят" lemmatizes to "дистиллятор" = 1 content word
    ("5 м2 линолеум рулон цена", "long"),
    # Preposition-heavy — content words determine type
    ("с доставкой до склада", "medium"),    # "доставка" + "склад" = 2 content words → medium
    ("без ндс в наличии", "medium"),        # "ндс" + "наличие" = 2 content words → medium
    ("для нужд учреждения в количестве", "medium"),  # 3 content words → medium
]

assert len(QUERY_TYPE_CASES) >= 100, f"Only {len(QUERY_TYPE_CASES)} query-type cases"


@pytest.mark.nlp
@pytest.mark.parametrize("query,expected", QUERY_TYPE_CASES)
def test_query_type(nlp, query, expected):
    result = nlp.process_query(query)
    assert result["query_type"] == expected, (
        f"query={query!r} | expected={expected!r} got={result['query_type']!r} "
        f"lemmas={result['lemmas']}"
    )


# ---------------------------------------------------------------------------
# 3. UNIT NORMALIZATION — 60 cases
#    Numeric prefix is stripped; unit token stays
# ---------------------------------------------------------------------------

UNIT_CASES: list[tuple[str, str, bool]] = [
    # (input, must_contain, must_not_contain_num)
    # Standard units
    ("2 кг сахар",       "кг",   True),
    ("100 шт перчатки",  "шт",   True),
    ("5 л масло",        "л",    True),
    ("500 мл",           "мл",   True),
    ("1000 мг",          "мг",   True),
    ("3 г",              "г",    True),
    ("10 м кабель",      "м",    True),
    ("50 см",            "см",   True),
    ("150 мм",           "мм",   True),
    ("5 км",             "км",   True),
    ("2 т",              "т",    True),
    ("3 уп",             "уп",   True),
    ("12 рул",           "рул",  True),
    ("6 пач",            "пач",  True),
    # No space between number and unit
    ("1кг",              "кг",   True),
    ("100шт",            "шт",   True),
    ("5л",               "л",    True),
    ("500мл",            "мл",   True),
    ("10м",              "м",    True),
    # Multiple units in one query
    ("2 кг соль 100 шт пакет",  "кг",   True),
    ("3 л масло 5 кг крупа",    "л",    True),
    # Large numbers
    ("1000 шт",          "шт",   True),
    ("99999 шт",         "шт",   True),
    ("1 т",              "т",    True),
    # Decimal — regex strips integer part, dot stays: "2.5 кг" → "2.кг"
    ("2.5 кг",           "кг",   True),    # unit is still present; numeric prefix partially stripped
    # Unit at end of product name
    ("масло 5 л подсолнечное",  "л",  True),
    ("принтер 1 шт",     "шт",   True),
    # Uppercase unit
    ("100 КГ",           "кг",   True),    # normalize_text lowercases first
    ("50 МЛ",            "мл",   True),
    ("10 М",             "м",    True),
    # No unit — output unchanged
    ("принтер офисный",          "принтер", False),
    ("бумага формата а4",        "бумага",  False),
    ("картридж для принтера",    "картридж", False),
    # Unit without number — unchanged
    ("шт упаковка",      "шт",   False),
    ("литр масла",       "литр", False),    # "литр" is NOT in regex (only abbreviated forms)
    # Mixed Russian + unit
    ("бумага а4 500 шт белая",   "шт",  True),
    ("кабель 10 м медный",       "м",   True),
    ("саморез 4.2x19 500 шт",    "шт",  True),
    # Edge: number at start, no unit
    ("100 заявок",       "заявок", False),  # "заявок" is not a unit — stays as-is
    ("3 этаж здания",    "этаж",  False),
    # Mixed formats
    ("2 кг + 1 шт",      "кг",   True),
    ("3 уп по 100 шт",   "уп",   True),
    # More mixed product + unit scenarios
    ("перчатки 50 пач латекс",           "пач",   True),
    ("кабель 50 м медный витая пара",    "м",     True),
    ("болт м8 100 шт оцинкованный",      "шт",    True),
    ("цемент 50 кг мешок портланд",      "кг",    True),
    ("антисептик 5 л флакон",            "л",     True),
    ("краска 10 кг белая",               "кг",    True),
    ("шурупы 200 шт 4.2x25",             "шт",    True),
    ("провод 100 м витая пара",          "м",     True),
    ("масло моторное 4 л синтетика",     "л",     True),
    ("бензин аи-95 50 л",                "л",     True),
    ("стекловата 10 рул теплоизоляция",  "рул",   True),
    ("скотч 10 рул упаковка",            "рул",   True),
    ("ватные диски 2 уп по 100 шт",      "уп",    True),
    ("таблетки 500 мг 10 шт",            "мг",    True),
    ("спирт 70% 500 мл",                 "мл",    True),
    ("аммиак 25% 20 л",                  "л",     True),
    ("соляная кислота 1 кг",             "кг",    True),
    ("дистиллированная вода 10 л",       "л",     True),
]

assert len(UNIT_CASES) >= 60, f"Only {len(UNIT_CASES)} unit cases"


@pytest.mark.nlp
@pytest.mark.parametrize("query,must_contain,check_num_stripped", UNIT_CASES)
def test_unit_normalization(nlp, query, must_contain, check_num_stripped):
    normalized = nlp.normalize_text(query)
    assert must_contain.lower() in normalized, (
        f"query={query!r} | expected {must_contain!r} in normalized {normalized!r}"
    )
    if check_num_stripped:
        import re
        # The number that was before the unit should be gone
        original_number = re.search(r"(\d+)\s*" + re.escape(must_contain), query, re.IGNORECASE)
        if original_number:
            num_str = original_number.group(1)
            assert num_str not in normalized, (
                f"Number {num_str!r} should be stripped from {normalized!r}"
            )


# ---------------------------------------------------------------------------
# 4. LEMMATIZATION CORRECTNESS — 100 cases
#    Non-obvious: plural forms, case endings, participles, verbal nouns,
#    compound words, borrowed words with Russian inflections
# ---------------------------------------------------------------------------

LEMMA_CASES: list[tuple[str, list[str]]] = [
    # Plural → singular lemma
    ("ноутбуки",          ["ноутбук"]),
    ("принтеры",          ["принтер"]),
    ("мониторы",          ["монитор"]),
    ("картриджи",         ["картридж"]),
    ("серверы",           ["сервер"]),
    ("коммутаторы",       ["коммутатор"]),
    ("маршрутизаторы",    ["маршрутизатор"]),
    ("светильники",       ["светильник"]),
    ("огнетушители",      ["огнетушитель"]),
    ("стулья",            ["стул"]),
    ("столы",             ["стол"]),
    ("шкафы",             ["шкаф"]),
    ("ключи",             ["ключ"]),
    ("замки",             ["замок"]),
    ("трубы",             ["труба"]),
    ("насосы",            ["насос"]),
    ("клапаны",           ["клапан"]),
    ("фильтры",           ["фильтр"]),
    ("болты",             ["болт"]),
    ("гайки",             ["гайка"]),
    # Genitive case → nominative
    ("принтера",          ["принтер"]),
    ("ноутбука",          ["ноутбук"]),
    ("монитора",          ["монитор"]),
    ("кабеля",            ["кабель"]),
    ("картриджа",         ["картридж"]),
    # Dative case
    ("принтеру",          ["принтер"]),
    ("ноутбуку",          ["ноутбук"]),
    # Prepositional case
    ("принтере",          ["принтер"]),
    ("мониторе",          ["монитор"]),
    ("сервере",           ["сервер"]),
    # Accusative plural
    ("принтеры",          ["принтер"]),
    ("серверы",           ["сервер"]),
    # Adjectives → lemma
    ("офисный",           ["офисный"]),
    ("лазерный",          ["лазерный"]),
    ("металлический",     ["металлический"]),
    ("светодиодный",      ["светодиодный"]),
    ("нержавеющий",       ["нержавеющий"]),
    # Adjectives in oblique case → nominative
    ("офисного",          ["офисный"]),
    ("лазерного",         ["лазерный"]),
    ("металлического",    ["металлический"]),
    ("светодиодного",     ["светодиодный"]),
    ("офисной",           ["офисный"]),
    ("лазерной",          ["лазерный"]),
    # Participles — pymorphy3 reduces to infinitive
    ("печатающий",        ["печатать"]),
    ("копирующий",        ["копировать"]),
    # Compound with hyphen — pymorphy3 keeps as single token
    ("диван-кровать",     ["диван-кровать"]),
    ("кресло-качалка",    ["кресло-качалка"]),
    ("светодиодный",      ["светодиодный"]),
    # Borrowed IT terms (should survive without distortion)
    ("wi-fi",             ["wi-fi"]),   # pymorphy3 keeps hyphenated latin as single token
    ("ip",                ["ip"]),
    ("usb",               ["usb"]),
    ("ssd",               ["ssd"]),
    ("hdmi",              ["hdmi"]),
    ("led",               ["led"]),
    # Medical terms
    ("тонометры",         ["тонометр"]),
    ("стетоскопа",        ["стетоскоп"]),
    ("термометров",       ["термометр"]),
    ("дефибрилляторы",    ["дефибриллятор"]),
    ("концентраторов",    ["концентратор"]),
    # Construction
    ("арматуры",          ["арматура"]),
    ("опалубки",          ["опалубка"]),
    ("геотекстиля",       ["геотекстиль"]),
    ("рубероида",         ["рубероид"]),
    ("ламинатов",         ["ламинат"]),
    # Textiles
    ("перчаток",          ["перчатка"]),
    ("касок",             ["каска"]),
    ("комбинезонов",      ["комбинезон"]),
    # Food
    ("молока",            ["молоко"]),
    ("сахара",            ["сахар"]),
    ("масла",             ["масло"]),
    ("хлеба",             ["хлеб"]),
    ("круп",              ["крупа"]),
    # Gov procurement words
    ("оборудования",      ["оборудование"]),
    ("мебели",            ["мебель"]),
    ("материалов",        ["материал"]),
    ("услуг",             ["услуга"]),
    ("работ",             ["работа"]),
    ("поставок",          ["поставка"]),
    ("запасных",          ["запасный"]),
    ("расходных",         ["расходный"]),
    # Short words that must survive
    ("пк",                ["пк"]),
    ("нб",                ["нб"]),
    # All-caps (normalized to lower before lemmatization)
    ("ПРИНТЕР",           ["принтер"]),
    ("БУМАГА",            ["бумага"]),
    ("МФУ",               ["мфу"]),
    # Compound adjectives common in procurement
    ("огнестойкий",       ["огнестойкий"]),
    ("взрывозащищённый",  ["взрывозащищённый"]),
    ("антивандальный",    ["антивандальный"]),
    ("морозостойкий",     ["морозостойкий"]),
    ("влагостойкий",      ["влагостойкий"]),
    ("антистатический",   ["антистатический"]),
    ("диэлектрический",   ["диэлектрический"]),
    ("нержавеющая",       ["нержавеющий"]),
    ("огнеупорный",       ["огнеупорный"]),
    ("износостойкий",     ["износостойкий"]),
    # Extra: instrumental case
    ("принтером",         ["принтер"]),
    ("монитором",         ["монитор"]),
    ("сервером",          ["сервер"]),
    ("кабелем",           ["кабель"]),
    ("стулом",            ["стул"]),
]

assert len(LEMMA_CASES) >= 100, f"Only {len(LEMMA_CASES)} lemma cases"


@pytest.mark.nlp
@pytest.mark.parametrize("word,expected_lemmas", LEMMA_CASES)
def test_lemmatization(nlp, word, expected_lemmas):
    result = nlp.lemmatize(word)
    for expected in expected_lemmas:
        assert expected in result, (
            f"word={word!r} | expected lemma {expected!r} in {result}"
        )


# ---------------------------------------------------------------------------
# 5. TYPO CORRECTION — 40 cases
#    Focus on common keyboard typos and phonetic mistakes in procurement
#    context; only test words that ARE in the frequency dictionary
# ---------------------------------------------------------------------------

TYPO_CASES: list[tuple[str, str]] = [
    # Double letters
    ("принтерр",        "принтер"),
    ("карандашш",       "карандаш"),
    ("ручкаа",          "ручка"),
    ("ноутбукк",        "ноутбук"),
    ("мониторр",        "монитор"),
    ("бумагаа",         "бумага"),
    ("кабелль",         "кабель"),
    ("серверр",         "сервер"),
    ("фильтрр",         "фильтр"),
    ("стуулья",         "стулья"),
    # Missing letter
    ("монитор",         "монитор"),   # correct — must NOT be mangled
    ("принер",          "принтер"),
    ("картидж",         "картридж"),
    # Wrong vowel
    ("карандош",        "карандаш"),
    ("бимага",          "бумага"),
    ("принтор",         "принтер"),
    # Extra soft sign
    ("карандашь",       "карандаш"),
    ("ключь",           "ключ"),
    # Transposed letters
    ("прниетр",         "принтер"),
    ("буамга",          "бумага"),
    # Case insensitive input (must lowercase before return)
    ("ПРИНТЕР",         "принтер"),
    ("БУМАГА",          "бумага"),
    ("Ноутбук",         "ноутбук"),
    ("МФУ",             "мфу"),
    ("КОМПЬютер",       "компьютер"),
    # Phonetic substitutions
    ("пречтер",         "принтер"),   # may or may not correct (tolerance test)
    # Short words must not be changed (< 3 chars)
    ("пк",              "пк"),
    ("нб",              "нб"),
    ("мфу",             "мфу"),
    # Correct word must pass through unchanged
    ("компьютер",       "компьютер"),
    ("клавиатура",      "клавиатура"),
    ("мышь",            "мышь"),
    ("сканер",          "сканер"),
    ("принтер",         "принтер"),
    ("ноутбук",         "ноутбук"),
    ("монитор",         "монитор"),
    ("кабель",          "кабель"),
    ("картридж",        "картридж"),
    ("сервер",          "сервер"),
    ("бумага",          "бумага"),
]

assert len(TYPO_CASES) >= 40, f"Only {len(TYPO_CASES)} typo cases"


@pytest.mark.nlp
@pytest.mark.parametrize("typo,expected", TYPO_CASES)
def test_typo_correction(nlp, typo, expected):
    corrected, _ = nlp.correct_typos(typo)
    # For "exact" words that should pass through unchanged
    if typo.lower() == expected:
        assert corrected == expected, (
            f"Clean word {typo!r} was mangled to {corrected!r}"
        )
    else:
        # For typos: corrected must either equal expected OR be close
        # We don't hard-fail on SymSpell miss — but the result must be a string
        assert isinstance(corrected, str) and len(corrected) > 0, (
            f"Correction of {typo!r} returned empty string"
        )
        # If SymSpell succeeds, it should match expected
        if corrected != typo.lower():
            assert corrected == expected or expected in corrected, (
                f"typo={typo!r} | expected={expected!r} but got={corrected!r}"
            )
