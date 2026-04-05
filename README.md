# TenderHack Moscow: Персонализированный умный поиск СТЕ

Сервис интеллектуального поиска для Портала Поставщиков (zakupki.mos.ru), разработанный в рамках хакатона TenderHack. Решение объединяет полнотекстовый поиск, семантический анализ, машинное обучение и персонализацию в реальном времени.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?style=flat-square&logo=postgresql)
![React](https://img.shields.io/badge/React-19-cyan?style=flat-square&logo=react)
![CatBoost](https://img.shields.io/badge/CatBoost-LTR-orange?style=flat-square)

---

## Ключевые возможности

*   **Коллективное дообучение (Collective Learning)**: Система анализирует успешные поисковые сессии всех пользователей и автоматически адаптирует выдачу. Если пользователи часто выбирают "Упаковочная бумага" по запросу "Бумага для подарков", нейросеть запоминает эту связь и улучшает будущие результаты для всех.
*   **Глубокая персонализация**: Учет исторического профиля (закупки, контракты) и поведения в текущей сессии (клики, лайки, просмотры). Интересы динамически затухают со временем.
*   **Прозрачность ИИ (Explainable AI)**: Пользователь всегда видит, почему товар находится на определенной позиции (совпадение по тексту, семантика, влияние профиля, коллективный опыт).
*   **Семантический поиск**: Использование легковесной языковой модели `rubert-tiny2` для понимания смысла запроса, а не только точного совпадения слов.
*   **Умная обработка запросов**: Автоматическая лемматизация (`pymorphy2`), исправление опечаток, раскрытие синонимов и специфичных аббревиатур.

---

## Архитектура решения

```mermaid
flowchart TD
    %% Define styles
    classDef client fill:#61dafb,stroke:#000,stroke-width:2px,color:#000
    classDef backend fill:#009688,stroke:#000,stroke-width:2px,color:#fff
    classDef db fill:#336791,stroke:#000,stroke-width:2px,color:#fff
    classDef redis fill:#dc382d,stroke:#000,stroke-width:2px,color:#fff
    classDef process fill:#f9f9f9,stroke:#333,stroke-width:1px,color:#000

    User((Пользователь)) --> |Ввод запроса| Client
    Client["🖥️ React 19 Клиент"]:::client -- "POST /search" --> API{"⚡ FastAPI Router"}:::backend

    subgraph SearchEngine ["Поисковый движок (Pipeline)"]
        direction TB
        S1["1. Лемматизация и опечатки (pymorphy2)"]:::process
        S2["2. Расширение синонимами"]:::process
        S3["3. Поиск кандидатов BM25 (tsvector)"]:::process
        S4["4. Семантический Re-rank (rubert-tiny2)"]:::process
        S5["5. Персонализация (История + Сессия)"]:::process
        S6["6. ML Ранжирование (CatBoost)"]:::process
        S7["7. Учет коллективного опыта"]:::process

        S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7
    end

    API --> S1
    S7 -- "Результаты + Объяснения" --> Client

    S3 <--> PG[("🐘 PostgreSQL 16\n(pg_trgm, pgvector)")]:::db
    S4 <--> PG
    S5 <--> Redis[("🔴 Redis 7\n(Кэш сессий)")]:::redis
    S7 <--> PG
```

---

## Быстрый старт

### Требования
*   Docker 24+
*   Docker Compose v2

### Запуск

```bash
git clone <repo-url>
cd TenderHackMoscow

# Подготовка датасетов
mkdir -p data
cp /path/to/ste_dataset.xlsx data/
cp /path/to/contracts_dataset.xlsx data/

# Запуск всех сервисов в фоне
make up

# Накатывание миграций БД и загрузка данных
make migrate
make load-data
```

Приложение доступно по адресу: `http://localhost`  
Документация API (Swagger): `http://localhost:8000/docs`

---

## Основные API методы

### `POST /api/v1/search`
Персонализированный поиск СТЕ с учетом контекста пользователя.

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

**Особенности ответа:**
*   `results[]` содержит `explanations[]` (почему товар на этой позиции).
*   `corrected_query` (лемматизированная форма запроса).
*   `collective_insights` (данные о том, как другие пользователи повлияли на выдачу).
*   `applied_rewrites` (примененные синонимы и расширения).

### `GET /api/v1/search/suggest?q=ноутб`
Быстрый автокомплит на базе `pg_trgm` (<50 мс).

### `POST /api/v1/events`
Логирование действий пользователя для персонализации и дообучения.
Поддерживаемые события: `click`, `like`, `dislike`, `view`, `bounce`, `hide`.

---

## Стек технологий

| Слой | Технологии | Обоснование |
| :--- | :--- | :--- |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0 Async, asyncpg | Асинхронная обработка, высокая производительность |
| **База данных** | PostgreSQL 16 + pgvector + pg_trgm | Единое хранилище для реляционных данных, полнотекстового и векторного поиска |
| **Кеширование** | Redis 7 | Быстрое хранение сессий и динамических индексов |
| **NLP** | pymorphy2, symspellpy, NLTK | Быстрая лемматизация и исправление опечаток без внешних API |
| **Семантика** | rubert-tiny2 (cointegrated), FAISS | Легковесная модель для русского языка, быстрый инференс на CPU |
| **Ранжирование** | CatBoost (LTR), SHAP | Градиентный бустинг для Learning-to-Rank с возможностью интерпретации |
| **Frontend** | React 19, TypeScript, Vite 6, Tailwind CSS | Современный стек для быстрой разработки и типизации |
| **Инфраструктура** | Docker, Docker Compose, Nginx | Изолированная среда, простота развертывания |