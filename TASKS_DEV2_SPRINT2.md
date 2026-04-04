# Dev 2 — Sprint 2: Backend, DB & Ranking Tasks

**Зона ответственности**: `backend/app/services/**`, `backend/app/models.py`, `backend/app/api/**`, `backend/app/schemas.py`, `backend/scripts/**`
**Зона запрета**: не трогать `frontend/**`

**Алгоритм работы**:
1. Сначала — DB-миграция (Задача 1), она разблокирует всё остальное.
2. Потом — API-эндпоинты (Задача 2), Dev1 сможет подключить фронт.
3. Затем — Ранжирование (Задачи 3, 4, 5).

---

## Задача 1 — DB-миграция: теги, продвижение, user_id на STE

**Файл**: `backend/app/models.py`

### 1.1 Добавить поля в модель STE
```python
from sqlalchemy import Array, String, DateTime

class STE(Base):
    # ... существующие поля ...
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True, default=list
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    promoted_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    promotion_boost: Mapped[float] = mapped_column(
        Numeric(5, 3), nullable=False, server_default="0.0"
    )
    creator_user_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    order_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
```

### 1.2 Написать Alembic-миграцию (или ALTER TABLE вручную)

**Файл**: `backend/scripts/migrate_sprint2.py` (новый)
```python
"""Apply Sprint 2 schema changes: tags, promotion, description."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

MIGRATIONS = [
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}'",
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS description TEXT",
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS promoted_until TIMESTAMPTZ",
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS promotion_boost NUMERIC(5,3) DEFAULT 0.0",
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS creator_user_id TEXT",
    "ALTER TABLE ste ADD COLUMN IF NOT EXISTS order_count BIGINT DEFAULT 0",
    # Индекс для поиска по тегам
    "CREATE INDEX IF NOT EXISTS ix_ste_tags ON ste USING GIN(tags)",
    # Индекс для поиска активных продвижений
    "CREATE INDEX IF NOT EXISTS ix_ste_promoted ON ste(promoted_until) WHERE promoted_until IS NOT NULL",
    # Обновить tsvector для тегов — расширить после добавления колонки
    """
    CREATE OR REPLACE FUNCTION ste_tsv_update() RETURNS trigger AS $$
    BEGIN
      NEW.name_tsv := to_tsvector('russian',
        COALESCE(NEW.name, '') || ' ' ||
        COALESCE(array_to_string(NEW.tags, ' '), '') || ' ' ||
        COALESCE(NEW.description, '')
      );
      RETURN NEW;
    END
    $$ LANGUAGE plpgsql;
    """,
    """
    DROP TRIGGER IF EXISTS ste_tsv_trigger ON ste;
    CREATE TRIGGER ste_tsv_trigger BEFORE INSERT OR UPDATE ON ste
    FOR EACH ROW EXECUTE FUNCTION ste_tsv_update();
    """,
]

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        for sql in MIGRATIONS:
            print(f"Running: {sql[:60]}...")
            await conn.execute(text(sql))
    await engine.dispose()
    print("Migration done!")

asyncio.run(main())
```

**Запустить**: `python backend/scripts/migrate_sprint2.py`

---

## Задача 2 — API-эндпоинты для товаров и продвижения

**Файл**: `backend/app/api/products.py` (новый)

### 2.1 Создание товара
```python
@router.post("", response_model=CreateProductResponse, status_code=201)
async def create_product(req: CreateProductRequest, db: AsyncSession = Depends(get_db)):
    """Create a new product listing by a supplier."""
    result = await db.execute(
        text("""
            INSERT INTO ste (name, category, tags, description, creator_user_id, order_count, attributes)
            VALUES (:name, :category, :tags, :description, :user_id, 0, '{}')
            RETURNING id
        """),
        {
            "name": req.name,
            "category": req.category,
            "tags": req.tags,
            "description": req.description,
            "user_id": req.user_id,
        }
    )
    new_id = result.scalar()
    await db.commit()
    return CreateProductResponse(id=new_id, name=req.name, tags=req.tags,
                                  message="Товар создан успешно")
```

### 2.2 Активация продвижения
```python
@router.post("/{product_id}/promote", response_model=PromoteResponse)
async def promote_product(
    product_id: int, req: PromoteRequest, db: AsyncSession = Depends(get_db)
):
    """Activate paid promotion for a product."""
    from datetime import datetime, timedelta, timezone

    promoted_until = datetime.now(timezone.utc) + timedelta(days=req.days)
    # Boost логика: базовый boost = 2.0, дополнительно пропорционально дням
    boost = round(2.0 + min(req.days / 30.0, 1.0), 3)  # max = 3.0

    await db.execute(
        text("""
            UPDATE ste SET promoted_until = :until, promotion_boost = :boost
            WHERE id = :id
        """),
        {"until": promoted_until, "boost": boost, "id": product_id}
    )
    await db.commit()
    return PromoteResponse(
        product_id=product_id,
        promoted_until=promoted_until.isoformat(),
        boost=boost,
        price=req.days * 350
    )
```

### 2.3 Список "Мои товары"
```python
@router.get("", response_model=list[MyProductResponse])
async def get_my_products(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get all products created by a user."""
    from datetime import datetime, timezone
    rows = await db.execute(
        text("""
            SELECT s.id, s.name, s.category, s.tags, s.description,
                   s.promoted_until, s.promotion_boost, s.order_count,
                   COALESCE(sp.contract_cnt, s.order_count, 0) AS total_orders
            FROM ste s
            LEFT JOIN ste_popularity sp ON sp.ste_id = s.id
            WHERE s.creator_user_id = :uid
            ORDER BY s.id DESC
        """),
        {"uid": user_id}
    )
    now = datetime.now(timezone.utc)
    return [
        MyProductResponse(
            id=r.id, name=r.name, category=r.category,
            tags=r.tags or [], order_count=r.total_orders,
            is_promoted=r.promoted_until is not None and r.promoted_until > now,
            promoted_until=r.promoted_until.isoformat() if r.promoted_until else None,
            promotion_boost=float(r.promotion_boost or 0),
        )
        for r in rows
    ]
```

### 2.4 Схемы (добавить в `backend/app/schemas.py`)
```python
class CreateProductRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=500)
    category: str | None = None
    tags: list[str] = []
    description: str | None = None
    user_id: str

class CreateProductResponse(BaseModel):
    id: int
    name: str
    tags: list[str]
    message: str

class PromoteRequest(BaseModel):
    days: int = Field(..., ge=1, le=30)

class PromoteResponse(BaseModel):
    product_id: int
    promoted_until: str
    boost: float
    price: int

class MyProductResponse(BaseModel):
    id: int
    name: str
    category: str | None
    tags: list[str]
    order_count: int
    is_promoted: bool
    promoted_until: str | None
    promotion_boost: float
```

### 2.5 Подключить роутер
**Файл**: `backend/app/main.py` — добавить:
```python
from app.api.products import router as products_router
app.include_router(products_router, prefix="/api/v1/products")
```

---

## Задача 3 — Теги в поиске

### 3.1 Поиск по тегам в SQL
**Файл**: `backend/app/api/search.py` — изменить `_get_candidates`:

Текущий WHERE добавить тег-поиск:
```sql
OR s.tags && ARRAY[:tag_terms]::TEXT[]          -- прямое совпадение тега
OR s.tags @> ARRAY[:exact_tag]::TEXT[]          -- exact tag match
```

В Python-код перед SQL:
```python
# Извлечь теги из запроса — каждое слово запроса проверяем как потенциальный тег
query_words = [w.strip().lower() for w in pq.clean.split() if len(w) > 2]

# В SQL параметры добавить
params["tag_terms"] = query_words  # для ANY/overlaps
```

Или более простой вариант — использовать уже расширенный `name_tsv` (тригер из Задачи 1 уже включает теги в tsvector), поэтому обычный `name_tsv @@ tsquery` уже будет искать по тегам. Дополнительно — прямое совпадение:

```sql
OR :query_lower = ANY(s.tags)     -- точное совпадение тега
```

### 3.2 Добавить теги в STEResult
**Файл**: `backend/app/schemas.py` — в `STEResult`:
```python
tags: list[str] = []
is_promoted: bool = False
promotion_boost: float = 0.0
```

**Файл**: `backend/app/api/search.py` — в SQL выборке добавить `s.tags, s.promoted_until, s.promotion_boost`:
```sql
SELECT s.id, s.name, s.category, s.attributes, s.tags,
       s.promoted_until, s.promotion_boost, ...
```

В сборке результата:
```python
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
is_promoted = (row.promoted_until is not None and row.promoted_until > now)
```

---

## Задача 4 — Продвижение в ранжировании

**Файл**: `backend/app/api/search.py` — в функцию расчёта `final_score`:

### 4.1 Логика promotion boost

В блоке где вычисляется `final_score` (после `base_score + personalization_boost`):
```python
# Promotion boost: если active promotion — добавляем фиксированный сигнал
if row.promoted_until:
    from datetime import datetime, timezone
    if row.promoted_until > datetime.now(timezone.utc):
        promotion_signal = float(row.promotion_boost or 2.0)
        final_score += promotion_signal
        explanations.append(RankingExplanation(
            reason="Продвигается",
            factor="promotion",
            weight=promotion_signal
        ))
```

### 4.2 Логика популярности (тай-брейкер)

Если два товара имеют одинаковое продвижение — выше тот, у кого больше заказов:
```python
# Используем order_count как тай-брейкер (малый вес, не перевешивает score)
popularity_tiebreak = min(row.order_count or 0, 10000) / 10000 * 0.1
final_score += popularity_tiebreak
```

### 4.3 Стиль badge в STEResult

В response добавить флаг `is_promoted` (уже описан в Задаче 3.2) — Dev1 использует для отображения badge "Продвигается".

---

## Задача 5 — Like/Dislike сигналы в ранжировании

**Файл**: `backend/app/api/events.py` — в обработчик событий

### 5.1 Сохранение like/dislike в Redis
```python
# В endpoint POST /events
if event.action == "like":
    # Boost для этого ste_id в контексте этого пользователя
    key = f"user:{event.user_id}:likes"
    await redis.zincrby(key, 1.5, str(event.ste_id))
    await redis.expire(key, 86400 * 7)  # TTL 7 дней

elif event.action == "dislike":
    # Penalty для этого ste_id
    key = f"user:{event.user_id}:dislikes"
    await redis.zincrby(key, 1.0, str(event.ste_id))
    await redis.expire(key, 86400 * 7)
```

### 5.2 Применение like/dislike в поиске
**Файл**: `backend/app/services/session_index.py` — добавить функцию:
```python
async def get_like_dislike_boosts(user_id: str, ste_ids: list[int]) -> dict[int, float]:
    """
    Returns {ste_id: score_delta} based on persistent like/dislike signals.
    Likes: +1.5, Dislikes: -1.5 (gradually push down).
    """
    if not ste_ids or not user_id:
        return {}
    try:
        r = get_redis_client()
        like_key = f"user:{user_id}:likes"
        dislike_key = f"user:{user_id}:dislikes"
        boosts = {}
        for sid in ste_ids:
            like_score = await r.zscore(like_key, str(sid)) or 0.0
            dislike_score = await r.zscore(dislike_key, str(sid)) or 0.0
            delta = like_score * 1.5 - dislike_score * 1.5
            if delta != 0:
                boosts[sid] = delta
        return boosts
    except Exception:
        return {}
```

**Файл**: `backend/app/api/search.py` — интегрировать в pipeline (Stage 4):
```python
# Stage 4b: Like/Dislike persistent signals
like_boosts = await get_like_dislike_boosts(req.user_inn, [r.id for r in rows])
for row in rows:
    row_score = scores.get(row.id, 0)
    if row.id in like_boosts:
        scores[row.id] = row_score + like_boosts[row.id]
```

---

## Задача 6 — Эндпоинт объяснения "Размышления поиска"

**Файл**: `backend/app/api/search.py` — добавить эндпоинт

```python
@router.get("/thinking/{ste_id}", response_model=ThinkingResponse)
async def get_thinking(
    ste_id: int,
    query: str,
    user_inn: str = "",
    db: AsyncSession = Depends(get_db),
):
    """
    Explain ranking decision for a specific STE item and query.
    Used by 'Размышления поиска' panel in UI.
    """
    from app.services.query_processor import process_query
    from app.services.nlp_service import get_nlp_service

    nlp = get_nlp_service()
    query_data = nlp.process_query(query)
    pq = process_query(query_data.get("corrected", query))

    row = (await db.execute(
        text("""
            SELECT s.id, s.name, s.category, s.tags, s.promoted_until,
                   s.promotion_boost, s.order_count,
                   COALESCE(sp.contract_cnt, 0) AS contract_cnt,
                   ts_rank(s.name_tsv, plainto_tsquery('russian', :lemma)) AS ts_score,
                   similarity(s.name, :orig) AS trgm_score
            FROM ste s
            LEFT JOIN ste_popularity sp ON sp.ste_id = s.id
            WHERE s.id = :ste_id
        """),
        {"ste_id": ste_id, "lemma": pq.lemma, "orig": query}
    )).fetchone()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "STE not found")

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    is_promoted = row.promoted_until is not None and row.promoted_until > now

    factors = [
        {"name": "Совпадение по tsvector", "score": round(float(row.ts_score), 4), "type": "text"},
        {"name": "Триграмное сходство", "score": round(float(row.trgm_score), 4), "type": "text"},
        {"name": "Популярность (кол-во контрактов)", "score": int(row.contract_cnt), "type": "popularity"},
    ]
    if is_promoted:
        factors.append({"name": "Активное продвижение", "score": float(row.promotion_boost or 2.0), "type": "promotion"})

    return ThinkingResponse(
        ste_id=ste_id,
        name=row.name,
        query=query,
        corrected_query=query_data.get("corrected", query),
        applied_synonyms=query_data.get("applied_synonyms", []),
        was_corrected=query_data.get("was_corrected", False),
        factors=factors,
        is_promoted=is_promoted,
        promotion_boost=float(row.promotion_boost or 0),
        tags=row.tags or [],
    )
```

**Схемы** (`backend/app/schemas.py`):
```python
class ThinkingFactor(BaseModel):
    name: str
    score: float
    type: str  # "text" | "popularity" | "promotion" | "personalization"

class ThinkingResponse(BaseModel):
    ste_id: int
    name: str
    query: str
    corrected_query: str
    applied_synonyms: list[str]
    was_corrected: bool
    factors: list[ThinkingFactor]
    is_promoted: bool
    promotion_boost: float
    tags: list[str]
```

---

## Задача 7 — Накрутка popularity для тестирования продвижения

**Файл**: `backend/app/api/products.py` — добавить тестовый endpoint:
```python
@router.post("/{product_id}/fake-orders")
async def add_fake_orders(
    product_id: int, count: int = 10, db: AsyncSession = Depends(get_db)
):
    """
    Dev/demo endpoint: artificially increase order count for a product.
    Used to demonstrate popularity-based ranking.
    """
    await db.execute(
        text("UPDATE ste SET order_count = order_count + :n WHERE id = :id"),
        {"n": count, "id": product_id}
    )
    await db.commit()
    return {"product_id": product_id, "added_orders": count, "message": f"Added {count} fake orders"}
```

Также обновить `ste_popularity` view при изменении `order_count`:
```sql
-- При запуске promote или fake-orders добавлять в ste_popularity
INSERT INTO ste_popularity (ste_id, contract_cnt)
VALUES (:ste_id, :count)
ON CONFLICT (ste_id) DO UPDATE SET contract_cnt = ste_popularity.contract_cnt + :count;
```

---

## Файловая карта (итог)

```
backend/
  scripts/
    migrate_sprint2.py          — НОВЫЙ: ALTER TABLE миграция
  app/
    models.py                   — правки: tags, promoted_until, promotion_boost, creator_user_id, order_count
    schemas.py                  — правки: CreateProductRequest/Response, PromoteRequest/Response,
                                           MyProductResponse, ThinkingFactor, ThinkingResponse
    api/
      products.py               — НОВЫЙ: CRUD + promote + fake-orders
      search.py                 — правки: promotion boost в scoring, теги в SQL, /thinking/{id}
      events.py                 — правки: like/dislike → Redis
    services/
      session_index.py          — правки: get_like_dislike_boosts()
    main.py                     — правки: подключить products router
```

---

## Порядок выполнения (рекомендуемый)

1. **Задача 1** (миграция) — 20 мин — `python backend/scripts/migrate_sprint2.py`
2. **Задача 2** (API products) — 60 мин
3. **Задача 3** (теги в поиске) — 30 мин
4. **Задача 4** (promotion в ранжировании) — 30 мин
5. **Задача 5** (like/dislike) — 30 мин
6. **Задача 6** (thinking endpoint) — 45 мин
7. **Задача 7** (fake-orders) — 15 мин

**Всего**: ~4 часа

## Важные заметки

- Всегда запускать `migrate_sprint2.py` перед изменением `models.py` на prod.
- `ste_popularity` таблица уже есть (из Sprint 1) — при fake-orders обновлять её тоже.
- Эндпоинт `/thinking/{ste_id}` работает независимо от Dev1 — Dev1 его подключает позже.
- `is_promoted` и `promotion_boost` должны возвращаться в каждом `STEResult` из `/search`.
- Не трогать `frontend/**` — полная независимость от Dev1.
- Тестирование: `python check_search.py` после каждого изменения в ранжировании.
