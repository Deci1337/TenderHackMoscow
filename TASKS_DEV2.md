# Dev 2 — ML, NLP & Data Tasks

**Зона ответственности**: `backend/app/services/**`, `backend/scripts/**`, `backend/app/data/**`
**Зона запрета**: не трогать `frontend/**`, `backend/app/api/**`, `backend/app/schemas.py`

---

## Приоритет 1 — Данные (разблокирует всё остальное)

### 1.1 Загрузка реальных данных
- Файл: `backend/scripts/load_data.py` — уже готов, запустить как только появятся файлы
- Команда: `make load-data` или `python -m scripts.load_data --ste-file data/ste.csv --contracts-file data/contracts.csv`
- После загрузки: запустить `build_ml_indexes` — он строит BM25 + embeddings + profiles
- Проверить логи: количество строк STE, контрактов, пользователей

### 1.2 Словарь частот для SymSpell из корпуса СТЕ
- Файл: `backend/app/services/nlp_service.py` — метод `build_frequency_dict_from_corpus` уже есть
- Вызвать из `load_data.py` после загрузки STE: `nlp.build_frequency_dict_from_corpus(ste_names)`
- Сохранится в `backend/app/data/frequency_dict_ru.txt`
- Результат: typo correction будет работать на реальной лексике товаров, а не на general-purpose словаре

### 1.3 Popularity scoring для СТЕ
- Файл: `backend/scripts/build_popularity.py` (новый)
- SQL: `SELECT ste_id, COUNT(*) as contract_count, SUM(cost) as total_volume FROM contracts GROUP BY ste_id`
- Сохранить в Redis: `HSET ste_popularity {ste_id} {score}` — нормализованный 0..1
- Читать в `ranking_service.py` из Redis при scoring
- Это даёт popularity_score feature для CatBoost без хранения в памяти

---

## Приоритет 2 — Качество NLP

### 2.1 Обработка омографов (контекстная)
- Файл: `backend/app/services/homograph_service.py` (новый)
- Словарь омографов: `{"ручка": {"медицина": ["ручка дверная", "ручка санитарная"], "образование": ["ручка шариковая", "ручка гелевая"], "default": ["ручка шариковая"]}}`
- Метод `resolve(word, user_industry) -> list[str]`: возвращает уточнённые синонимы по контексту
- Подключить в `nlp_service.py` в методе `expand_synonyms`: если слово в словаре омографов — использовать контекст
- `user_industry` передавать через `process_query(query, user_industry=None)`
- Покрыть минимум 15 омографов: ручка, кран, нос, замок, коса, лист, ключ, лук, брак, вал, мир, пара, печать, среда, язык

### 2.2 Расширение словаря синонимов
- Файл: `backend/app/services/nlp_service.py` — раздел `PROCUREMENT_SYNONYMS`
- Добавить минимум 30 новых пар специфичных для госзакупок:
  - медоборудование, расходники, стройматериалы, канцелярия, IT-оборудование
  - Пример: "мфу" → ["принтер", "сканер", "копир", "многофункциональное устройство"]
- Также добавить аббревиатуры: "пк" → "персональный компьютер", "нб" → "ноутбук"

### 2.3 Нормализация единиц измерения в запросах
- Файл: `backend/app/services/nlp_service.py` — добавить метод `normalize_units`
- "2 кг" → "кг", "100 шт" → "шт", "А4" → "а4" (lowercase)
- Вызывать в `normalize_text` перед лемматизацией

---

## Приоритет 3 — ML Ранжирование

### 3.1 Генерация псевдо-меток для CatBoost из истории контрактов
- Файл: `backend/scripts/train_ranker.py` (новый)
- Логика: если ste_id встречается в контрактах пользователя — релевантность 3, в той же категории — 1, иначе 0
- Формат: LETOR-style — `qid, relevance, features[11]`
- Сохранить датасет в `backend/app/data/train_pairs.csv`

### 3.2 Обучение CatBoost Ranker
- Файл: `backend/scripts/train_ranker.py` — продолжение
- `CatBoostRanker(loss_function='YetiRank', iterations=500, learning_rate=0.05, depth=6)`
- Train/val split 80/20, логировать NDCG@10 на валидации
- Сохранить модель в `backend/app/data/catboost_ranker.cbm`
- При следующем старте сервера — `ranking_service.py` автоматически подхватит файл

### 3.3 Профили пользователей из контрактов (холодный старт)
- Файл: `backend/app/services/personalization_service.py` — метод `build_profile_from_contracts` уже есть
- Убедиться что вызывается в `load_data.py` после загрузки контрактов
- Добавить метод `get_profile_summary(inn) -> dict` — краткая статистика для API: top-3 категории, кол-во контрактов, регион
- API `/users/{inn}/profile` уже читает из БД, но не из in-memory — сделать fallback

---

## Приоритет 4 — Качество поиска

### 4.1 Динамическое обновление весов BM25 (alpha)
- Файл: `backend/app/services/search_service.py` — метод `search()`
- Текущий `alpha = settings.bm25_weight` — статичный
- Сделать адаптивным: если запрос короткий (1 слово) → `alpha = 0.8` (больше BM25), длинный (3+ слов) → `alpha = 0.4` (больше семантики)
- Добавить `query_type: Literal["short", "medium", "long"]` в возвращаемый `query_data`

### 4.2 Кэширование embeddings в Redis
- Файл: `backend/app/services/embedding_service.py` — добавить Redis cache
- `embed_single(text)`: сначала проверить `GET emb:{hash(text)}` в Redis, если есть — десериализовать numpy array
- Если нет — посчитать, сохранить с TTL=3600
- Это критично для latency: повторные запросы будут мгновенными

### 4.3 Оффлайн-оценка качества поиска
- Файл: `backend/scripts/evaluate_search.py` (новый)
- Тестовые запросы: 20 пар `(query, expected_ste_ids)` — захардкодить вручную по данным
- Считать NDCG@10, MRR, Precision@5 для:
  - SQL-only (tsvector)
  - BM25-only
  - BM25 + semantic (hybrid)
  - hybrid + CatBoost
- Вывести таблицу сравнения — использовать в презентации как доказательство качества

---

## Файловая карта (итог)

```
backend/app/services/
  homograph_service.py          — новый (п. 2.1)
  nlp_service.py                — правки (п. 2.2, 2.3)
  search_service.py             — правки (п. 4.1)
  embedding_service.py          — правки (п. 4.2)
  personalization_service.py    — правки (п. 3.3)
  ranking_service.py            — правки (п. 3.3 fallback)

backend/scripts/
  build_popularity.py           — новый (п. 1.3)
  train_ranker.py               — новый (п. 3.1, 3.2)
  evaluate_search.py            — новый (п. 4.3)
```
