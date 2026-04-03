# TenderHack Moscow — Персонализированный умный поиск СТЕ

Сервис персонализированного поиска для Портала Поставщиков (zakupki.mos.ru).  
Разработан в рамках хакатона TenderHackMoscow (48 ч).

---

## Архитектура

```
┌─────────────────────────────────────────────────────┐
│                    Клиент (браузер)                  │
│  React 19 + Vite + TypeScript + Tailwind CSS         │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP  /api/v1/*
┌──────────────────────▼──────────────────────────────┐
│              FastAPI Backend (Python 3.11)            │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Search Pipeline                                │ │
│  │  1. pymorphy2 query normalization               │ │
│  │  2. pg_trgm + tsvector candidate retrieval      │ │
│  │  3. [Dev2] rubert-tiny2 semantic re-rank        │ │
│  │  4. SQL rule-based personalization boosts       │ │
│  │  5. Redis session dynamic indexing              │ │
│  │  6. [Dev2] CatBoost LTR re-rank                 │ │
│  └─────────────────────────────────────────────────┘ │
└──────────┬────────────────────────┬─────────────────┘
           │                        │
┌──────────▼──────────┐  ┌──────────▼──────────────┐
│  PostgreSQL 16       │  │  Redis 7                 │
│  + pgvector          │  │  (session state,         │
│  + pg_trgm           │  │   dynamic indexing)      │
│  Tables: ste,        │  └─────────────────────────┘
│  contracts,          │
│  user_profiles,      │
│  events              │
└─────────────────────┘
```

---

## Быстрый старт (Ubuntu / Linux)

### Требования
- Docker 24+
- Docker Compose v2

### Запуск

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd TenderHackMoscow

# 2. Положить датасеты в ./data/
mkdir -p data
cp /path/to/ste_dataset.xlsx data/
cp /path/to/contracts_dataset.xlsx data/

# 3. Поднять все сервисы (PostgreSQL, Redis, Backend, Frontend)
make up

# 4. Запустить миграции
make migrate

# 5. Загрузить данные
make load-data
```

Приложение доступно на `http://localhost`.  
API документация: `http://localhost:8000/docs`

---

## API

### `POST /api/v1/search`
Персонализированный поиск СТЕ.

```json
{
  "query": "ноутбук",
  "user_inn": "7701234567",
  "session_id": "s_abc123",
  "limit": 20,
  "offset": 0
}
```

Ответ содержит:
- `results[]` с полем `explanations[]` — почему товар на этой позиции
- `corrected_query` — лемматизированная форма запроса
- `did_you_mean` — причина смены выдачи в сессии

### `GET /api/v1/search/suggest?q=ноутб`
Быстрый автокомплит (pg_trgm, <50 мс).

### `POST /api/v1/events`
Логирование действий пользователя.

| `event_type` | Сигнал |
|---|---|
| `click` | Позитивный |
| `compare` | Позитивный |
| `like` | Позитивный |
| `view` | Нейтральный |
| `bounce` | Негативный (возврат < 3 сек) |
| `hide` | Негативный (явный отказ) |

### `POST /api/v1/users/onboarding`
Создание/обновление профиля пользователя (cold start).

---

## Стек технологий

| Компонент | Решение | Обоснование |
|---|---|---|
| Backend | FastAPI + asyncpg | Async, высокая производительность |
| База данных | PostgreSQL 16 + pgvector + pg_trgm | Один сервис: текстовый + векторный поиск |
| Морфология | pymorphy2 | Легковесная (~5 МБ), 100% offline |
| Персонализация | SQL rule-based + CatBoost Ranker | Нет внешних API, быстрый инференс |
| Семантика | rubert-tiny2 (~118 МБ) + FAISS | Легковесная BERT-like модель для Russian |
| Динамическая индексация | Redis | Sub-ms session state без перезагрузки индекса |
| Frontend | React 19 + Vite + Tailwind | Быстрая разработка, соответствие UI-киту |
| Контейнеризация | Docker Compose | Одна команда для деплоя |
