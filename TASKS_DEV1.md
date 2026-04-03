# Dev 1 — Frontend & API Tasks

**Зона ответственности**: `frontend/src/**`, `backend/app/api/**`, `backend/app/schemas.py`
**Зона запрета**: не трогать `backend/app/services/**`, `backend/scripts/**`

---

## Приоритет 1 — Карточки и выдача (высокая ценность для демо)

### 1.1 Модальное окно детальной карточки СТЕ
- Файл: `frontend/src/components/STEModal.tsx` (новый)
- При клике "Подробнее" открывается модалка, не переход
- Показать: полное название, категория, все атрибуты в таблице, ID, статистика (сколько раз покупали — из поля popularity_score если придёт от бэка)
- Кнопки: «Сравнить», «В избранное», «Скрыть»
- Закрытие по Esc и клику вне области

### 1.2 Режим сравнения (Compare Tray)
- Файл: `frontend/src/components/CompareTray.tsx` (новый)
- Снизу экрана sticky-полоска: "Сравниваете: X товаров" + кнопка «Сравнить»
- При нажатии «Сравнить» на карточке — товар добавляется (макс 3)
- Страница сравнения: таблица атрибут → значения по столбцам
- Хук: `frontend/src/hooks/useCompare.ts` (новый)

### 1.3 Скелетон-загрузка вместо спиннера
- Файл: `frontend/src/components/STECardSkeleton.tsx` (новый)
- Пока `loading === true` — показывать 6 серых карточек-скелетонов (pulse animation)
- Подключить в `App.tsx` вместо пустого состояния

---

## Приоритет 2 — Фильтры и сортировка

### 2.1 Sidebar с фильтрами категорий
- Файл: `frontend/src/components/FilterPanel.tsx` (новый)
- Список уникальных категорий (получать с бэка: `GET /api/v1/search/facets`)
- Чекбоксы с количеством товаров
- При выборе — добавить `category` в `SearchRequest`

### 2.2 Бэкенд: facets endpoint
- Файл: `backend/app/api/search.py` — добавить `GET /search/facets`
- Возвращает `{categories: [{name, count}]}` — простой SQL `GROUP BY category`
- Обновить `backend/app/schemas.py`: добавить `FacetsResponse`

### 2.3 Сортировка результатов
- Файл: `frontend/src/components/SortDropdown.tsx` (новый)
- Варианты: «По релевантности», «По популярности», «По алфавиту»
- Добавить `sort_by: str = "relevance"` в `SearchRequest` schema
- В `backend/app/api/search.py` применить ORDER BY при `sort_by != "relevance"`

---

## Приоритет 3 — UX-полировка

### 3.1 Toast-уведомления
- Файл: `frontend/src/components/Toast.tsx` (новый)
- При «Скрыть» — «Товар скрыт, выдача обновится»
- При «В избранное» — «Добавлено в избранное»
- При исправлении опечатки — «Поиск исправлен: "компютер" → "компьютер"»
- Хук: `frontend/src/hooks/useToast.ts` (новый)

### 3.2 История поиска в строке
- Файл: `frontend/src/components/SearchBar.tsx` — расширить
- LocalStorage: хранить последние 5 запросов
- При фокусе на пустой строке — показать "Недавние: ..."
- Клик по истории — сразу запускает поиск

### 3.3 Пустое состояние с советами
- Файл: `frontend/src/components/EmptyState.tsx` (новый)
- При 0 результатов: показать 3 совета («Попробуйте более общий запрос», «Проверьте синонимы», «Используйте категорию»)
- Показать 3 «популярных запроса» как кнопки-теги (хардкод: бумага, картридж, компьютер)

### 3.4 Кнопка "Почему именно этот результат?" в карточке
- Файл: `frontend/src/components/STECard.tsx` — добавить иконку-вопрос (?)
- При наведении (tooltip) или клике — показать полный список `explanations` в попапе
- Стиль: плашка снизу карточки с иконкой `HelpCircle`

---

## Приоритет 4 — Бэкенд дополнения

### 4.1 Endpoint статистики поиска
- Файл: `backend/app/api/users.py` — добавить `GET /users/stats`
- Возвращает: `{total_stes, total_contracts, total_users, top_categories: [...]}`
- Используется в `ProfilePanel` для отображения масштаба системы

### 4.2 Endpoint популярных запросов
- Файл: `backend/app/api/search.py` — добавить `GET /search/popular`
- Redis: при каждом поиске делать `ZINCRBY popular_queries 1 {query}`
- `GET /popular` возвращает `ZREVRANGE popular_queries 0 9 WITHSCORES`
- Используется в EmptyState и подсказках SearchBar

### 4.3 Улучшение suggest — персональный
- Файл: `backend/app/api/search.py` — `GET /search/suggest`
- Добавить `user_inn` query param
- Если `user_inn` есть — поднимать в подсказках категории из профиля
- SQL: `UNION` с запросом на историю контрактов пользователя

---

## Файловая карта (итог)

```
frontend/src/
  components/
    STEModal.tsx          — новый
    CompareTray.tsx       — новый
    STECardSkeleton.tsx   — новый
    FilterPanel.tsx       — новый
    SortDropdown.tsx      — новый
    Toast.tsx             — новый
    EmptyState.tsx        — новый
    STECard.tsx           — правки (п. 3.4)
    SearchBar.tsx         — правки (п. 3.2)
  hooks/
    useCompare.ts         — новый
    useToast.ts           — новый

backend/app/
  api/
    search.py             — добавить /facets, /popular, улучшить /suggest
    users.py              — добавить /stats
  schemas.py              — добавить FacetsResponse, sort_by в SearchRequest
```
