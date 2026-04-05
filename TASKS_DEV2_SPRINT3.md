# Dev 2 — Sprint 3: Backend, ML & Data

**Зона ответственности**: `backend/app/services/**`, `backend/app/api/**`, `backend/app/models.py`, `backend/app/schemas.py`, `backend/scripts/**`
**Зона запрета**: не трогать `frontend/**`
**Стек**: FastAPI, SQLAlchemy async, PostgreSQL, Redis, Python 3.11+

**Что даёт Dev 1**: UI для интересов, стрелки позиций, панель объяснений — всё это консюмит твои API.

**Контракт API** (Dev 1 ждёт эти эндпоинты; реализовать в первую очередь):
- `GET /users/{inn}/interests` → `UserInterestSummary`
- `GET /users/{inn}/categories` → `list[str]`
- `POST /search` — в каждом `STEResult` добавить поле `rank_delta: int | None`

---

## Задача 0 — Срочно: удалить монетизацию (продвижение + добавление товаров)

### 0.1 Удалить роутер products из main.py

**Файл**: `backend/app/main.py`

Найти строку:
```python
from app.api import products
app.include_router(products.router)
```
Удалить обе строки. Файл `backend/app/api/products.py` можно оставить, но не регистрировать.

### 0.2 Удалить analytics-эндпоинты продвижения

**Файл**: `backend/app/api/analytics.py`

Убрать эндпоинты связанные с `promotion`:
- `GET /analytics/products/{id}` — если возвращает `promotion_boost`, убрать поля из ответа
- Оставить только `GET /analytics/hot` если он есть и не связан с продвижением

### 0.3 Очистить модель STE от promotion-полей в бизнес-логике

**Файл**: `backend/app/api/search.py`

Найти все места где используется `ste.promotion_boost` или `ste.promoted_until` при формировании `STEResult`:
- Установить `is_promoted = False` и `promotion_boost = 0.0` принудительно
- Не удалять колонки из БД (это отдельная миграция, риск конфликтов) — просто не использовать

**Файл**: `backend/app/services/ranking_service.py`

Найти код вида:
```python
if ste.promoted_until and ste.promoted_until > now:
    score += ste.promotion_boost * PROMOTION_WEIGHT
```
Закомментировать или удалить этот блок. Промо-буст не должен влиять на ранжирование.

### 0.4 Проверка схем на конфликты

**Файл**: `backend/app/schemas.py`

Удалить / закомментировать схемы:
```python
# class CreateProductRequest ...
# class CreateProductResponse ...
# class PromoteRequest ...
# class PromoteResponse ...
# class MyProductResponse ...
# class ProductAnalyticsResponse ...  (если содержит promotion)
```

`STEResult` — поля `is_promoted` и `promotion_boost` оставить (не удалять из модели) но принудительно выставлять `False` / `0.0`.

---

## Задача 1 — Новый API: сводка интересов пользователя

Это главный эндпоинт для панели Dev 1.

**Файл**: `backend/app/api/users.py`

### 1.1 Схемы (backend/app/schemas.py)

```python
class CategoryInterest(BaseModel):
    category: str
    click_count: int           # кликов в текущей сессии (0 если нет)
    contract_count: int        # исторических контрактов
    weight: float              # итоговый вес 0..1
    trend: str                 # "rising" | "stable" | "fading"
    last_interaction_days: int # дней с последнего взаимодействия (0 = сегодня)

class UserInterestSummary(BaseModel):
    inn: str
    label: str | None
    top_categories: list[CategoryInterest]
    session_clicks_total: int
    recent_query: str | None
    active_interests: list[str]   # категории с weight > 0.3
    fading_interests: list[str]   # не взаимодействовали > 14 дней
    last_updated: str             # ISO datetime
```

### 1.2 Логика формирования интересов

**Файл**: `backend/app/services/personalization_service.py`

Добавить метод `get_interest_summary(inn: str, db) -> UserInterestSummary`:

```python
async def get_interest_summary(self, inn: str, db) -> dict:
    """
    Строит сводку интересов пользователя из:
    1. История контрактов (из БД) — базовый вес
    2. Текущая сессия (из in-memory _profiles) — сессионный вес
    3. Давность взаимодействия (затухание)
    """
    ctx = self._profiles.get(inn)

    # Загрузить статистику контрактов из БД
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT s.category, COUNT(*) as cnt
        FROM contracts c
        JOIN ste s ON c.ste_id = s.id
        WHERE c.customer_inn = :inn AND s.category IS NOT NULL
        GROUP BY s.category
        ORDER BY cnt DESC
        LIMIT 10
    """), {"inn": inn})
    contract_counts = {row.category: row.cnt for row in result.fetchall()}

    # Загрузить последнюю дату взаимодействия по категориям
    result2 = await db.execute(text("""
        SELECT s.category, MAX(e.created_at) as last_at
        FROM events e
        JOIN ste s ON e.ste_id = s.id
        WHERE e.user_inn = :inn AND s.category IS NOT NULL
        GROUP BY s.category
    """), {"inn": inn})
    last_interactions = {row.category: row.last_at for row in result2.fetchall()}

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # Объединяем контракты + сессионные веса
    all_cats = set(contract_counts.keys())
    if ctx:
        all_cats |= set(ctx.category_weights.keys())

    categories = []
    for cat in all_cats:
        contract_cnt = contract_counts.get(cat, 0)
        session_weight = ctx.category_weights.get(cat, 0.0) if ctx else 0.0

        # Давность (затухание)
        last_dt = last_interactions.get(cat)
        if last_dt:
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            days_ago = (now - last_dt).days
        else:
            days_ago = 999

        # Итоговый вес: контракты дают базу, сессия добавляет актуальность
        base = min(contract_cnt / 50.0, 1.0)  # нормируем по 50 контрактов
        decay = max(0.0, 1.0 - days_ago / 30.0)  # за 30 дней весь decay
        weight = min(1.0, base * 0.6 + session_weight * 0.4) * (0.3 + 0.7 * decay)

        # Тренд
        if session_weight > 0.3 and days_ago < 1:
            trend = "rising"
        elif days_ago > 14:
            trend = "fading"
        else:
            trend = "stable"

        categories.append({
            "category": cat,
            "click_count": 0,  # сессионные клики — из session_index
            "contract_count": contract_cnt,
            "weight": round(weight, 3),
            "trend": trend,
            "last_interaction_days": days_ago if days_ago < 999 else -1,
        })

    categories.sort(key=lambda x: x["weight"], reverse=True)

    active = [c["category"] for c in categories if c["weight"] > 0.3]
    fading = [c["category"] for c in categories if c["trend"] == "fading"]

    # Последний запрос из Redis
    recent_query = None
    try:
        import redis.asyncio as aioredis
        from app.config import get_settings
        r = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
        recent_query = await r.lindex(f"user_queries:{inn}", 0)
        await r.aclose()
    except Exception:
        pass

    profile = await db.get(__import__("app.models", fromlist=["UserProfile"]).UserProfile, inn)

    return {
        "inn": inn,
        "label": profile.name if profile else None,
        "top_categories": categories[:8],
        "session_clicks_total": ctx.interaction_count if ctx else 0,
        "recent_query": recent_query,
        "active_interests": active[:3],
        "fading_interests": fading[:2],
        "last_updated": now.isoformat(),
    }
```

### 1.3 Эндпоинт

**Файл**: `backend/app/api/users.py` — добавить:

```python
from app.schemas import UserInterestSummary

@router.get("/{inn}/interests", response_model=UserInterestSummary)
async def get_user_interests(inn: str, db: AsyncSession = Depends(get_db)):
    from app.services.personalization import get_personalization_service
    svc = get_personalization_service()
    data = await svc.get_interest_summary(inn, db)
    return data
```

---

## Задача 2 — Новый API: персонализированные категории

**Файл**: `backend/app/api/users.py`

### 2.1 Маппинг индустрия → разрешённые категории

**Файл**: `backend/app/services/personalization_service.py` (или новый файл `category_filter.py`)

```python
INDUSTRY_ALLOWED_CATEGORIES: dict[str, list[str]] = {
    "Образование": [
        "Канцелярские товары", "Мебель", "Мебель офисная", "IT-оборудование",
        "Компьютеры", "Спортивный инвентарь", "Хозяйственные товары", "Книги",
    ],
    "Медицина": [
        "Медицинские товары", "Расходные материалы", "Мебель медицинская",
        "Хозяйственные товары", "IT-оборудование", "Спецодежда",
    ],
    "Стройматериалы": [
        "Стройматериалы", "Электротехника", "Инструменты", "Крепёж",
        "Хозяйственные товары", "Мебель", "Спецодежда",
    ],
    "Электротехника": [
        "Электротехника", "IT-оборудование", "Инструменты", "Кабели",
    ],
    "IT-оборудование": [
        "IT-оборудование", "Компьютеры", "Сетевое оборудование",
        "Канцелярские товары", "Мебель офисная",
    ],
    "ЖКХ": [
        "ЖКХ", "Стройматериалы", "Электротехника", "Хозяйственные товары", "Инструменты",
    ],
    "Транспорт": [
        "Транспортные средства", "Запчасти", "Электротехника", "ЖКХ",
    ],
    "Хозяйственные товары": [
        "Хозяйственные товары", "Стройматериалы", "ЖКХ",
    ],
    "Канцелярские товары": [
        "Канцелярские товары", "Мебель офисная", "IT-оборудование",
    ],
}

def get_allowed_categories_for_user(
    industry: str | None,
    contract_categories: list[str],
) -> list[str]:
    """
    Возвращает список разрешённых категорий для пользователя.
    Объединяет: индустриальные категории + категории из контрактов.
    """
    allowed = set(contract_categories)
    if industry and industry in INDUSTRY_ALLOWED_CATEGORIES:
        allowed |= set(INDUSTRY_ALLOWED_CATEGORIES[industry])
    # Если ничего не определено — показывать всё (новый пользователь)
    return sorted(allowed) if allowed else []
```

### 2.2 Эндпоинт

```python
@router.get("/{inn}/categories", response_model=list[str])
async def get_user_categories(inn: str, db: AsyncSession = Depends(get_db)):
    """
    Возвращает список категорий, релевантных данному пользователю.
    Используется для фильтра 'Только интересные' на фронтенде.
    """
    from sqlalchemy import text
    result = await db.execute(text("""
        SELECT DISTINCT s.category
        FROM contracts c
        JOIN ste s ON c.ste_id = s.id
        WHERE c.customer_inn = :inn AND s.category IS NOT NULL
    """), {"inn": inn})
    contract_cats = [row.category for row in result.fetchall()]

    profile = await db.get(UserProfile, inn)
    industry = profile.industry if profile else None

    from app.services.personalization_service import get_allowed_categories_for_user
    categories = get_allowed_categories_for_user(industry, contract_cats)
    return categories if categories else contract_cats  # fallback
```

---

## Задача 3 — Затухание интересов (interest decay)

Пользователь, который давно не интересовался категорией, должен видеть её с меньшим приоритетом.

**Файл**: `backend/app/services/personalization.py` (или `personalization_service.py`)

### 3.1 Логика затухания

Добавить метод `apply_decay_to_profile`:

```python
from datetime import datetime, timedelta, timezone

DECAY_HALF_LIFE_DAYS = 14  # через 14 дней вес уменьшается вдвое

def apply_decay_to_category_weights(
    category_weights: dict[str, float],
    last_seen: dict[str, datetime],  # последнее взаимодействие по категории
    now: datetime | None = None,
) -> dict[str, float]:
    """
    Применяет экспоненциальное затухание к весам категорий.
    Категория, которую не смотрели 14 дней, теряет 50% веса.
    Категория после 30 дней практически исчезает из приоритетов.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    decayed = {}
    for cat, weight in category_weights.items():
        last = last_seen.get(cat)
        if last is None:
            decayed[cat] = weight  # нет данных — не трогаем
            continue
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days = (now - last).total_seconds() / 86400
        decay_factor = 0.5 ** (days / DECAY_HALF_LIFE_DAYS)
        decayed[cat] = weight * decay_factor

    return decayed
```

### 3.2 Вызов затухания при каждом поиске

В `get_user_boosts` (или где строятся бусты из профиля) — применять `apply_decay_to_category_weights` перед формированием буста:

```python
# Перед применением category_weights в персонализации:
from app.services.decay import apply_decay_to_category_weights
effective_weights = apply_decay_to_category_weights(ctx.category_weights, last_seen_by_category)
```

`last_seen_by_category` — загружать из БД (таблица `events`, MAX(created_at) per category).

### 3.3 Сохранение последней даты взаимодействия

При обработке события (`POST /events`) — сохранять в Redis для быстрого доступа:
```python
# В events.py при обработке клика:
await redis.set(f"last_cat:{user_inn}:{category}", datetime.utcnow().isoformat(), ex=86400*60)
```

---

## Задача 4 — Переработать demo-пользователей (seed_demo.py)

**Файл**: `backend/scripts/seed_demo.py`

### 4.1 Требования к демо-профилям

Три пользователя с реальными историями закупок, которые система умеет читать:

```python
DEMO_PROFILES = [
    {
        "inn": "7701234567",
        "name": "Школа №1234",
        "industry": "Образование",
        "region": "Москва",
        # Исторические закупки: много канцелярии, мебели, немного IT
        "purchase_pattern": {
            "Канцелярские товары": 45,   # кол-во контрактов
            "Мебель офисная": 20,
            "IT-оборудование": 12,
            "Спортивный инвентарь": 8,
        },
    },
    {
        "inn": "7709876543",
        "name": "Городская больница №5",
        "industry": "Медицина",
        "region": "Москва",
        # Исторические закупки: медоборудование, расходники, хозтовары
        "purchase_pattern": {
            "Медицинские товары": 80,
            "Расходные материалы": 60,
            "Хозяйственные товары": 25,
            "IT-оборудование": 15,
        },
    },
    {
        "inn": "7705551234",
        "name": "СтройМонтаж ООО",
        "industry": "Стройматериалы",
        "region": "Московская область",
        # Исторические закупки: стройматериалы, электротехника
        "purchase_pattern": {
            "Стройматериалы": 120,
            "Электротехника": 55,
            "Инструменты": 30,
            "Хозяйственные товары": 18,
        },
    },
]
```

### 4.2 Генерация контрактов из реальных STE

Вместо захардкоженных моков — брать реальные STE из БД по категории:

```python
async def seed_demo_contracts(db: AsyncSession):
    for profile in DEMO_PROFILES:
        # Создать / обновить UserProfile
        await db.merge(UserProfile(
            inn=profile["inn"],
            name=profile["name"],
            industry=profile["industry"],
            region=profile["region"],
        ))

        for category, count in profile["purchase_pattern"].items():
            # Берём реальные STE из этой категории
            result = await db.execute(
                text("SELECT id FROM ste WHERE category ILIKE :cat LIMIT :lim"),
                {"cat": f"%{category}%", "lim": count}
            )
            ste_ids = [row.id for row in result.fetchall()]

            for i, ste_id in enumerate(ste_ids):
                contract_date = date.today() - timedelta(days=random.randint(1, 365))
                await db.merge(Contract(
                    contract_id=f"DEMO-{profile['inn']}-{ste_id}",
                    ste_id=ste_id,
                    customer_inn=profile["inn"],
                    customer_name=profile["name"],
                    customer_region=profile["region"],
                    contract_date=contract_date,
                    cost=random.uniform(1000, 500000),
                ))

        await db.commit()
        # Обновить профиль персонализации в памяти
        from app.services.personalization import get_personalization_service
        svc = get_personalization_service()
        await svc.rebuild_from_db(profile["inn"], db)
```

---

## Задача 5 — Улучшить explainability_service: язык бизнеса

**Файл**: `backend/app/services/explainability_service.py`

### 5.1 Текущая проблема

Текущие объяснения типа "BM25 score: 0.84", "catboost_rank: +0.23" непонятны жюри.

### 5.2 Таблица маппинга факторов

Добавить функцию `humanize_factor`:

```python
def humanize_factor(factor: str, weight: float, meta: dict | None = None) -> str:
    """
    Преобразует технический фактор в понятное бизнес-объяснение.
    """
    meta = meta or {}
    category = meta.get("category", "")
    contract_count = meta.get("contract_count", 0)
    session_count = meta.get("session_count", 0)

    templates = {
        "bm25": lambda: f"Точное совпадение слов в названии товара",
        "semantic": lambda: f"Семантически похож на запрос пользователя",
        "history": lambda: (
            f"Пользователь закупал товары категории '{category}' — {contract_count} контрактов в истории"
            if contract_count > 0 else
            f"Совпадает с историей закупок пользователя"
        ),
        "category": lambda: f"Входит в предпочтительную категорию '{category}'",
        "session": lambda: (
            f"Пользователь кликал на похожие товары {session_count} раз в этой сессии"
            if session_count > 0 else
            "Интерес проявлен в текущей сессии"
        ),
        "negative": lambda: "Снижен в позиции — пользователь ранее отклонил похожие товары",
        "popularity": lambda: f"Часто заказывается другими покупателями",
        "like_boost": lambda: "Поднят — пользователь оценил этот товар положительно",
        "dislike_penalty": lambda: "Опущен — пользователь отметил как нерелевантный",
        "catboost": lambda: "ML-модель оценила как подходящий для данного пользователя",
        "decay": lambda: f"Категория '{category}' давно не просматривалась — приоритет снижен",
    }

    fn = templates.get(factor)
    return fn() if fn else factor
```

### 5.3 Применить в search.py при формировании explanations

В `backend/app/api/search.py` при построении `RankingExplanation`:

```python
from app.services.explainability_service import humanize_factor

explanations = [
    RankingExplanation(
        reason=humanize_factor(exp["factor"], exp["weight"], exp.get("meta")),
        factor=exp["factor"],
        weight=exp["weight"],
    )
    for exp in raw_explanations
]
```

---

## Задача 6 — Логировать запросы пользователя в Redis

**Файл**: `backend/app/api/search.py`

В начале обработки поиска, после валидации запроса — логировать в Redis список последних запросов:

```python
try:
    import redis.asyncio as aioredis
    _r = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
    pipe = _r.pipeline()
    pipe.lpush(f"user_queries:{req.user_inn}", req.query.strip())
    pipe.ltrim(f"user_queries:{req.user_inn}", 0, 9)  # хранить последние 10
    pipe.expire(f"user_queries:{req.user_inn}", 86400)
    await pipe.execute()
    await _r.aclose()
except Exception:
    pass
```

Это используется в `get_interest_summary` для отображения последнего запроса в панели интересов.

---

## Файловая карта (итог)

```
backend/app/
  main.py                         — убрать регистрацию products.router
  schemas.py                      — добавить CategoryInterest, UserInterestSummary;
                                    удалить CreateProductRequest, PromoteRequest и др.
  models.py                       — без изменений (поля promotion_* оставить в БД, не трогать)

  api/
    users.py                      — добавить GET /{inn}/interests, GET /{inn}/categories
    search.py                     — логировать запросы; humanize explanations; убрать promotion boost
    analytics.py                  — убрать promotion-связанные ответы
    products.py                   — не регистрировать (но файл оставить)

  services/
    personalization_service.py    — добавить get_interest_summary, apply_decay_to_category_weights,
                                    get_allowed_categories_for_user
    explainability_service.py     — добавить humanize_factor
    ranking_service.py            — убрать promotion_boost из scoring

backend/scripts/
  seed_demo.py                    — переписать: реальные контракты из STE по категориям
```

---

## API-контракт для Dev 1 (финальные форматы ответов)

### GET /users/{inn}/interests
```json
{
  "inn": "7701234567",
  "label": "Школа №1234",
  "top_categories": [
    {
      "category": "Канцелярские товары",
      "click_count": 8,
      "contract_count": 45,
      "weight": 0.72,
      "trend": "rising",
      "last_interaction_days": 0
    }
  ],
  "session_clicks_total": 12,
  "recent_query": "ручка гелевая",
  "active_interests": ["Канцелярские товары", "Мебель офисная"],
  "fading_interests": ["IT-оборудование"],
  "last_updated": "2026-04-05T12:00:00+00:00"
}
```

### GET /users/{inn}/categories
```json
["Канцелярские товары", "Мебель офисная", "IT-оборудование", "Спортивный инвентарь"]
```

### STEResult (обновлённый — для стрелок позиций)
Поле `rank_delta` добавлять на стороне фронтенда (Dev 1 вычисляет сам из двух последовательных поисков). От бэкенда не требуется.

---

## Порядок выполнения

| # | Задача | Время | Блокирует Dev 1 |
|---|--------|-------|-----------------|
| 0 | Убрать продвижение из API | 30 мин | нет |
| 1 | GET /interests эндпоинт | 90 мин | да (InterestPanel) |
| 2 | GET /categories эндпоинт | 30 мин | да (фильтр категорий) |
| 3 | Decay интересов | 60 мин | нет |
| 4 | Seed demo пользователей | 45 мин | да (DemoSelector) |
| 5 | Humanize explanations | 40 мин | нет |
| 6 | Логировать запросы | 15 мин | нет |

**Итого**: ~5 часов. Задачи 1 и 2 — стартовать первыми, они разблокируют Dev 1.

## Правила

- Не трогать `frontend/**`
- Не удалять promotion-колонки из БД (только убрать использование в логике)
- Все новые эндпоинты — документировать через FastAPI docstring
- Для тестирования: `python -m scripts.seed_demo` должна работать без ошибок
