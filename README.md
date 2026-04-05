# TenderHack Moscow -- Персонализированный умный поиск СТЕ

Сервис персонализированного поиска для Портала Поставщиков (zakupki.mos.ru).  
Разработан в рамках хакатона TenderHackMoscow.

---

## Архитектура

```
 Клиент (браузер)
 React 19 + Vite + TypeScript
          |  HTTP /api/v1/*
          v
 FastAPI Backend (Python 3.11)
 +------------------------------------------+
 | Search Pipeline                          |
 | 1. pymorphy2 лемматизация + исправление  |
 | 2. Фразовые перезаписи + синонимы        |
 | 3. pg_trgm + tsvector BM25 retrieval     |
 | 4. rubert-tiny2 семантический re-rank    |
 | 5. Персонализация (история + сессия)     |
 | 6. CatBoost Learning-to-Rank             |
 | 7. Collective learning (дообучение)      |
 +------------------------------------------+
          |                    |
 PostgreSQL 16            Redis 7
 + pgvector               (session state,
 + pg_trgm                 dynamic indexing)
```

---

## Быстрый старт

### Требования
- Docker 24+
- Docker Compose v2

### Запуск

```bash
git clone <repo-url>
cd TenderHackMoscow

# Положить датасеты
mkdir -p data
cp /path/to/ste_dataset.xlsx data/
cp /path/to/contracts_dataset.xlsx data/

# Поднять все сервисы
make up

# Миграции + загрузка данных
make migrate
make load-data
```

Приложение: `http://localhost`  
API docs: `http://localhost:8000/docs`

---

## Основные функции

- **Полнотекстовый поиск** с лемматизацией, исправлением опечаток, синонимами
- **Семантический поиск** через rubert-tiny2 + FAISS
- **Персонализация** на основе истории закупок и поведения в сессии
- **Ранжирование** CatBoost LTR с объяснениями (SHAP)
- **Коллективное обучение** -- система учитывает действия всех пользователей
- **Интерес-трекинг** -- отслеживание и визуализация интересов покупателя
- **Прозрачность AI** -- пользователь видит, как нейросеть приняла решение

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
  "offset": 0,
  "category": "Компьютерная техника"
}
```

Ответ содержит:
- `results[]` с `explanations[]` -- почему товар на этой позиции
- `corrected_query` -- лемматизированная форма запроса
- `collective_insights` -- данные коллективного обучения
- `applied_rewrites` -- примененные расширения запроса

### `GET /api/v1/search/suggest?q=ноутб`
Быстрый автокомплит (pg_trgm, <50 мс).

### `POST /api/v1/events`
Логирование действий пользователя (click, like, dislike, view, bounce, hide).

### `GET /api/v1/users/{inn}/categories`
Категории пользователя с количеством товаров.

### `GET /api/v1/search/facets`
Все категории с количеством товаров.

---

## Стек технологий

| Компонент | Решение |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 Async, asyncpg |
| База данных | PostgreSQL 16 + pgvector + pg_trgm |
| Кеширование | Redis 7 |
| NLP | pymorphy2, symspellpy, NLTK |
| Семантика | rubert-tiny2 (cointegrated), FAISS |
| Ранжирование | CatBoost (LTR), SHAP |
| Frontend | React 19, TypeScript, Vite 6 |
| Инфраструктура | Docker, Docker Compose, Nginx |
