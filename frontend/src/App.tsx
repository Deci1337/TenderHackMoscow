import {
  useCallback, useEffect, useRef, useState,
  type CSSProperties, type ReactNode,
} from "react";
import { api, STEResult, SearchResponse, CategoryFacet } from "./api/client";
import {
  Search, LogOut, ChevronRight, ChevronDown, Loader2, PackageSearch,
  ThumbsDown, ThumbsUp, X, SlidersHorizontal, ArrowUpDown, Brain,
} from "lucide-react";
import { InterestPanel } from "./components/InterestPanel";

const PAGE_SIZE = 20;
const POPULAR = ["бумага офисная", "картридж", "компьютер", "стул офисный", "маска медицинская"];
const SORT_OPTIONS = [
  { value: "relevance", label: "По релевантности" },
  { value: "name", label: "По названию" },
  { value: "popularity", label: "По популярности" },
] as const;
const BADGE_STYLES: Record<string, CSSProperties> = {
  history: { background: "#E6F7F1", color: "#0D9B68" },
  category: { background: "#E5F4F5", color: "#167C85" },
  session: { background: "#FEF3EB", color: "#F67319" },
  negative: { background: "#FDECEA", color: "#DB2B21" },
};

interface User { id: string; label: string; interests: string[] }

export default function App() {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const s = localStorage.getItem("portal_user");
      return s ? JSON.parse(s) : null;
    } catch { return null; }
  });

  function login(u: User) {
    localStorage.setItem("portal_user", JSON.stringify(u));
    setUser(u);
  }
  function logout() {
    localStorage.removeItem("portal_user");
    setUser(null);
  }

  if (!user) return <DemoSelector onDone={login} />;
  return <Main user={user} onLogout={logout} />;
}

interface DemoProfile {
  id: string;
  label: string;
  industry: string;
  description: string;
  categories: string[];
  contracts: number;
  isNew?: boolean;
}

const DEMO_PROFILES_BASE: Omit<DemoProfile, "categories" | "contracts">[] = [
  { id: "7701234567", label: "Школа №1234",           industry: "Образование",   description: "Категории определены по истории закупок и отрасли" },
  { id: "7709876543", label: "Городская больница №5", industry: "Медицина",      description: "Категории определены по истории закупок и отрасли" },
  { id: "7705551234", label: "СтройМонтаж ООО",       industry: "Строительство", description: "Категории определены по истории закупок и отрасли" },
];

/* ===================  DEMO SELECTOR  =================== */
const INDUSTRY_ICONS: Record<string, string> = {
  "Образование": "📚", "Медицина": "🏥", "Строительство": "🏗️", "Не определена": "👤",
};

function DemoSelector({ onDone }: { onDone: (u: User) => void }) {
  const profiles: DemoProfile[] = [
    ...DEMO_PROFILES_BASE.map(p => ({ ...p, categories: [], contracts: 0 })),
    { id: `new_${Date.now()}`, label: "Новый пользователь", industry: "Не определена",
      description: "Чистый профиль — интересы сформируются по вашим действиям",
      categories: [], contracts: 0, isNew: true },
  ];

  function pick(demo: DemoProfile) {
    onDone({
      id: demo.isNew ? `new_${Date.now()}` : demo.id,
      label: demo.label,
      interests: [],
    });
  }

  return (
    <div style={{ minHeight: "100vh", background: "#E7EEF7", display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div style={{ background: "#fff", borderRadius: 8, boxShadow: "0 4px 24px rgba(0,0,0,.12)", width: "100%", maxWidth: 460, overflow: "hidden" }}>
        <div style={{ background: "#264B82", padding: "20px 24px", color: "#fff" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <div style={{ width: 28, height: 28, background: "#fff", borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center", color: "#264B82", fontWeight: 900, fontSize: 12 }}>П</div>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Портал поставщиков</span>
          </div>
          <div style={{ fontWeight: 700, fontSize: 18 }}>Умный поиск СТЕ</div>
          <div style={{ fontSize: 13, color: "#a3bfe0", marginTop: 4 }}>
            Система определяет интересы по истории закупок и поведению
          </div>
        </div>
        <div style={{ padding: "16px 24px 24px", display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 2 }}>Выберите профиль для демонстрации</div>
          {profiles.map(u => (
            <button key={u.id} onClick={() => pick(u)}
              style={{
                padding: "12px 14px", borderRadius: 6, textAlign: "left",
                border: u.isNew ? "1px dashed #D4DBE6" : "1px solid #D4DBE6",
                background: u.isNew ? "#F8FAFE" : "#fff", cursor: "pointer",
              }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = "#264B82")}
              onMouseLeave={e => (e.currentTarget.style.borderColor = "#D4DBE6")}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 18 }}>{INDUSTRY_ICONS[u.industry] ?? "🏢"}</span>
                <div>
                  <span style={{ fontWeight: 700, fontSize: 14, color: "#1A1A1A" }}>{u.label}</span>
                  {!u.isNew && (
                    <span style={{ fontSize: 10, background: "#E7EEF7", color: "#264B82", borderRadius: 3, padding: "1px 6px", fontWeight: 600, marginLeft: 6 }}>{u.industry}</span>
                  )}
                  <div style={{ fontSize: 12, color: "#8C8C8C", marginTop: 2 }}>{u.description}</div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ===================  MAIN  =================== */
function parseRawAttrs(raw: string): Record<string, string> {
  return Object.fromEntries(
    raw.split(";")
      .map(p => { const i = p.indexOf(":"); return i > 0 ? [p.slice(0, i).trim(), p.slice(i + 1).trim()] : null; })
      .filter((p): p is [string, string] => p !== null && p[1] !== "")
  );
}

function Main({ user: initialUser, onLogout }: { user: User; onLogout: () => void }) {
  const [user, setUser] = useState(initialUser);
  const [query, setQuery] = useState("");
  const [inputVal, setInputVal] = useState("");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [modalItem, setModalItem] = useState<STEResult | null>(null);
  const [thinkingItem, setThinkingItem] = useState<{ item: STEResult; position: number } | null>(null);
  const [sortBy, setSortBy] = useState("relevance");
  const [category, setCategory] = useState<string | null>(null);
  const [facets, setFacets] = useState<CategoryFacet[]>([]);
  const [showFilters, setShowFilters] = useState(true);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [likedIds, setLikedIds] = useState<Set<number>>(new Set());
  const [dislikedIds, setDislikedIds] = useState<Set<number>>(new Set());
  const [toast, setToast] = useState<string | null>(null);
  const [history] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem("sh") || "[]"); } catch { return []; }
  });
  const [sessionId] = useState(() => `s_${Date.now()}`);

  // Sprint 3: interest tracking panel
  const [showInterestPanel, setShowInterestPanel] = useState(false);
  const [sessionClicks, setSessionClicks] = useState<Array<{ steId: number; category: string; name: string }>>([]);

  // Sprint 3: category interest filter (starts false until user data arrives)
  const [onlyInteresting, setOnlyInteresting] = useState(false);
  const [userCategoryFacets, setUserCategoryFacets] = useState<CategoryFacet[]>([]);

  // Sprint 3: rank delta arrows (use ref to avoid infinite effect loop)
  const prevPositionsRef = useRef<Record<number, number>>({});
  const [rankDeltas, setRankDeltas] = useState<Record<number, number>>({});

  const suggestTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    Promise.all([
      api.facets().catch(() => ({ categories: [] as CategoryFacet[] })),
      api.getUserCategories(user.id).catch(() => [] as CategoryFacet[]),
    ]).then(([facetsResp, userCats]) => {
      setFacets(facetsResp.categories);
      if (userCats.length > 0) {
        setUserCategoryFacets(userCats);
        setOnlyInteresting(true);
        setUser(prev => ({ ...prev, interests: userCats.map(c => c.name) }));
      }
    });
  }, [user.id]);

  useEffect(() => {
    function handle(e: MouseEvent) {
      if (suggestRef.current && !suggestRef.current.contains(e.target as Node) && e.target !== inputRef.current) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  // Compute rank deltas when results change
  useEffect(() => {
    if (!response) return;
    const newPositions: Record<number, number> = {};
    response.results.forEach((r, i) => { newPositions[r.id] = i + 1; });

    const deltas: Record<number, number> = {};
    response.results.forEach((r, i) => {
      const prev = prevPositionsRef.current[r.id];
      if (prev !== undefined) deltas[r.id] = prev - (i + 1);
    });
    prevPositionsRef.current = newPositions;

    if (Object.values(deltas).some(d => d !== 0)) {
      setRankDeltas(deltas);
      const timer = setTimeout(() => setRankDeltas({}), 5000);
      return () => clearTimeout(timer);
    }
  }, [response]);

  const visibleFacets: CategoryFacet[] = onlyInteresting && userCategoryFacets.length > 0
    ? userCategoryFacets.sort((a, b) => b.count - a.count)
    : facets;

  const doSearch = useCallback(async (q: string, off = 0, sort = sortBy, cat = category) => {
    if (!q.trim() && !cat) return;
    const searchQuery = q.trim() || "*";
    setQuery(searchQuery); setOffset(off); setLoading(true); setShowSuggestions(false);
    if (searchQuery !== "*") {
      const h = [searchQuery, ...history.filter(x => x !== searchQuery)].slice(0, 8);
      localStorage.setItem("sh", JSON.stringify(h));
    }
    try {
      const data = await api.search(searchQuery, user.id, sessionId, PAGE_SIZE, off, sort, cat || undefined, user.interests);
      setResponse(data);
      // Boost categories found in search results (lightweight interest signal)
      if (data.results.length > 0 && searchQuery !== "*") {
        const cats = new Set(data.results.map(r => r.category).filter(Boolean) as string[]);
        cats.forEach(c => boostCategory(c, 0.5));
      }
    } catch (err: unknown) {
      const isTimeout = err instanceof DOMException && err.name === "AbortError";
      if (isTimeout) {
        setResponse({ query: searchQuery, corrected_query: null, did_you_mean: null, total: -1, results: [] });
      } else {
        setResponse({ query: searchQuery, corrected_query: null, did_you_mean: null, total: 0, results: [] });
      }
    } finally { setLoading(false); }
  }, [user.id, sessionId, sortBy, category, history, user.interests]);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  function boostCategory(cat: string, _amount: number) {
    setUserCategoryFacets(prev => {
      const idx = prev.findIndex(f => f.name === cat);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = { ...updated[idx], count: updated[idx].count + 1 };
        return updated;
      }
      return [...prev, { name: cat, count: 1 }];
    });
  }

  function trackAction(steId: number, action: string, cat?: string) {
    const meta: Record<string, unknown> = {};
    if (cat) meta.category = cat;
    api.logEvent(user.id, steId, action, sessionId, query, meta).catch(() => {});
    if (cat) {
      const boost = action === "click" ? 3 : action === "like" ? 2 : 1;
      boostCategory(cat, boost);
    }
    if (action === "click" && cat) {
      const item = response?.results.find(r => r.id === steId);
      if (item) setSessionClicks(prev => [...prev, { steId, category: cat, name: item.name }]);
    }
  }

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

  function onInputChange(val: string) {
    setInputVal(val);
    clearTimeout(suggestTimer.current);
    if (val.trim().length < 2) { setSuggestions([]); setShowSuggestions(false); return; }
    suggestTimer.current = setTimeout(() => {
      api.suggest(val.trim()).then(r => { setSuggestions(r.suggestions); setShowSuggestions(r.suggestions.length > 0); }).catch(() => {});
    }, 200);
  }

  function selectCategory(cat: string | null) {
    setCategory(cat);
    setOffset(0);
    setResponse(null);
    if (cat) boostCategory(cat, 1);
    const q = inputVal.trim() || query || (cat ? "*" : "");
    if (q) doSearch(q, 0, sortBy, cat);
  }

  function selectSort(s: string) {
    setSortBy(s);
    if (query) doSearch(query, 0, s, category);
  }

  function pickSuggestion(s: string) {
    setInputVal(s);
    setShowSuggestions(false);
    doSearch(s);
  }

  return (
    <div style={{ minHeight: "100vh", background: "#E7EEF7" }}>
      {/* HEADER */}
      <header style={{ background: "#264B82", color: "#fff" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 16px", height: 48, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 24, height: 24, background: "#fff", borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center", color: "#264B82", fontWeight: 900, fontSize: 10 }}>П</div>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Портал поставщиков</span>
            <span style={{ color: "#a3bfe0", fontSize: 12, marginLeft: 4 }}>/ Умный поиск</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button onClick={() => setShowInterestPanel(v => !v)}
              style={{ background: showInterestPanel ? "rgba(255,255,255,.3)" : "rgba(255,255,255,.15)", border: "none", color: "#fff", padding: "4px 10px", borderRadius: 4, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}>
              <Brain size={13} /> Интересы
            </button>
            <button onClick={onLogout} style={{ background: "rgba(255,255,255,.15)", border: "none", color: "#fff", padding: "4px 12px", borderRadius: 4, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
              {user.label} <LogOut size={14} />
            </button>
          </div>
        </div>
      </header>

      {/* SEARCH BAR */}
      <div style={{ background: "#fff", borderBottom: "1px solid #D4DBE6" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "16px 16px 12px" }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 12 }}>
            <div>
              <h1 style={{ fontSize: 18, fontWeight: 700, color: "#1A1A1A", margin: 0 }}>Каталог товаров СТЕ</h1>
              {user.interests.length > 0 && (
                <p style={{ fontSize: 13, color: "#8C8C8C", margin: "2px 0 0" }}>{user.interests.slice(0, 3).join(" · ")}</p>
              )}
            </div>
            {response && <span style={{ fontSize: 12, color: "#8C8C8C" }}>Найдено: <strong style={{ color: "#1A1A1A" }}>{response.total}</strong></span>}
          </div>
          <form onSubmit={e => { e.preventDefault(); doSearch(inputVal); }} style={{ display: "flex", gap: 8 }}>
            <div style={{ flex: 1, position: "relative" }}>
              <Search size={16} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#8C8C8C", pointerEvents: "none" }} />
              <input ref={inputRef} value={inputVal} onChange={e => onInputChange(e.target.value)} placeholder="Поиск по каталогу СТЕ..."
                onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true); }}
                style={{ width: "100%", padding: "10px 36px", border: "2px solid #D4DBE6", borderRadius: 6, fontSize: 14, outline: "none", boxSizing: "border-box" }}
              />
              {inputVal && (
                <button type="button" onClick={() => { setInputVal(""); setSuggestions([]); }}
                  style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "#8C8C8C" }}>
                  <X size={16} />
                </button>
              )}
              {showSuggestions && (
                <div ref={suggestRef} style={{ position: "absolute", top: "100%", left: 0, right: 0, background: "#fff", border: "1px solid #D4DBE6", borderTop: "none", borderRadius: "0 0 6px 6px", zIndex: 50, boxShadow: "0 4px 12px rgba(0,0,0,.08)", maxHeight: 240, overflow: "auto" }}>
                  {suggestions.map((s, i) => (
                    <button key={i} type="button" onClick={() => pickSuggestion(s)}
                      style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px", border: "none", background: "transparent", cursor: "pointer", fontSize: 14, color: "#1A1A1A" }}
                      onMouseEnter={e => (e.currentTarget.style.background = "#E7EEF7")}
                      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                    >
                      <Search size={12} style={{ marginRight: 8, color: "#8C8C8C", verticalAlign: "middle" }} />
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button type="submit" style={{ padding: "0 20px", background: "#264B82", color: "#fff", border: "none", borderRadius: 6, fontWeight: 600, fontSize: 14, cursor: "pointer", whiteSpace: "nowrap" }}>Найти</button>
          </form>
          {response?.corrected_query && (
            <p style={{ marginTop: 8, fontSize: 13, color: "#F67319" }}>Исправлено: показаны результаты по запросу <strong>«{response.corrected_query}»</strong></p>
          )}
          {response?.did_you_mean && (
            <p style={{ marginTop: 4, fontSize: 12, color: "#167C85", background: "#E5F4F5", display: "inline-block", padding: "4px 10px", borderRadius: 4 }}>{response.did_you_mean}</p>
          )}
        </div>
      </div>

      {/* BODY: sidebar + results */}
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "16px 16px", display: "flex", gap: 16, alignItems: "flex-start" }}>
        {/* SIDEBAR */}
        <aside style={{ width: 220, flexShrink: 0, background: "#fff", border: "1px solid #D4DBE6", borderRadius: 6, overflow: "hidden", position: "sticky", top: 16 }}>
          <button onClick={() => setShowFilters(!showFilters)}
            style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", padding: "12px 14px", border: "none", background: "transparent", cursor: "pointer", fontSize: 13, fontWeight: 700, color: "#1A1A1A" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}><SlidersHorizontal size={14} /> Фильтры</span>
            <ChevronDown size={14} style={{ transform: showFilters ? "rotate(180deg)" : "none", transition: "transform .2s" }} />
          </button>
          {showFilters && (
            <div style={{ padding: "0 14px 14px" }}>
              {/* Sort */}
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: "#8C8C8C", textTransform: "uppercase", marginBottom: 6, display: "flex", alignItems: "center", gap: 4 }}><ArrowUpDown size={11} /> Сортировка</div>
                {SORT_OPTIONS.map(o => (
                  <button key={o.value} onClick={() => selectSort(o.value)}
                    style={{ display: "block", width: "100%", textAlign: "left", padding: "5px 10px", border: "none", borderRadius: 3, cursor: "pointer", fontSize: 13, marginBottom: 2,
                      background: sortBy === o.value ? "#264B82" : "transparent",
                      color: sortBy === o.value ? "#fff" : "#1A1A1A" }}
                    onMouseEnter={e => { if (sortBy !== o.value) e.currentTarget.style.background = "#E7EEF7"; }}
                    onMouseLeave={e => { if (sortBy !== o.value) e.currentTarget.style.background = "transparent"; }}
                  >{o.label}</button>
                ))}
              </div>
              {/* Categories */}
              <div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: "#8C8C8C", textTransform: "uppercase" }}>Категория</div>
                  <button onClick={() => setOnlyInteresting(v => !v)}
                    style={{ padding: "2px 8px", borderRadius: 20, fontSize: 10, border: "1px solid", cursor: "pointer",
                      borderColor: onlyInteresting ? "#264B82" : "#D4DBE6",
                      background: onlyInteresting ? "#264B82" : "#fff",
                      color: onlyInteresting ? "#fff" : "#8C8C8C" }}>
                    {onlyInteresting ? "Мои" : "Все"}
                  </button>
                </div>
                <button onClick={() => selectCategory(null)}
                  style={{ display: "flex", justifyContent: "space-between", width: "100%", textAlign: "left", padding: "5px 10px", border: "none", borderRadius: 3, cursor: "pointer", fontSize: 13, marginBottom: 2,
                    background: category === null ? "#264B82" : "transparent",
                    color: category === null ? "#fff" : "#1A1A1A" }}
                  onMouseEnter={e => { if (category !== null) e.currentTarget.style.background = "#E7EEF7"; }}
                  onMouseLeave={e => { if (category !== null) e.currentTarget.style.background = "transparent"; }}
                >Все категории</button>
                {visibleFacets.map(f => (
                  <button key={f.name} onClick={() => selectCategory(f.name)}
                    style={{ display: "flex", justifyContent: "space-between", width: "100%", textAlign: "left", padding: "5px 10px", border: "none", borderRadius: 3, cursor: "pointer", fontSize: 12, marginBottom: 1,
                      background: category === f.name ? "#264B82" : "transparent",
                      color: category === f.name ? "#fff" : "#1A1A1A" }}
                    onMouseEnter={e => { if (category !== f.name) e.currentTarget.style.background = "#E7EEF7"; }}
                    onMouseLeave={e => { if (category !== f.name) e.currentTarget.style.background = "transparent"; }}
                  >
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</span>
                    <span style={{ fontSize: 11, color: category === f.name ? "rgba(255,255,255,.7)" : "#8C8C8C", flexShrink: 0, marginLeft: 4 }}>{f.count}</span>
                  </button>
                ))}
                {onlyInteresting && userCategoryFacets.length === 0 && (
                  <p style={{ fontSize: 11, color: "#8C8C8C", fontStyle: "italic", margin: "6px 0 0" }}>Нет данных о предпочтениях — нажмите «Все»</p>
                )}
              </div>
            </div>
          )}
        </aside>

        {/* RESULTS AREA */}
        <main style={{ flex: 1, minWidth: 0 }}>
          {loading && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: 40, justifyContent: "center", color: "#8C8C8C" }}>
              <Loader2 size={20} style={{ animation: "spin 1s linear infinite" }} /> Поиск...
            </div>
          )}

          {!loading && response && response.results.length > 0 && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <p style={{ fontSize: 13, color: "#8C8C8C", margin: 0 }}>
                  {query === "*" && category
                    ? <>Товары категории «<strong style={{ color: "#1A1A1A" }}>{category}</strong>»</>
                    : <>Результаты по запросу «<strong style={{ color: "#1A1A1A" }}>{response.query}</strong>»
                      {category && <span> в категории «{category}»</span>}</>
                  }
                </p>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {response.results.map((item, idx) => {
                  const delta = rankDeltas[item.id];
                  return (
                    <div key={item.id} style={{ background: "#fff", border: "1px solid #D4DBE6", borderRadius: 6, display: "flex", flexDirection: "column" }}>
                      <div style={{ padding: "14px 16px", flex: 1 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2, flexWrap: "wrap" }}>
                              <span style={{ fontSize: 11, fontWeight: 700, color: "#264B82", background: "#E7EEF7", borderRadius: 3, padding: "1px 6px", fontFamily: "monospace" }}>#{offset + idx + 1}</span>
                              {delta !== undefined && delta !== 0 && (
                                <span style={{
                                  display: "inline-flex", alignItems: "center", gap: 2,
                                  color: delta > 0 ? "#0D9B68" : "#DB2B21",
                                  fontSize: 11, fontWeight: 700, padding: "1px 6px",
                                  background: delta > 0 ? "#E6F7F1" : "#FDECEA",
                                  borderRadius: 4,
                                }}>
                                  {delta > 0 ? "↑" : "↓"}{Math.abs(delta)}
                                </span>
                              )}
                              <h3 onClick={() => { trackAction(item.id, "click", item.category ?? undefined); setModalItem(item); }}
                                style={{ fontSize: 14, fontWeight: 600, color: "#1A1A1A", margin: 0, cursor: "pointer", lineHeight: 1.35 }}
                                onMouseEnter={e => (e.currentTarget.style.color = "#264B82")}
                                onMouseLeave={e => (e.currentTarget.style.color = "#1A1A1A")}
                              >{item.name}</h3>
                            </div>
                            {item.category && <p style={{ fontSize: 12, color: "#8C8C8C", margin: "2px 0 0" }}>{item.category}</p>}
                            {item.snippet && item.snippet !== item.name && (
                              <p style={{ fontSize: 11, color: "#7F8792", margin: "4px 0 0", fontStyle: "italic" }}
                                dangerouslySetInnerHTML={{ __html: item.snippet.replace(/<<(.*?)>>/g, '<mark style="background:#FFF3CD;padding:0 2px;border-radius:2px">$1</mark>') }}
                              />
                            )}
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
                            <span style={{ fontSize: 10, fontFamily: "monospace", color: "#8C8C8C", background: "#E7EEF7", borderRadius: 3, padding: "2px 6px" }}>ID {item.id}</span>
                            <span style={{ fontSize: 10, fontFamily: "monospace", color: "#264B82" }}>score: {item.score.toFixed(3)}</span>
                            {item.avg_price != null && (
                              <span style={{ fontSize: 11, color: "#0D9B68", fontWeight: 600 }}>
                                ~{item.avg_price.toLocaleString("ru-RU")} ₽
                                {item.price_trend === "down" && <span title="Цена снижается" style={{ marginLeft: 3 }}>↓</span>}
                                {item.price_trend === "up" && <span title="Цена растёт" style={{ marginLeft: 3, color: "#F67319" }}>↑</span>}
                              </span>
                            )}
                          </div>
                        </div>
                        {item.attributes && Object.keys(item.attributes).length > 0 && (
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px", marginTop: 6 }}>
                            {Object.entries(item.attributes).slice(0, 4).map(([k, v]) => (
                              <span key={k} style={{ fontSize: 11, color: "#8C8C8C" }}><strong style={{ color: "#7F8792" }}>{k}:</strong> {String(v)}</span>
                            ))}
                          </div>
                        )}
                        {item.explanations.length > 0 && (
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
                            {item.explanations.map((e, i) => (
                              <span key={i} style={{ fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 3, ...(BADGE_STYLES[e.factor] || { background: "#E7EEF7", color: "#8C8C8C" }) }}>{e.reason}</span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div style={{ padding: "6px 16px", borderTop: "1px solid #E7EEF7", display: "flex", alignItems: "center", gap: 4 }}>
                        <Btn onClick={() => { trackAction(item.id, "click", item.category ?? undefined); setModalItem(item); }} color="#264B82"><ChevronRight size={12} /> Подробнее</Btn>
                        <Btn onClick={() => setThinkingItem({ item, position: offset + idx + 1 })} color="#7F8792"><Brain size={12} /> Почему здесь?</Btn>
                        <div style={{ display: "flex", gap: 2, marginLeft: "auto" }}>
                          <button
                            onClick={() => handleLike(item.id, item.category ?? undefined)}
                            title="Подходящий товар — поднять выше"
                            style={{ background: likedIds.has(item.id) ? "#E8F8F2" : "none", border: "none", color: likedIds.has(item.id) ? "#0D9B68" : "#C9D1DF", fontSize: 12, cursor: "pointer", padding: "4px 8px", borderRadius: 4 }}
                            onMouseEnter={e => { if (!likedIds.has(item.id)) { e.currentTarget.style.color = "#0D9B68"; e.currentTarget.style.background = "#E8F8F2"; } }}
                            onMouseLeave={e => { if (!likedIds.has(item.id)) { e.currentTarget.style.color = "#C9D1DF"; e.currentTarget.style.background = "none"; } }}
                          ><ThumbsUp size={12} /></button>
                          <button
                            onClick={() => handleDislike(item.id, item.category ?? undefined)}
                            title="Не подходит — опустить ниже"
                            style={{ background: dislikedIds.has(item.id) ? "#FDECEA" : "none", border: "none", color: dislikedIds.has(item.id) ? "#DB2B21" : "#C9D1DF", fontSize: 12, cursor: "pointer", padding: "4px 8px", borderRadius: 4 }}
                            onMouseEnter={e => { if (!dislikedIds.has(item.id)) { e.currentTarget.style.color = "#DB2B21"; e.currentTarget.style.background = "#FDECEA"; } }}
                            onMouseLeave={e => { if (!dislikedIds.has(item.id)) { e.currentTarget.style.color = "#C9D1DF"; e.currentTarget.style.background = "none"; } }}
                          ><ThumbsDown size={12} /></button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              {response.total > PAGE_SIZE && (
                <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
                  <PgBtn disabled={offset === 0} onClick={() => doSearch(query, Math.max(0, offset - PAGE_SIZE))}>Назад</PgBtn>
                  <span style={{ padding: "8px 12px", fontSize: 13, color: "#8C8C8C" }}>{Math.floor(offset / PAGE_SIZE) + 1} / {Math.ceil(response.total / PAGE_SIZE)}</span>
                  <PgBtn disabled={offset + PAGE_SIZE >= response.total} onClick={() => doSearch(query, offset + PAGE_SIZE)}>Далее</PgBtn>
                </div>
              )}
            </>
          )}

          {!loading && response && response.total === -1 && (
            <EmptyBox icon={<PackageSearch size={48} style={{ color: "#F67319" }} />}
              title="Сервер загружается, подождите 30 секунд"
              subtitle="Система прогревает поисковые индексы. Попробуйте повторить поиск."
              onPick={(q) => { setInputVal(q); doSearch(q); }} />
          )}

          {!loading && response && response.total === 0 && response.results.length === 0 && (
            <EmptyBox icon={<PackageSearch size={48} style={{ color: "#D4DBE6" }} />}
              title={query === "*" && category ? `В категории «${category}» ничего не найдено` : `По запросу «${query}» ничего не найдено`}
              subtitle="Попробуйте другой запрос или снимите фильтр категории"
              onPick={(q) => { setInputVal(q); doSearch(q); }} />
          )}

          {!loading && !response && (
            <EmptyBox icon={<Search size={48} style={{ color: "#D4DBE6" }} />}
              title="Начните вводить название товара"
              subtitle="Система учтёт ваш профиль и историю закупок для персональной выдачи"
              onPick={(q) => { setInputVal(q); doSearch(q); }} />
          )}
        </main>
      </div>

      {/* MODALS */}
      {modalItem && (
        <DetailModal item={modalItem} onClose={() => setModalItem(null)}
          onLike={handleLike} onDislike={handleDislike}
          likedIds={likedIds} dislikedIds={dislikedIds}
          trackAction={trackAction} />
      )}
      {thinkingItem && (
        <ThinkingModal item={thinkingItem.item} position={thinkingItem.position}
          query={query} correctedQuery={response?.corrected_query ?? null}
          onClose={() => setThinkingItem(null)} />
      )}

      {/* INTEREST PANEL */}
      {showInterestPanel && (
        <InterestPanel
          userInn={user.id}
          userLabel={user.label}
          lastQuery={query}
          sessionClicks={sessionClicks}
          onClose={() => setShowInterestPanel(false)}
        />
      )}

      {/* TOAST */}
      {toast && (
        <div style={{ position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)", background: "#1A1A1A", color: "#fff", padding: "10px 20px", borderRadius: 6, fontSize: 13, zIndex: 9999, boxShadow: "0 4px 16px rgba(0,0,0,.25)", pointerEvents: "none" }}>
          {toast}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  );
}

/* ---- small reusable pieces ---- */
function Btn({ onClick, color, children }: { onClick: () => void; color: string; children: ReactNode }) {
  return (
    <button onClick={onClick}
      style={{ background: "none", border: "none", color, fontSize: 12, fontWeight: 600, cursor: "pointer", padding: "4px 8px", borderRadius: 4, display: "flex", alignItems: "center", gap: 4 }}
      onMouseEnter={e => (e.currentTarget.style.background = "#E7EEF7")}
      onMouseLeave={e => (e.currentTarget.style.background = "none")}
    >{children}</button>
  );
}

function PgBtn({ disabled, onClick, children }: { disabled: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button disabled={disabled} onClick={onClick}
      style={{ padding: "8px 16px", border: "1px solid #D4DBE6", borderRadius: 4, background: "#fff", cursor: disabled ? "default" : "pointer", opacity: disabled ? 0.4 : 1, fontSize: 13 }}
    >{children}</button>
  );
}

function EmptyBox({ icon, title, subtitle, onPick }: { icon: ReactNode; title: string; subtitle: string; onPick: (q: string) => void }) {
  return (
    <div style={{ textAlign: "center", padding: "60px 20px" }}>
      <div style={{ marginBottom: 12 }}>{icon}</div>
      <p style={{ fontSize: 16, fontWeight: 600, color: "#1A1A1A" }}>{title}</p>
      <p style={{ fontSize: 13, color: "#8C8C8C", marginTop: 4, marginBottom: 16 }}>{subtitle}</p>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 8 }}>
        {POPULAR.map(q => (
          <button key={q} onClick={() => onPick(q)}
            style={{ padding: "6px 14px", border: "1px solid #D4DBE6", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13 }}
            onMouseEnter={e => { e.currentTarget.style.background = "#264B82"; e.currentTarget.style.color = "#fff"; e.currentTarget.style.borderColor = "#264B82"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "#fff"; e.currentTarget.style.color = "#1A1A1A"; e.currentTarget.style.borderColor = "#D4DBE6"; }}
          >{q}</button>
        ))}
      </div>
    </div>
  );
}

/* ---- DetailModal ---- */
function DetailModal({ item, onClose, onLike, onDislike, likedIds, dislikedIds, trackAction }: {
  item: STEResult; onClose: () => void;
  onLike: (id: number, cat?: string) => void;
  onDislike: (id: number, cat?: string) => void;
  likedIds: Set<number>; dislikedIds: Set<number>;
  trackAction: (id: number, a: string) => void;
}) {
  const openedAt = useRef(Date.now());
  const isLiked = likedIds.has(item.id);
  const isDisliked = dislikedIds.has(item.id);

  function handleClose() {
    if (Date.now() - openedAt.current < 4000) trackAction(item.id, "bounce");
    onClose();
  }

  const attrs: Record<string, string> = (() => {
    if (!item.attributes) return {};
    const raw = (item.attributes as Record<string, unknown>)["raw"];
    if (typeof raw === "string") return parseRawAttrs(raw);
    return Object.fromEntries(Object.entries(item.attributes).map(([k, v]) => [k, String(v)]));
  })();

  return (
    <div onClick={e => { if (e.target === e.currentTarget) handleClose(); }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", display: "flex", alignItems: "center", justifyContent: "center", padding: 16, zIndex: 999 }}>
      <div style={{ background: "#fff", borderRadius: 8, boxShadow: "0 8px 40px rgba(0,0,0,.2)", width: "100%", maxWidth: 520, maxHeight: "90vh", overflow: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: 20, borderBottom: "1px solid #D4DBE6" }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1A1A1A", margin: 0 }}>{item.name}</h2>
            {item.category && <p style={{ fontSize: 13, color: "#8C8C8C", margin: "4px 0 0" }}>{item.category}</p>}
          </div>
          <button onClick={handleClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#8C8C8C", padding: 4 }}><X size={18} /></button>
        </div>
        <div style={{ padding: 20 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <span style={{ fontSize: 11, fontFamily: "monospace", color: "#8C8C8C", background: "#E7EEF7", borderRadius: 3, padding: "3px 8px" }}>ID: {item.id}</span>
            <span style={{ fontSize: 11, fontFamily: "monospace", color: "#264B82", background: "#E7EEF7", borderRadius: 3, padding: "3px 8px" }}>Score: {item.score.toFixed(4)}</span>
            {item.avg_price != null && (
              <span style={{ fontSize: 11, color: "#0D9B68", background: "#E6F7F1", borderRadius: 3, padding: "3px 8px", fontWeight: 600 }}>~{item.avg_price.toLocaleString("ru-RU")} ₽</span>
            )}
          </div>
          {item.explanations.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", marginBottom: 8 }}>Почему этот результат выше</p>
              {item.explanations.map((e, i) => (
                <div key={i} style={{ fontSize: 13, color: "#1A1A1A", margin: "6px 0", paddingLeft: 12, borderLeft: "3px solid #264B82", display: "flex", justifyContent: "space-between" }}>
                  <span>{e.reason}</span>
                  <span style={{ fontSize: 11, color: "#8C8C8C", flexShrink: 0, marginLeft: 8 }}>
                    {e.weight > 0 ? `+${e.weight.toFixed(2)}` : e.weight.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          )}
          {Object.keys(attrs).length > 0 && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", marginBottom: 8 }}>Характеристики</p>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <tbody>
                  {Object.entries(attrs).map(([k, v]) => (
                    <tr key={k} style={{ borderBottom: "1px solid #E7EEF7" }}>
                      <td style={{ padding: "5px 8px 5px 0", fontWeight: 500, color: "#1A1A1A", width: "45%", verticalAlign: "top" }}>{k}</td>
                      <td style={{ padding: "5px 0", color: "#7F8792" }}>{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <div style={{ padding: "14px 20px", borderTop: "1px solid #D4DBE6", display: "flex", gap: 8 }}>
          <button onClick={() => onLike(item.id, item.category ?? undefined)}
            style={{ padding: "8px 16px", border: `1px solid ${isLiked ? "#0D9B68" : "#D4DBE6"}`, borderRadius: 4, background: isLiked ? "#E6F7F1" : "#fff", cursor: "pointer", fontSize: 13, color: isLiked ? "#0D9B68" : "#1A1A1A", display: "flex", alignItems: "center", gap: 4, fontWeight: isLiked ? 600 : 400 }}
          ><ThumbsUp size={14} /> {isLiked ? "Понравилось" : "Нравится"}</button>
          <button onClick={() => { onDislike(item.id, item.category ?? undefined); handleClose(); }}
            style={{ padding: "8px 16px", border: `1px solid ${isDisliked ? "rgba(219,43,33,.4)" : "#D4DBE6"}`, borderRadius: 4, background: isDisliked ? "#FDECEA" : "#fff", cursor: "pointer", fontSize: 13, color: "#DB2B21", display: "flex", alignItems: "center", gap: 4 }}
          ><ThumbsDown size={14} /> Не подходит</button>
          <button onClick={() => { trackAction(item.id, "hide"); handleClose(); }}
            style={{ marginLeft: "auto", padding: "8px 16px", border: "1px solid rgba(219,43,33,.2)", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13, color: "#DB2B21", display: "flex", alignItems: "center", gap: 4 }}
          ><X size={14} /> Скрыть</button>
        </div>
      </div>
    </div>
  );
}

/* ---- ThinkingModal: business language ---- */
const FACTOR_LABELS: Record<string, string> = {
  history: "Пользователь закупал похожие товары раньше",
  category: "Совпадает с интересующей пользователя категорией",
  session: "Пользователь кликал на похожие товары в этой сессии",
  collaborative: "Похожие организации часто это покупают",
  profile_mismatch: "Не совпадает с профилем пользователя",
  negative: "Пользователь ранее отклонил похожие товары",
  popularity: "Часто заказывается другими покупателями",
  bm25: "Точное совпадение слов в названии товара",
  semantic: "Похож по смыслу на поисковый запрос",
  catboost: "ML-модель оценила как подходящий для профиля",
  like_boost: "Пользователь оценил этот товар положительно",
  dislike_penalty: "Пользователь отметил как нерелевантный",
};
const FACTOR_COLORS: Record<string, string> = {
  history: "#0D9B68", category: "#167C85", session: "#F67319",
  collaborative: "#48B8C2", profile_mismatch: "#DB2B21", negative: "#DB2B21",
  popularity: "#264B82", bm25: "#264B82", semantic: "#264B82",
  catboost: "#264B82", like_boost: "#0D9B68", dislike_penalty: "#DB2B21",
};

function ThinkingModal({ item, position, query, correctedQuery, onClose }: {
  item: STEResult; position: number; query: string;
  correctedQuery: string | null; onClose: () => void;
}) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

  const maxWeight = Math.max(...item.explanations.map(e => Math.abs(e.weight)), 1);
  const wasCorrected = correctedQuery && correctedQuery !== query;

  return (
    <div onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", display: "flex", alignItems: "center", justifyContent: "center", padding: 16, zIndex: 1000 }}>
      <div style={{ background: "#fff", borderRadius: 10, boxShadow: "0 8px 40px rgba(0,0,0,.25)", width: "100%", maxWidth: 560, maxHeight: "92vh", overflow: "auto" }}>
        {/* header */}
        <div style={{ background: "#264B82", padding: "16px 20px", borderRadius: "10px 10px 0 0", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <Brain size={18} color="#fff" />
              <span style={{ color: "#fff", fontWeight: 700, fontSize: 15 }}>Почему товар на позиции #{position}?</span>
            </div>
            <p style={{ color: "#a3bfe0", fontSize: 12, margin: 0 }}>Логика ранжирования — простым языком</p>
          </div>
          <button onClick={onClose} style={{ background: "rgba(255,255,255,.15)", border: "none", color: "#fff", cursor: "pointer", borderRadius: 4, padding: 4 }}><X size={16} /></button>
        </div>

        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 18 }}>
          {/* Товар */}
          <div style={{ background: "#E7EEF7", borderRadius: 6, padding: "10px 14px" }}>
            <div style={{ fontWeight: 700, fontSize: 14, color: "#1A1A1A" }}>{item.name}</div>
            {item.category && <div style={{ fontSize: 12, color: "#8C8C8C", marginTop: 2 }}>{item.category}</div>}
            <div style={{ display: "flex", gap: 12, marginTop: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 12, color: "#7F8792" }}>Позиция #{position}</span>
              <span style={{ fontSize: 12, fontFamily: "monospace", color: "#264B82" }}>score: {item.score.toFixed(3)}</span>
              {item.avg_price != null && <span style={{ fontSize: 12, color: "#0D9B68", fontWeight: 600 }}>~{item.avg_price.toLocaleString("ru-RU")} ₽</span>}
            </div>
          </div>

          {/* Как система понимала запрос */}
          <div>
            <p style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", margin: "0 0 10px" }}>Как система понимала запрос</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 7, fontSize: 13 }}>
              <div style={{ display: "flex", gap: 8 }}>
                <span style={{ color: "#8C8C8C", minWidth: 130, flexShrink: 0 }}>Исходный запрос:</span>
                <strong>«{query}»</strong>
              </div>
              {wasCorrected ? (
                <div style={{ display: "flex", gap: 8 }}>
                  <span style={{ color: "#8C8C8C", minWidth: 130, flexShrink: 0 }}>Исправлено:</span>
                  <span>«{query}» <span style={{ color: "#8C8C8C" }}>→</span> <strong style={{ color: "#F67319" }}>«{correctedQuery}»</strong></span>
                </div>
              ) : (
                <div style={{ display: "flex", gap: 8 }}>
                  <span style={{ color: "#8C8C8C", minWidth: 130, flexShrink: 0 }}>Опечатки:</span>
                  <span style={{ color: "#0D9B68" }}>не обнаружены</span>
                </div>
              )}
              <div style={{ display: "flex", gap: 8 }}>
                <span style={{ color: "#8C8C8C", minWidth: 130, flexShrink: 0 }}>Пайплайн:</span>
                <span style={{ color: "#7F8792", fontSize: 12 }}>лемматизация → опечатки → синонимы → учёт контекста → BM25 + семантика → профиль → ML-ранжирование</span>
              </div>
            </div>
          </div>

          {/* Факторы */}
          <div>
            <p style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", marginBottom: 10 }}>Факторы позиции</p>
            {item.explanations.length === 0 ? (
              <p style={{ fontSize: 13, color: "#7F8792", fontStyle: "italic" }}>Ранжирование только по текстовому совпадению — других сигналов нет</p>
            ) : (
              item.explanations.map((exp, i) => {
                const isNeg = exp.weight < 0;
                const barColor = FACTOR_COLORS[exp.factor] ?? (isNeg ? "#DB2B21" : "#264B82");
                const barW = Math.min(Math.abs(exp.weight) / maxWeight * 100, 100);
                const label = FACTOR_LABELS[exp.factor] ?? exp.reason;
                return (
                  <div key={i} style={{ marginBottom: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 13, color: "#1A1A1A" }}>{label}</span>
                      <span style={{ fontSize: 12, fontFamily: "monospace", color: isNeg ? "#DB2B21" : barColor, fontWeight: 700 }}>
                        {isNeg ? exp.weight.toFixed(2) : `+${exp.weight.toFixed(2)}`}
                      </span>
                    </div>
                    <div style={{ height: 6, background: "#E7EEF7", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${barW}%`, background: barColor, borderRadius: 3 }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
