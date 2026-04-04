# Dev 1 — Sprint 2: Frontend & UX Tasks

**Зона ответственности**: `frontend/src/**`, `backend/app/api/**`, `backend/app/schemas.py`
**Зона запрета**: не трогать `backend/app/services/**`, `backend/app/models.py`, `backend/scripts/**`

**Используй скилл**: `@Skills/antigravity-awesome-skills/skills/ui-ux-pro-max` — UI-компоненты, анимации, UX-паттерны.
**Стек**: React 18 + TypeScript + Vite, inline styles (цвета из дизайн-системы), lucide-react иконки.
**Цвета**: `#264B82` (blue), `#DB2B21` (red), `#0D9B68` (green), `#1A1A1A` (black), `#8C8C8C` (gray), `#E7EEF7` (pale bg).

---

## Задача 1 — UI-чистка: убрать "Сравнить", переименовать "Raw"

**Файл**: `frontend/src/components/STECard.tsx`

### 1.1 Удалить кнопку "Сравнить"
- Убрать кнопку с иконкой `GitCompare` и текстом "Сравнить" / "В сравнении" полностью.
- Убрать `inCompare` prop и передачу `"compare"` в `onAction`.
- Убрать импорт `GitCompare` из lucide-react.

### 1.2 Переименовать "Raw" → "Характеристики"
**Файл**: `frontend/src/components/STEModal.tsx`
- Найти все места где рендерится ключ `"raw"` из `item.attributes`.
- Если `attributes.raw` — показывать заголовок "Характеристики" вместо "Raw".
- Строку атрибутов из `attributes.raw` (формат `"ключ:значение;ключ:значение"`) парсить в таблицу:

```typescript
// Парсинг строки "Объем:16;Вес:0.05;Цвет:черный" в объект
const parseRawAttrs = (raw: string): Record<string, string> =>
  Object.fromEntries(raw.split(";").map(p => p.split(":").map(s => s.trim())).filter(p => p.length === 2));
```

- Отображать как таблицу: левая колонка — ключ, правая — значение.
- Убрать `CompareTray` и `CompareModal` из App.tsx и их импорты (они больше не нужны).

---

## Задача 2 — Кнопка "Нравится" с функционалом продвижения в поиске

**Файл**: `frontend/src/components/STECard.tsx`

### Что нужно сделать:
Добавить кнопку **ThumbsUp** ("Нравится") рядом с ThumbsDown в action bar карточки.

```tsx
import { ThumbsUp, ThumbsDown, ChevronRight, HelpCircle } from "lucide-react";
```

В action bar рядом с ThumbsDown:
```tsx
<div style={{ display: "flex", gap: 4, marginLeft: "auto" }}>
  <button
    onClick={() => onAction(item.id, "like")}
    style={{ color: liked ? "#0D9B68" : "#8C8C8C", background: liked ? "#E8F8F2" : "transparent",
             border: "none", borderRadius: 6, padding: "6px 8px", cursor: "pointer" }}
    title="Правильный товар — поднять в поиске"
  >
    <ThumbsUp size={13} />
  </button>
  <button
    onClick={() => onAction(item.id, "dislike")}
    style={{ color: disliked ? "#DB2B21" : "#8C8C8C", background: disliked ? "#FDECEA" : "transparent",
             border: "none", borderRadius: 6, padding: "6px 8px", cursor: "pointer" }}
    title="Неподходящий товар — опустить в поиске"
  >
    <ThumbsDown size={13} />
  </button>
</div>
```

- Локальный useState для `liked` / `disliked` (взаимоисключающие).
- При like → toast "Товар продвинут выше".
- При dislike → toast "Товар отмечен как нерелевантный".
- `onAction` уже отправляет события на бэк — Dev2 обрабатывает ранжирование.

**Файл**: `frontend/src/api/client.ts`
- Убедиться что в `logEvent` передаётся `action: "like"` или `action: "dislike"` с `meta: { ste_id: id }`.

---

## Задача 3 — Панель "Размышления поиска" (демо для жюри)

Это ключевая фича для **презентации жюри** — показать что алгоритм объяснимый.

### 3.1 Кнопка в карточке
**Файл**: `frontend/src/components/STECard.tsx`
- Добавить кнопку с иконкой `Brain` (lucide-react) в action bar.
- При клике → открыть `ThinkingModal` для данного item.

### 3.2 Новый компонент ThinkingModal
**Файл**: `frontend/src/components/ThinkingModal.tsx` (новый)

Модальное окно показывающее "как думал алгоритм":

```tsx
interface ThinkingModalProps {
  item: STEResult;
  query: string;
  position: number; // позиция в выдаче (1-based)
  onClose: () => void;
}
```

**Секции модального окна**:

1. **Позиция и итоговый score**
   ```
   Товар на позиции #3 из 15 результатов
   Итоговый score: 0.847
   ```

2. **Факторы ранжирования** (из `item.explanations`)
   - Визуальный прогресс-бар для каждого фактора
   - Если `explanations` пустые — показать "Нет дополнительных сигналов"
   ```
   Точное совпадение названия    ████████████  +400
   История закупок пользователя  ██████        +0.3
   Популярность товара           ████          +0.2
   Продвижение                   ████████████  Активно
   ```

3. **NLP pipeline**
   - Что было исправлено (corrected_query)
   - Какие синонимы применены
   - Финальный поисковый запрос

4. **Значок продвижения** (если `item.is_promoted`)
   - Зелёный блок: "Товар имеет активное продвижение — +{boost} к позиции"

5. **Кнопка "Подробнее"** → открывает STEModal

**Данные**: `ThinkingModal` получает всё из `STEResult` и пропа `position`.
Dev2 добавит в `STEResult` поле `is_promoted: bool` и `promotion_boost: float | null`.

**Стиль**: белый фон, синие заголовки секций (#264B82), без Tailwind — только inline styles.

---

## Задача 4 — Форма создания нового товара

Это win-win фича: поставщики могут добавлять свои товары.

### 4.1 Кнопка "Добавить товар" в шапке
**Файл**: `frontend/src/components/Header.tsx`
- Добавить кнопку "Добавить товар" рядом с аватаром/профилем.
- Стиль: обводочная кнопка `border: 1px solid #264B82`, цвет текста `#264B82`.
- При клике → открыть `CreateProductModal`.

### 4.2 Компонент CreateProductModal
**Файл**: `frontend/src/components/CreateProductModal.tsx` (новый)

**Поля формы**:
```
Название товара *       [__________________________]
Категория               [__dropdown_________________] (список уникальных категорий с бэка)
Теги (через запятую)    [айфон, телефон, гаджет, техника]
  Подсказка: "Теги помогают найти товар по синонимам"
Описание                [__текстовое поле____________]
                        [____________________________]
```

**Логика тегов**: input с chip-тегами. При нажатии Enter/запятой — добавляет тег как chip.
```tsx
// Пример chip-input для тегов
const [tags, setTags] = useState<string[]>([]);
const [tagInput, setTagInput] = useState("");
const handleTagKey = (e: KeyboardEvent) => {
  if (e.key === "Enter" || e.key === ",") {
    const t = tagInput.trim().replace(",", "");
    if (t && !tags.includes(t)) setTags(prev => [...prev, t]);
    setTagInput("");
  }
};
```

**Кнопки**:
- "Создать товар" → POST `/api/v1/products` (Dev2 делает эндпоинт)
- После успеха → показать `PromotionModal` с предложением купить продвижение

**Файл**: `frontend/src/api/client.ts` — добавить метод:
```typescript
createProduct(data: CreateProductRequest): Promise<CreateProductResponse>
```

### 4.3 Схема запроса
**Файл**: `backend/app/schemas.py` — добавить:
```python
class CreateProductRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=500)
    category: str | None = None
    tags: list[str] = []
    description: str | None = None
    user_id: str  # ID создавшего пользователя

class CreateProductResponse(BaseModel):
    id: int
    name: str
    tags: list[str]
    message: str  # "Товар создан успешно"
```

---

## Задача 5 — Модальное окно продвижения товара (Promotion Slider)

**Файл**: `frontend/src/components/PromotionModal.tsx` (новый)

### 5.1 Описание фичи
Аналог продвижения на Авито: ползунок дней → динамическая цена.
При активации — товар получает boost в поиске.

### 5.2 Компонент

```tsx
interface PromotionModalProps {
  productId: number;
  productName: string;
  onClose: () => void;
  onSuccess: () => void;
}
```

**Layout**:
```
┌─────────────────────────────────────────────┐
│  Продвижение товара                     [X]  │
│  "Айфон 17 Pro Max"                          │
│                                              │
│  Как работает продвижение:                   │
│  [i] Ваш товар появится выше конкурентов     │
│  [i] Работает даже при 0 заказах             │
│  [i] При равном продвижении — больше заказов │
│                                              │
│  Срок продвижения:                           │
│  1 день ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 30 дней │
│                       [7 дней]               │
│                                              │
│  Стоимость: 350 руб/день × 7 = 2 450 руб    │
│                                              │
│  [  Отмена  ]    [ Активировать продвижение ]│
└─────────────────────────────────────────────┘
```

**Логика цены**:
```typescript
const PRICE_PER_DAY = 350; // руб
const [days, setDays] = useState(7);
const totalPrice = days * PRICE_PER_DAY;
```

**При активации** → `POST /api/v1/products/{id}/promote` с `{ days }` (Dev2 эндпоинт).

---

## Задача 6 — Страница "Мои товары"

**Файл**: `frontend/src/components/MyProductsPanel.tsx` (новый)

### 6.1 Открытие
- В Header добавить таб/кнопку "Мои товары" — рядом с "Добавить товар".
- При клике — показывает панель справа (боковая slide-in панель).

### 6.2 Список товаров

Каждый элемент списка:
```
┌────────────────────────────────────────────────────┐
│ Айфон 17 Pro Max                     ID: 1234567   │
│ Категория: Мобильные телефоны                      │
│ Теги: #телефон #гаджет #техника                    │
│ Заказы: 0                                          │
│                                                    │
│ Продвижение: [● АКТИВНО до 11.04.2026]             │
│              или                                   │
│              [○ Не активно]  [Включить продвижение]│
└────────────────────────────────────────────────────┘
```

- Если продвижение активно — зелёный badge с датой окончания.
- Если не активно — серый badge + кнопка "Включить продвижение" → открывает `PromotionModal`.

**API**: `GET /api/v1/products?user_id={id}` (Dev2 делает эндпоинт).

**Файл**: `frontend/src/api/client.ts` — добавить:
```typescript
getMyProducts(userId: string): Promise<MyProduct[]>
activatePromotion(productId: number, days: number): Promise<{ promoted_until: string }>
```

### 6.3 Отображение "Продвигается" в карточке поиска
**Файл**: `frontend/src/components/STECard.tsx`
- Если `item.is_promoted === true` — добавить badge "Продвигается" оранжевым цветом:
  ```tsx
  {item.is_promoted && (
    <span style={{ background: "#FFF3E8", color: "#F67319", border: "1px solid #F67319",
                   borderRadius: 4, padding: "1px 6px", fontSize: 11, fontWeight: 600 }}>
      Продвигается
    </span>
  )}
  ```

---

## Обновления API-клиента (итог)

**Файл**: `frontend/src/api/client.ts`

Добавить в интерфейс `STEResult`:
```typescript
is_promoted?: boolean;
promotion_boost?: number | null;
tags?: string[];
```

Добавить методы:
```typescript
createProduct(data: CreateProductRequest): Promise<CreateProductResponse>
getMyProducts(userId: string): Promise<MyProduct[]>
activatePromotion(productId: number, days: number): Promise<{ promoted_until: string }>
```

---

## Файловая карта (итог)

```
frontend/src/
  components/
    STECard.tsx            — правки: убрать Сравнить, добавить ThumbsUp, brain-кнопку, promoted badge
    STEModal.tsx           — правки: Raw → Характеристики (таблица атрибутов)
    Header.tsx             — правки: кнопка "Добавить товар", таб "Мои товары"
    ThinkingModal.tsx      — НОВЫЙ: "Размышления поиска"
    CreateProductModal.tsx — НОВЫЙ: форма создания товара
    PromotionModal.tsx     — НОВЫЙ: слайдер продвижения
    MyProductsPanel.tsx    — НОВЫЙ: список своих товаров с управлением продвижением
  api/
    client.ts              — правки: новые методы + поля STEResult

backend/app/
  schemas.py               — правки: CreateProductRequest, CreateProductResponse, MyProduct
```

---

## Порядок выполнения (рекомендуемый)

1. Задача 1 (UI-чистка) — 20 мин
2. Задача 2 (ThumbsUp) — 30 мин
3. Задача 3 (ThinkingModal) — 60 мин
4. Задача 4 (CreateProductModal) — 45 мин
5. Задача 5 (PromotionModal) — 30 мин
6. Задача 6 (MyProductsPanel) — 45 мин

**Всего**: ~4 часа

## Важные заметки

- Не используй Tailwind классы — только inline styles (исторически сайт уже так написан).
- Новые компоненты: импортируй и подключай через App.tsx.
- Не трогай `backend/app/services/` — это зона Dev2.
- Пока Dev2 не сделал эндпоинты — используй моки: `const mockProducts: MyProduct[] = [...]`.
- `ThinkingModal` работает уже сейчас — данные из `STEResult.explanations` уже приходят с бэка.
