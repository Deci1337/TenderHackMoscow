# Dev 1 — Sprint 3: Frontend & UX

**Зона ответственности**: `frontend/src/**`
**Зона запрета**: не трогать `backend/app/services/**`, `backend/app/models.py`, `backend/scripts/**`
**Стек**: React 18 + TypeScript + Vite, inline styles, lucide-react
**Цвета**: `#264B82` (blue), `#DB2B21` (red), `#0D9B68` (green), `#F67319` (orange), `#1A1A1A` (black), `#8C8C8C` (gray), `#E7EEF7` (pale bg)

**API-контракт с Dev 2** (все эндпоинты Dev 2 реализует параллельно — используй моки до момента слияния):
- `GET /users/{inn}/interests` → `UserInterestSummary`
- `GET /users/{inn}/categories` → `string[]` (отфильтрованный список категорий для данного пользователя)
- `POST /search` response теперь содержит `rank_delta?: number` в каждом `STEResult`

---

## Задача 0 — Срочный баг: смена категории не обновляет товары

**Файл**: `frontend/src/App.tsx`, функция `selectCategory`

Текущая проблема: `setResponse(null)` сбрасывает стейт, но `doSearch` вызывается с устаревшим `query` до его обновления в стейте.

**Исправление**:
```tsx
function selectCategory(cat: string | null) {
  setCategory(cat);
  setOffset(0);
  setResponse(null);
  if (inputVal.trim()) doSearch(inputVal.trim(), 0, sortBy, cat);
  else if (query) doSearch(query, 0, sortBy, cat);
}
```

Причина: `query` — это последний выполненный поиск, `inputVal` — то, что сейчас в инпуте. При смене категории нужно перезапустить поиск по актуальному запросу. Также убедиться что `doSearch` в `useCallback` зависит от актуального `inputVal`.

---

## Задача 1 — Убрать онбординг (приветственный опрос)

**Файл**: `frontend/src/App.tsx`

Вместо показа `<Onboarding>` при отсутствии пользователя — сразу показывать `<DemoSelector>`.

### 1.1 Заменить компонент Onboarding на DemoSelector

Новый компонент `DemoSelector` (inline в App.tsx или в `components/DemoSelector.tsx`):

```tsx
const DEMO_USERS = [
  {
    id: "7701234567",
    label: "Школа №1234",
    // интересы определяются из истории контрактов — Dev 2 seed_demo.py
  },
  {
    id: "7709876543",
    label: "Городская больница №5",
  },
  {
    id: "7705551234",
    label: "СтройМонтаж ООО",
  },
];
```

UI: три карточки пользователей. При клике — `api.getUser(id)` чтобы получить профиль из БД (категории из контрактов). Никакого "выбора интересов" — интересы определяются системой автоматически.

```tsx
function DemoSelector({ onDone }: { onDone: (u: User) => void }) {
  async function pick(demo: typeof DEMO_USERS[number]) {
    const profile = await api.getUser(demo.id).catch(() => null);
    onDone({
      id: demo.id,
      label: demo.label,
      interests: profile?.top_categories ?? [],
    });
  }

  return (
    <div style={{ minHeight: "100vh", background: "#E7EEF7", display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div style={{ background: "#fff", borderRadius: 8, boxShadow: "0 4px 24px rgba(0,0,0,.12)", width: "100%", maxWidth: 400, overflow: "hidden" }}>
        <div style={{ background: "#264B82", padding: "20px 24px", color: "#fff" }}>
          <div style={{ fontWeight: 700, fontSize: 18 }}>Портал поставщиков</div>
          <div style={{ fontSize: 13, color: "#a3bfe0", marginTop: 4 }}>Выберите профиль для демонстрации</div>
        </div>
        <div style={{ padding: "16px 24px 24px", display: "flex", flexDirection: "column", gap: 8 }}>
          {DEMO_USERS.map(u => (
            <button key={u.id} onClick={() => pick(u)}
              style={{ padding: "14px 16px", borderRadius: 6, border: "1px solid #D4DBE6", background: "#fff", cursor: "pointer", textAlign: "left" }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = "#264B82")}
              onMouseLeave={e => (e.currentTarget.style.borderColor = "#D4DBE6")}
            >
              <div style={{ fontWeight: 600, fontSize: 14, color: "#1A1A1A" }}>{u.label}</div>
              <div style={{ fontSize: 12, color: "#8C8C8C", marginTop: 2 }}>Профиль по истории закупок</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
```

### 1.2 Обновить App.tsx

```tsx
if (!user) return <DemoSelector onDone={login} />;
```

Удалить весь компонент `Onboarding` и константу `INTEREST_OPTIONS`.

---

## Задача 2 — Убрать монетизацию из UI

**Файлы**: `frontend/src/App.tsx`, `frontend/src/api/client.ts`

### 2.1 Из Header удалить кнопки
Убрать полностью:
- Кнопку `<Package> Мои товары`
- Кнопку `<Plus> Добавить товар`

### 2.2 Из стейта App убрать
Удалить состояния: `showCreateProduct`, `showMyProducts`, `promotingProduct`, `myProducts`
Удалить `useEffect` с `api.getMyProducts`.

### 2.3 Из STECard убрать
Убрать badge "Продвигается" (там где рендерится `item.is_promoted`).
Убрать отображение `promotion_boost`.

### 2.4 Из ThinkingModal (если он есть) убрать секцию продвижения
Убрать блок "Товар имеет активное продвижение".

### 2.5 Из client.ts убрать (или оставить, но не использовать)
Можно просто удалить методы `createProduct`, `getMyProducts`, `activatePromotion`.
Удалить интерфейсы `CreateProductRequest`, `MyProduct`, `PromoteRequest`.

---

## Задача 3 — Правая панель: "Профиль интересов пользователя"

Ключевая фича для жюри: показать как система отслеживает поведение пользователя в реальном времени.

**Новый файл**: `frontend/src/components/InterestPanel.tsx`

### 3.1 Интерфейс данных

```typescript
// В client.ts добавить:
export interface CategoryInterest {
  category: string;
  click_count: number;        // кол-во кликов за сессию
  contract_count: number;     // кол-во исторических контрактов
  weight: number;             // итоговый вес 0..1
  trend: "rising" | "stable" | "fading";  // тренд интереса
  last_interaction_days: number;  // дней с последнего взаимодействия
}

export interface UserInterestSummary {
  inn: string;
  label: string;
  top_categories: CategoryInterest[];
  session_clicks_total: number;
  recent_query: string | null;
  active_interests: string[];   // категории с weight > 0.3
  fading_interests: string[];   // категории, не интересовавшие >14 дней
  last_updated: string;
}
```

Мок до слияния с Dev 2:
```typescript
const MOCK_INTERESTS: UserInterestSummary = {
  inn: "7701234567",
  label: "Школа №1234",
  top_categories: [
    { category: "Канцелярские товары", click_count: 8, contract_count: 45, weight: 0.72, trend: "rising", last_interaction_days: 0 },
    { category: "Мебель офисная", click_count: 3, contract_count: 20, weight: 0.45, trend: "stable", last_interaction_days: 2 },
    { category: "IT-оборудование", click_count: 1, contract_count: 12, weight: 0.28, trend: "fading", last_interaction_days: 18 },
  ],
  session_clicks_total: 12,
  recent_query: "ручка гелевая",
  active_interests: ["Канцелярские товары", "Мебель офисная"],
  fading_interests: ["IT-оборудование"],
  last_updated: new Date().toISOString(),
};
```

### 3.2 Компонент InterestPanel

```tsx
interface InterestPanelProps {
  userInn: string;
  userLabel: string;
  lastQuery: string;
  sessionClicks: Array<{ steId: number; category: string; name: string }>;
  onClose: () => void;
}
```

**Layout панели** (фиксированная справа, ширина 320px):

```
┌──────────────────────────────────────────┐
│ Профиль интересов              [×]        │
│ Школа №1234  · ИНН 7701234567            │
├──────────────────────────────────────────┤
│ ТЕКУЩАЯ СЕССИЯ                           │
│ Запросов: 5   Кликов: 12                 │
│ Последний запрос: "ручка гелевая"        │
├──────────────────────────────────────────┤
│ КАК СИСТЕМА ПОНИМАЕТ ИНТЕРЕСЫ            │
│                                          │
│ Канцелярские товары     ████████░░ 72%   │
│   8 кликов + 45 контрактов               │
│   Тренд: растет ↑                        │
│                                          │
│ Мебель офисная          █████░░░░░ 45%   │
│   3 клика + 20 контрактов                │
│   Тренд: стабильно →                     │
│                                          │
│ IT-оборудование         ███░░░░░░░ 28%   │
│   Не интересовались 18 дней              │
│   Тренд: угасает ↓ (снижается приоритет) │
├──────────────────────────────────────────┤
│ ВЫВОД СИСТЕМЫ                            │
│ По запросу "ручка" система показывает    │
│ ручку гелевую (канцелярия), т.к. эта     │
│ категория активнее всего сейчас          │
└──────────────────────────────────────────┘
```

**Реализация**:
```tsx
export function InterestPanel({ userInn, userLabel, lastQuery, sessionClicks, onClose }: InterestPanelProps) {
  const [data, setData] = useState<UserInterestSummary | null>(null);

  useEffect(() => {
    api.getUserInterests(userInn).then(setData).catch(() => setData(MOCK_INTERESTS));
  }, [userInn, sessionClicks.length]); // обновляем после каждого нового клика

  if (!data) return null;

  const trendIcon = (t: string) => t === "rising" ? "↑" : t === "fading" ? "↓" : "→";
  const trendColor = (t: string) => t === "rising" ? "#0D9B68" : t === "fading" ? "#DB2B21" : "#8C8C8C";

  return (
    <div style={{
      position: "fixed", right: 0, top: 0, bottom: 0, width: 320,
      background: "#fff", boxShadow: "-4px 0 24px rgba(0,0,0,.12)",
      zIndex: 200, overflowY: "auto", display: "flex", flexDirection: "column",
    }}>
      {/* header */}
      <div style={{ background: "#264B82", color: "#fff", padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>Профиль интересов</div>
          <div style={{ fontSize: 11, color: "#a3bfe0", marginTop: 2 }}>{userLabel}</div>
        </div>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "#fff", cursor: "pointer", fontSize: 18 }}>×</button>
      </div>

      {/* session stats */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid #E7EEF7", background: "#F8FAFE" }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }}>Текущая сессия</div>
        <div style={{ display: "flex", gap: 16, fontSize: 13 }}>
          <span><b>{sessionClicks.length}</b> кликов</span>
          {lastQuery && <span>Запрос: <b>"{lastQuery}"</b></span>}
        </div>
      </div>

      {/* categories */}
      <div style={{ padding: "12px 16px", flex: 1 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 12 }}>Как система понимает интересы</div>
        {data.top_categories.map(cat => (
          <div key={cat.category} style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A" }}>{cat.category}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: "#264B82" }}>{Math.round(cat.weight * 100)}%</span>
            </div>
            {/* progress bar */}
            <div style={{ height: 6, background: "#E7EEF7", borderRadius: 3, marginBottom: 4 }}>
              <div style={{ height: "100%", width: `${cat.weight * 100}%`, background: cat.trend === "fading" ? "#F67319" : "#264B82", borderRadius: 3, transition: "width .5s" }} />
            </div>
            <div style={{ fontSize: 11, color: "#8C8C8C" }}>
              {cat.click_count > 0 && `${cat.click_count} кликов в сессии · `}
              {cat.contract_count} контрактов
            </div>
            <div style={{ fontSize: 11, color: trendColor(cat.trend), marginTop: 2 }}>
              {trendIcon(cat.trend)} {cat.trend === "rising" ? "Интерес растёт" : cat.trend === "fading" ? `Не интересовались ${cat.last_interaction_days} дн. — приоритет снижается` : "Стабильный интерес"}
            </div>
          </div>
        ))}
      </div>

      {/* system conclusion */}
      {lastQuery && data.active_interests.length > 0 && (
        <div style={{ padding: "12px 16px", background: "#E6F7F1", borderTop: "1px solid #B2DFD0" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#0D9B68", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 6 }}>Вывод системы</div>
          <div style={{ fontSize: 12, color: "#1A1A1A", lineHeight: 1.5 }}>
            По запросу <b>"{lastQuery}"</b> система приоритизирует категорию <b>{data.active_interests[0]}</b> — она наиболее активна в текущей сессии.
          </div>
        </div>
      )}
    </div>
  );
}
```

### 3.3 Кнопка открытия панели

В App.tsx в шапке добавить кнопку "Профиль интересов" с иконкой `Brain`:
```tsx
<button onClick={() => setShowInterestPanel(true)}
  style={{ background: "rgba(255,255,255,.15)", border: "none", color: "#fff", padding: "4px 10px", borderRadius: 4, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}>
  <Brain size={13} /> Интересы
</button>
```

### 3.4 Отслеживание кликов по товарам в sessionClicks

В App.tsx добавить стейт:
```tsx
const [sessionClicks, setSessionClicks] = useState<Array<{ steId: number; category: string; name: string }>>([]);
```

В `trackAction` при `action === "click"` добавлять в `sessionClicks`.

---

## Задача 4 — AI Reasoning Panel (простым языком)

Переработка существующей `ThinkingModal` / компонента объяснения.

**Файл**: `frontend/src/components/ThinkingModal.tsx` (или создать заново)

### 4.1 Принцип "язык бизнеса"

**Было** (технический язык):
```
BM25 score: 0.847
semantic_similarity: 0.612
catboost_rank_delta: +0.23
```

**Стало** (язык бизнеса):
```
Почему этот товар на #2?

Точное совпадение с запросом       ████████████  Сильный сигнал
Этот пользователь покупал это 5 раз ████████░░░░  Из истории закупок
Популярен среди похожих покупателей ██████░░░░░░  Социальный сигнал
Редко не подходил другим           ████░░░░░░░░  Качество товара
```

### 4.2 Функция перевода факторов

```typescript
function humanReadableFactor(factor: string, reason: string, weight: number): string {
  const map: Record<string, string> = {
    "history":     "Пользователь закупал похожие товары",
    "category":    "Совпадает с интересующей категорией",
    "session":     "Проявлен интерес в текущей сессии",
    "negative":    "Снижен — пользователь отметил как нерелевантный",
    "bm25":        "Точное совпадение слов в названии",
    "semantic":    "Похож по смыслу на запрос",
    "popularity":  "Часто заказывают другие покупатели",
    "catboost":    "Модель ML оценила как подходящий",
  };
  return map[factor] ?? reason;
}
```

### 4.3 Секция "Как система исправила запрос"

Показывать только если `was_corrected` или `applied_synonyms.length > 0`:
```tsx
<div style={{ padding: 12, background: "#FEF3EB", borderRadius: 6, fontSize: 12, marginBottom: 12 }}>
  <b>Система скорректировала запрос:</b>
  {was_corrected && <div>Исправила опечатку: "{originalQuery}" → "{correctedQuery}"</div>}
  {synonyms.length > 0 && <div>Расширила синонимами: {synonyms.join(", ")}</div>}
  {userContext && <div>Учла контекст: пользователь из сферы "{userContext}" — значит "ручка" → ручка гелевая</div>}
</div>
```

### 4.4 Layout ThinkingModal

```
┌──────────────────────────────────────────────────────┐
│  Почему товар на позиции #2?                    [×]   │
│  "Ручка гелевая синяя 0.5мм"                         │
├──────────────────────────────────────────────────────┤
│  КАК СИСТЕМА ПОНИМАЛА ЗАПРОС                         │
│  Исходный запрос:  "ручка"                           │
│  Исправление:      нет опечаток                      │
│  Уточнение:        пользователь — школа →            │
│                    "ручка" = письменная принадлежность│
│  Использованы синонимы: ручка шариковая, карандаш    │
├──────────────────────────────────────────────────────┤
│  ФАКТОРЫ ПОЗИЦИИ                                     │
│  Точное совпадение с запросом      ████████████ +0.8 │
│  Интерес к канцелярии (8 кликов)   █████████░░░ +0.6 │
│  45 прошлых контрактов (закупки)   ███████░░░░░ +0.4 │
│  Популярен (12 закупок в регионе)  █████░░░░░░░ +0.3 │
└──────────────────────────────────────────────────────┘
```

---

## Задача 5 — Фильтр категорий: переключатель "Интересные / Все"

**Файл**: `frontend/src/App.tsx` (секция категорий), `frontend/src/components/FilterPanel.tsx`

### 5.1 Логика

- По умолчанию переключатель "Интересные" = ON → показываем только категории из `user.interests` (+ категории из контрактов, которые вернёт `GET /users/{inn}/categories`)
- Переключить в "Все" → показать все `facets`
- Когда "Интересные" ON — передавать в поиск флаг или фильтровать локально результаты

### 5.2 Состояние и UI

В App.tsx:
```tsx
const [onlyInteresting, setOnlyInteresting] = useState(true);
const [userCategories, setUserCategories] = useState<string[]>([]);

useEffect(() => {
  api.getUserCategories(user.id).then(setUserCategories).catch(() => {
    setUserCategories(user.interests); // fallback
  });
}, [user.id]);

const visibleFacets = onlyInteresting
  ? facets.filter(f => userCategories.includes(f.name))
  : facets;
```

Переключатель над списком категорий:
```tsx
<div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
  <span style={{ fontSize: 12, color: "#8C8C8C" }}>Категории:</span>
  <button onClick={() => setOnlyInteresting(!onlyInteresting)}
    style={{
      padding: "3px 10px", borderRadius: 20, fontSize: 11, border: "1px solid",
      cursor: "pointer",
      borderColor: onlyInteresting ? "#264B82" : "#D4DBE6",
      background: onlyInteresting ? "#264B82" : "#fff",
      color: onlyInteresting ? "#fff" : "#8C8C8C",
    }}>
    {onlyInteresting ? "Только интересные" : "Все категории"}
  </button>
</div>
```

### 5.3 Фильтрация товаров при "Интересные"

Когда `onlyInteresting` ON и нет активного фильтра по конкретной категории — в запрос поиска передавать `interests: userCategories`. Это уже поддерживается бэкендом.

---

## Задача 6 — Стрелки изменения позиции после реакции

**Файлы**: `frontend/src/App.tsx`, `frontend/src/components/STECard.tsx`

### 6.1 Механика

1. После получения результатов поиска сохранять маппинг `{ste_id -> position}` в стейте.
2. После лайка/дизлайка — перезапустить поиск через 1.5 секунды (чтобы сессионные бусты применились).
3. Сравнить новые позиции со старыми → вычислить `rank_delta`.
4. Показывать дельту на карточке в течение 5 секунд.

### 6.2 Стейт в App.tsx

```tsx
const [prevPositions, setPrevPositions] = useState<Record<number, number>>({});
const [rankDeltas, setRankDeltas] = useState<Record<number, number>>({}); // ste_id -> delta

// При получении новых результатов:
useEffect(() => {
  if (!response) return;
  const newPositions: Record<number, number> = {};
  response.results.forEach((r, i) => { newPositions[r.id] = i + 1; });

  // Вычислить дельты относительно предыдущих позиций
  const deltas: Record<number, number> = {};
  response.results.forEach((r, i) => {
    const prev = prevPositions[r.id];
    if (prev !== undefined) deltas[r.id] = prev - (i + 1); // положительное = вырос
  });
  setRankDeltas(deltas);
  setPrevPositions(newPositions);

  // Через 5 секунд скрыть стрелки
  const timer = setTimeout(() => setRankDeltas({}), 5000);
  return () => clearTimeout(timer);
}, [response]);
```

### 6.3 После лайка/дизлайка — отложенный перезапуск

```tsx
function handleLike(steId: number, cat?: string) {
  setLikedIds(prev => { const s = new Set(prev); s.add(steId); return s; });
  setDislikedIds(prev => { const s = new Set(prev); s.delete(steId); return s; });
  trackAction(steId, "like", cat);
  showToast("Оценено — пересчитываем позиции...");
  setTimeout(() => doSearch(query, offset), 1500);
}

function handleDislike(steId: number, cat?: string) {
  setDislikedIds(prev => { const s = new Set(prev); s.add(steId); return s; });
  setLikedIds(prev => { const s = new Set(prev); s.delete(steId); return s; });
  trackAction(steId, "dislike", cat);
  showToast("Отмечено — пересчитываем позиции...");
  setTimeout(() => doSearch(query, offset), 1500);
}
```

### 6.4 Отображение дельты в STECard

Добавить проп `rankDelta?: number` в STECard:
```tsx
{rankDelta !== undefined && rankDelta !== 0 && (
  <span style={{
    display: "inline-flex", alignItems: "center", gap: 2,
    color: rankDelta > 0 ? "#0D9B68" : "#DB2B21",
    fontSize: 11, fontWeight: 700, padding: "2px 6px",
    background: rankDelta > 0 ? "#E6F7F1" : "#FDECEA",
    borderRadius: 4, marginLeft: 6,
  }}>
    {rankDelta > 0 ? "↑" : "↓"} {Math.abs(rankDelta)}
  </span>
)}
```

---

## Задача 7 — Обновить demo-пользователей в App.tsx

**Файл**: `frontend/src/App.tsx`

Убрать приписанные интересы из `DEMO_USERS` — теперь они берутся из БД через `api.getUser()`.

```tsx
const DEMO_USERS = [
  { id: "7701234567", label: "Школа №1234" },
  { id: "7709876543", label: "Городская больница №5" },
  { id: "7705551234", label: "СтройМонтаж ООО" },
];
```

---

## Новые методы в client.ts

```typescript
// Получить сводку интересов пользователя для панели
getUserInterests(inn: string): Promise<UserInterestSummary> {
  return request<UserInterestSummary>(`/users/${inn}/interests`);
},

// Получить отфильтрованный список категорий для пользователя
getUserCategories(inn: string): Promise<string[]> {
  return request<string[]>(`/users/${inn}/categories`);
},
```

---

## Файловая карта (итог)

```
frontend/src/
  App.tsx                       — убрать Onboarding, продвижение, починить selectCategory,
                                  добавить InterestPanel, rankDeltas, sessionClicks
  api/client.ts                 — добавить getUserInterests, getUserCategories;
                                  удалить createProduct, getMyProducts, activatePromotion
  components/
    DemoSelector.tsx             — НОВЫЙ (или inline): выбор демо-пользователя
    InterestPanel.tsx            — НОВЫЙ: правая панель интересов пользователя
    ThinkingModal.tsx            — ПЕРЕРАБОТАТЬ: язык бизнеса, разделы NLP + факторы
    STECard.tsx                  — добавить rankDelta стрелку; убрать is_promoted badge
    FilterPanel.tsx              — добавить переключатель "Интересные / Все"
```

---

## Порядок выполнения

| # | Задача | Время | Блокирует |
|---|--------|-------|-----------|
| 0 | Баг с категориями | 10 мин | ничего |
| 1 | Убрать онбординг | 20 мин | ничего |
| 2 | Убрать монетизацию | 15 мин | ничего |
| 3 | InterestPanel | 90 мин | Dev 2 `GET /users/{inn}/interests` |
| 4 | ThinkingModal переработка | 60 мин | ничего |
| 5 | Фильтр категорий | 45 мин | Dev 2 `GET /users/{inn}/categories` |
| 6 | Стрелки позиций | 40 мин | ничего |
| 7 | Demo-пользователи | 10 мин | Dev 2 seed_demo |

**Итого**: ~5 часов. Задачи 0, 1, 2, 4, 6 не зависят от Dev 2 — стартовать с них.

## Правила

- Только inline styles, никакого Tailwind
- Не трогать `backend/app/services/**`
- Пока Dev 2 не сдал эндпоинты — использовать моки из этого документа
- Все новые компоненты подключать через `App.tsx`
