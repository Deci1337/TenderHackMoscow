import {
  useCallback, useEffect, useRef, useState,
  type CSSProperties, type FormEvent, type ReactNode,
} from "react";
import { api, STEResult, SearchResponse, CategoryFacet, MyProduct } from "./api/client";
import {
  Search, LogOut, ChevronRight, ChevronDown, Loader2, PackageSearch,
  ThumbsDown, ThumbsUp, X, SlidersHorizontal, ArrowUpDown, Brain,
  Plus, Zap, Package
} from "lucide-react";

const PAGE_SIZE = 20;
const INTEREST_OPTIONS = [
  "Канцелярские товары", "Медицинские товары", "IT-оборудование",
  "Стройматериалы", "Электротехника", "Образование",
  "Хозяйственные товары", "ЖКХ", "Транспорт", "Другое",
];
// Demo users have pre-seeded contract history in the database
const DEMO_USERS = [
  { id: "7701234567", label: "Школа №1234", interests: ["Образование", "Канцелярские товары"] },
  { id: "7709876543", label: "Городская больница №5", interests: ["Медицинские товары"] },
  { id: "7705551234", label: "СтройМонтаж", interests: ["Стройматериалы", "Электротехника"] },
];
const POPULAR = ["бумага офисная","картридж","компьютер","стул офисный","маска медицинская"];
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

function generateUserId(): string {
  return `uid_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
}

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

  if (!user) return <Onboarding onDone={login} />;
  return <Main user={user} onLogout={logout} />;
}

/* ===================  ONBOARDING  =================== */
function Onboarding({ onDone }: { onDone: (u: User) => void }) {
  const [interests, setInterests] = useState<string[]>([]);

  function toggle(item: string) {
    setInterests(prev => prev.includes(item) ? prev.filter(x => x !== item) : [...prev, item]);
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    if (interests.length === 0) return;
    const id = generateUserId();
    api.onboard(id, interests).catch(() => {});
    onDone({ id, label: "Покупатель", interests });
  }

  function pickDemo(u: typeof DEMO_USERS[number]) {
    api.onboard(u.id, u.interests).catch(() => {});
    onDone({ id: u.id, label: u.label, interests: u.interests });
  }

  return (
    <div style={{ minHeight: "100vh", background: "#E7EEF7", display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div style={{ background: "#fff", borderRadius: 8, boxShadow: "0 4px 24px rgba(0,0,0,.12)", width: "100%", maxWidth: 440, overflow: "hidden" }}>
        <div style={{ background: "#264B82", padding: "20px 24px", color: "#fff" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <div style={{ width: 28, height: 28, background: "#fff", borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center", color: "#264B82", fontWeight: 900, fontSize: 12 }}>П</div>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Портал поставщиков</span>
          </div>
          <div style={{ fontWeight: 700, fontSize: 18 }}>Персонализация поиска</div>
          <div style={{ fontSize: 13, color: "#a3bfe0", marginTop: 4 }}>Выберите интересующие категории — система поднимет их в выдаче</div>
        </div>
        <form onSubmit={submit} style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A", marginBottom: 10 }}>
              Что вас интересует?
              {interests.length > 0 && <span style={{ fontWeight: 400, color: "#8C8C8C", marginLeft: 6 }}>выбрано: {interests.length}</span>}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {INTEREST_OPTIONS.map(item => {
                const active = interests.includes(item);
                return (
                  <button type="button" key={item} onClick={() => toggle(item)}
                    style={{ padding: "7px 14px", borderRadius: 20, fontSize: 13, border: "1px solid", cursor: "pointer", transition: "all .15s",
                      borderColor: active ? "#264B82" : "#D4DBE6",
                      background: active ? "#264B82" : "#fff",
                      color: active ? "#fff" : "#1A1A1A",
                      fontWeight: active ? 600 : 400 }}
                  >{item}</button>
                );
              })}
            </div>
          </div>
          <button type="submit" disabled={interests.length === 0}
            style={{ padding: "10px 0", borderRadius: 4, border: "none",
              background: interests.length === 0 ? "#a3bfe0" : "#264B82",
              color: "#fff", fontWeight: 600, fontSize: 14,
              cursor: interests.length === 0 ? "default" : "pointer" }}
          >Начать поиск</button>
        </form>
        <div style={{ padding: "0 24px 20px", borderTop: "1px solid #E7EEF7" }}>
          <div style={{ fontSize: 11, color: "#8C8C8C", fontWeight: 600, textTransform: "uppercase", letterSpacing: 1, margin: "14px 0 8px" }}>Попробовать с историей закупок</div>
          {DEMO_USERS.map(u => (
            <button key={u.id} onClick={() => pickDemo(u)}
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%", padding: "8px 12px", border: "none", background: "transparent", borderRadius: 4, cursor: "pointer", textAlign: "left", fontSize: 14 }}
              onMouseEnter={e => (e.currentTarget.style.background = "#E7EEF7")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              <span style={{ fontWeight: 500, color: "#1A1A1A" }}>{u.label}</span>
              <span style={{ fontSize: 11, color: "#8C8C8C" }}>{u.interests.join(", ")}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ===================  MAIN  =================== */
/** Parse "Key:Value;Key2:Value2" attribute strings into a record. */
function parseRawAttrs(raw: string): Record<string, string> {
  return Object.fromEntries(
    raw.split(";")
      .map(p => { const i = p.indexOf(":"); return i > 0 ? [p.slice(0, i).trim(), p.slice(i + 1).trim()] : null; })
      .filter((p): p is [string, string] => p !== null && p[1] !== "")
  );
}

function Main({ user, onLogout }: { user: User; onLogout: () => void }) {
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
  const [showCreateProduct, setShowCreateProduct] = useState(false);
  const [showMyProducts, setShowMyProducts] = useState(false);
  const [promotingProduct, setPromotingProduct] = useState<MyProduct | null>(null);
  const [myProducts, setMyProducts] = useState<MyProduct[]>([]);
  const [history] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem("sh") || "[]"); } catch { return []; }
  });
  const [sessionId] = useState(() => `s_${Date.now()}`);
  const suggestTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestRef = useRef<HTMLDivElement>(null);

  useEffect(() => { api.facets().then(r => setFacets(r.categories)).catch(() => {}); }, []);
  useEffect(() => { api.getMyProducts(user.id).then(setMyProducts).catch(() => {}); }, [user.id]);

  // close suggestions on outside click
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (suggestRef.current && !suggestRef.current.contains(e.target as Node) && e.target !== inputRef.current) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  const doSearch = useCallback(async (q: string, off = 0, sort = sortBy, cat = category) => {
    if (!q.trim()) return;
    setQuery(q); setOffset(off); setLoading(true); setShowSuggestions(false);
    const h = [q, ...history.filter(x => x !== q)].slice(0, 8);
    localStorage.setItem("sh", JSON.stringify(h));
    try {
      const data = await api.search(q, user.id, sessionId, PAGE_SIZE, off, sort, cat || undefined, user.interests);
      setResponse(data);
    } catch {
      setResponse({ query: q, corrected_query: null, did_you_mean: null, total: 0, results: [] });
    } finally { setLoading(false); }
  }, [user.id, sessionId, sortBy, category, history]);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  function trackAction(steId: number, action: string, category?: string) {
    const meta: Record<string, unknown> = {};
    if (category) meta.category = category;
    api.logEvent(user.id, steId, action, sessionId, query, meta).catch(() => {});
  }

  function handleLike(steId: number, cat?: string) {
    setLikedIds(prev => { const s = new Set(prev); s.add(steId); return s; });
    setDislikedIds(prev => { const s = new Set(prev); s.delete(steId); return s; });
    trackAction(steId, "like", cat);
    showToast("Товар продвинут выше — спасибо за оценку");
  }

  function handleDislike(steId: number, cat?: string) {
    setDislikedIds(prev => { const s = new Set(prev); s.add(steId); return s; });
    setLikedIds(prev => { const s = new Set(prev); s.delete(steId); return s; });
    trackAction(steId, "dislike", cat);
    showToast("Отмечено как неподходящий товар");
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
    // Always clear old results immediately so stale data doesn't linger
    setResponse(null);
    if (query) doSearch(query, 0, sortBy, cat);
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
            <button onClick={() => { setShowMyProducts(true); api.getMyProducts(user.id).then(setMyProducts).catch(() => {}); }}
              style={{ background: "rgba(255,255,255,.15)", border: "none", color: "#fff", padding: "4px 10px", borderRadius: 4, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}>
              <Package size={13} /> Мои товары
            </button>
            <button onClick={() => setShowCreateProduct(true)}
              style={{ background: "#0D9B68", border: "none", color: "#fff", padding: "4px 10px", borderRadius: 4, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 5 }}>
              <Plus size={13} /> Добавить товар
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
              <p style={{ fontSize: 13, color: "#8C8C8C", margin: "2px 0 0" }}>{user.interests.join(" · ")}</p>
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
              {/* Suggestions dropdown */}
              {showSuggestions && (
                <div ref={suggestRef} style={{ position: "absolute", top: "100%", left: 0, right: 0, background: "#fff", border: "1px solid #D4DBE6", borderTop: "none", borderRadius: "0 0 6px 6px", zIndex: 50, boxShadow: "0 4px 12px rgba(0,0,0,.08)", maxHeight: 240, overflow: "auto" }}>
                  {history.length > 0 && !inputVal.trim() && (
                    <div style={{ padding: "6px 12px", fontSize: 11, color: "#8C8C8C", fontWeight: 600, textTransform: "uppercase" }}>Недавние</div>
                  )}
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
                <div style={{ fontSize: 11, fontWeight: 600, color: "#8C8C8C", textTransform: "uppercase", marginBottom: 6 }}>Категория</div>
                <button onClick={() => selectCategory(null)}
                  style={{ display: "flex", justifyContent: "space-between", width: "100%", textAlign: "left", padding: "5px 10px", border: "none", borderRadius: 3, cursor: "pointer", fontSize: 13, marginBottom: 2,
                    background: category === null ? "#264B82" : "transparent",
                    color: category === null ? "#fff" : "#1A1A1A" }}
                  onMouseEnter={e => { if (category !== null) e.currentTarget.style.background = "#E7EEF7"; }}
                  onMouseLeave={e => { if (category !== null) e.currentTarget.style.background = "transparent"; }}
                >Все категории</button>
                {facets.map(f => (
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
              </div>
            </div>
          )}
        </aside>

        {/* RESULTS AREA */}
        <main style={{ flex: 1, minWidth: 0 }}>
          {/* Loading */}
          {loading && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: 40, justifyContent: "center", color: "#8C8C8C" }}>
              <Loader2 size={20} style={{ animation: "spin 1s linear infinite" }} /> Поиск...
            </div>
          )}

          {/* Results */}
          {!loading && response && response.results.length > 0 && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <p style={{ fontSize: 13, color: "#8C8C8C", margin: 0 }}>
                  Результаты по запросу «<strong style={{ color: "#1A1A1A" }}>{response.query}</strong>»
                  {category && <span> в категории «{category}»</span>}
                </p>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {response.results.map((item, idx) => (
                  <div key={item.id} style={{ background: "#fff", border: "1px solid #D4DBE6", borderRadius: 6, display: "flex", flexDirection: "column" }}>
                    <div style={{ padding: "14px 16px", flex: 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2, flexWrap: "wrap" }}>
                            <span style={{ fontSize: 11, fontWeight: 700, color: "#264B82", background: "#E7EEF7", borderRadius: 3, padding: "1px 6px", fontFamily: "monospace" }}>#{offset + idx + 1}</span>
                            {item.creator_user_id && (
                              <span style={{ fontSize: 10, fontWeight: 700, color: "#fff", background: "#167C85", borderRadius: 3, padding: "1px 6px", letterSpacing: 0.5 }}>ТЕСТ</span>
                            )}
                            {item.is_promoted && (
                              <span style={{ fontSize: 10, fontWeight: 700, color: "#fff", background: "#F67319", borderRadius: 3, padding: "1px 6px", display: "flex", alignItems: "center", gap: 2 }}>
                                <Zap size={9} /> ПРОДВИГАЕТСЯ
                              </span>
                            )}
                            <h3 onClick={() => { trackAction(item.id, "click", item.category ?? undefined); setModalItem(item); }}
                              style={{ fontSize: 14, fontWeight: 600, color: "#1A1A1A", margin: 0, cursor: "pointer", lineHeight: 1.35 }}
                              onMouseEnter={e => (e.currentTarget.style.color = "#264B82")}
                              onMouseLeave={e => (e.currentTarget.style.color = "#1A1A1A")}
                            >{item.name}</h3>
                          </div>
                          {item.category && <p style={{ fontSize: 12, color: "#8C8C8C", margin: "2px 0 0" }}>{item.category}</p>}
                          {/* ts_headline snippet — highlights matching terms */}
                          {item.snippet && item.snippet !== item.name && (
                            <p style={{ fontSize: 11, color: "#7F8792", margin: "4px 0 0", fontStyle: "italic" }}
                              dangerouslySetInnerHTML={{ __html: item.snippet.replace(/<<(.*?)>>/g, '<mark style="background:#FFF3CD;padding:0 2px;border-radius:2px">$1</mark>') }}
                            />
                          )}
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
                          <span style={{ fontSize: 10, fontFamily: "monospace", color: "#8C8C8C", background: "#E7EEF7", borderRadius: 3, padding: "2px 6px" }}>ID {item.id}</span>
                          <span style={{ fontSize: 10, fontFamily: "monospace", color: "#264B82" }}>score: {item.score.toFixed(3)}</span>
                          {/* Price from historical contracts */}
                          {item.avg_price != null && (
                            <span style={{ fontSize: 11, color: "#0D9B68", fontWeight: 600 }}>
                              ~{item.avg_price.toLocaleString("ru-RU")} ₽
                              {item.price_trend === "down" && <span title="Цена снижается" style={{ marginLeft: 3, color: "#0D9B68" }}>↓</span>}
                              {item.price_trend === "up" && <span title="Цена растёт" style={{ marginLeft: 3, color: "#F67319" }}>↑</span>}
                            </span>
                          )}
                        </div>
                      </div>
                      {/* Attributes preview */}
                      {item.attributes && Object.keys(item.attributes).length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px", marginTop: 6 }}>
                          {Object.entries(item.attributes).slice(0, 4).map(([k, v]) => (
                            <span key={k} style={{ fontSize: 11, color: "#8C8C8C" }}><strong style={{ color: "#7F8792" }}>{k}:</strong> {String(v)}</span>
                          ))}
                        </div>
                      )}
                      {/* Explanation badges */}
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
                      <Btn onClick={() => setThinkingItem({ item, position: offset + idx + 1 })} color="#7F8792"><Brain size={12} /> Размышления</Btn>
                      <div style={{ display: "flex", gap: 2, marginLeft: "auto" }}>
                        <button
                          onClick={() => handleLike(item.id, item.category ?? undefined)}
                          title="Правильный товар — поднять в поиске"
                          style={{ background: likedIds.has(item.id) ? "#E8F8F2" : "none", border: "none", color: likedIds.has(item.id) ? "#0D9B68" : "#C9D1DF", fontSize: 12, cursor: "pointer", padding: "4px 8px", borderRadius: 4 }}
                          onMouseEnter={e => { if (!likedIds.has(item.id)) { e.currentTarget.style.color = "#0D9B68"; e.currentTarget.style.background = "#E8F8F2"; } }}
                          onMouseLeave={e => { if (!likedIds.has(item.id)) { e.currentTarget.style.color = "#C9D1DF"; e.currentTarget.style.background = "none"; } }}
                        ><ThumbsUp size={12} /></button>
                        <button
                          onClick={() => handleDislike(item.id, item.category ?? undefined)}
                          title="Неподходящий товар — опустить в поиске"
                          style={{ background: dislikedIds.has(item.id) ? "#FDECEA" : "none", border: "none", color: dislikedIds.has(item.id) ? "#DB2B21" : "#C9D1DF", fontSize: 12, cursor: "pointer", padding: "4px 8px", borderRadius: 4 }}
                          onMouseEnter={e => { if (!dislikedIds.has(item.id)) { e.currentTarget.style.color = "#DB2B21"; e.currentTarget.style.background = "#FDECEA"; } }}
                          onMouseLeave={e => { if (!dislikedIds.has(item.id)) { e.currentTarget.style.color = "#C9D1DF"; e.currentTarget.style.background = "none"; } }}
                        ><ThumbsDown size={12} /></button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {/* Pagination */}
              {response.total > PAGE_SIZE && (
                <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
                  <PgBtn disabled={offset === 0} onClick={() => doSearch(query, Math.max(0, offset - PAGE_SIZE))}>Назад</PgBtn>
                  <span style={{ padding: "8px 12px", fontSize: 13, color: "#8C8C8C" }}>{Math.floor(offset / PAGE_SIZE) + 1} / {Math.ceil(response.total / PAGE_SIZE)}</span>
                  <PgBtn disabled={offset + PAGE_SIZE >= response.total} onClick={() => doSearch(query, offset + PAGE_SIZE)}>Далее</PgBtn>
                </div>
              )}
            </>
          )}

          {/* Empty results */}
          {!loading && response && response.results.length === 0 && (
            <EmptyBox icon={<PackageSearch size={48} style={{ color: "#D4DBE6" }} />}
              title={`По запросу «${query}» ничего не найдено`}
              subtitle="Попробуйте другой запрос или снимите фильтр категории"
              onPick={(q) => { setInputVal(q); doSearch(q); }} />
          )}

          {/* Initial state */}
          {!loading && !response && (
            <EmptyBox icon={<Search size={48} style={{ color: "#D4DBE6" }} />}
              title="Начните вводить название товара"
              subtitle="Система учтёт ваш профиль и историю закупок для персональной выдачи"
              onPick={(q) => { setInputVal(q); doSearch(q); }} />
          )}
        </main>
      </div>

      {/* MODALS */}
      {modalItem && <DetailModal item={modalItem} onClose={() => setModalItem(null)} onLike={handleLike} onDislike={handleDislike} likedIds={likedIds} dislikedIds={dislikedIds} trackAction={trackAction} />}
      {thinkingItem && <ThinkingModal item={thinkingItem.item} position={thinkingItem.position} query={query} onClose={() => setThinkingItem(null)} />}
      {showCreateProduct && (
        <CreateProductModal userId={user.id} onClose={() => setShowCreateProduct(false)}
          onCreate={p => { setMyProducts(prev => [p, ...prev]); showToast(`Товар «${p.name}» добавлен`); }} />
      )}
      {showMyProducts && (
        <MyProductsPanel products={myProducts} userId={user.id} onClose={() => setShowMyProducts(false)}
          onPromote={p => setPromotingProduct(p)}
          onProductsChange={setMyProducts} />
      )}
      {promotingProduct && (
        <PromotionModal product={promotingProduct} userId={user.id}
          onClose={() => setPromotingProduct(null)}
          onDone={updated => {
            setMyProducts(prev => prev.map(p => p.id === updated.id ? updated : p));
            setPromotingProduct(null);
            showToast(`Продвижение «${updated.name}» активировано`);
          }} />
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

  // Normalize attributes: parse "raw" string into key/value pairs
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

/* ---- ThinkingModal: "Размышления поиска" for jury demo ---- */
const FACTOR_LABELS: Record<string, string> = {
  history: "История закупок",
  category: "Совпадение категории",
  session: "Сессионный сигнал",
  collaborative: "Совместные закупки",
  profile_mismatch: "Несоответствие профилю",
  negative: "Отклонённый товар",
  promotion: "Активное продвижение",
  popularity: "Популярность",
};
const FACTOR_COLORS: Record<string, string> = {
  history: "#0D9B68", category: "#167C85", session: "#F67319",
  collaborative: "#48B8C2", profile_mismatch: "#DB2B21", negative: "#DB2B21",
  promotion: "#F67319", popularity: "#264B82",
};

function ThinkingModal({ item, position, query, onClose }: {
  item: STEResult; position: number; query: string; onClose: () => void;
}) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

  const maxWeight = Math.max(...item.explanations.map(e => Math.abs(e.weight)), 1);

  return (
    <div onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", display: "flex", alignItems: "center", justifyContent: "center", padding: 16, zIndex: 1000 }}>
      <div style={{ background: "#fff", borderRadius: 10, boxShadow: "0 8px 40px rgba(0,0,0,.25)", width: "100%", maxWidth: 560, maxHeight: "92vh", overflow: "auto" }}>
        <div style={{ background: "#264B82", padding: "16px 20px", borderRadius: "10px 10px 0 0", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <Brain size={18} color="#fff" />
              <span style={{ color: "#fff", fontWeight: 700, fontSize: 15 }}>Размышления поиска</span>
            </div>
            <p style={{ color: "#a3bfe0", fontSize: 12, margin: 0 }}>Почему этот товар на позиции #{position}</p>
          </div>
          <button onClick={onClose} style={{ background: "rgba(255,255,255,.15)", border: "none", color: "#fff", cursor: "pointer", borderRadius: 4, padding: 4 }}><X size={16} /></button>
        </div>
        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ background: "#E7EEF7", borderRadius: 6, padding: "10px 14px" }}>
            <div style={{ fontWeight: 700, fontSize: 14, color: "#1A1A1A" }}>{item.name}</div>
            {item.category && <div style={{ fontSize: 12, color: "#8C8C8C", marginTop: 2 }}>{item.category}</div>}
            <div style={{ display: "flex", gap: 12, marginTop: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 12, fontFamily: "monospace", color: "#264B82" }}>Score: {item.score.toFixed(4)}</span>
              <span style={{ fontSize: 12, color: "#7F8792" }}>Позиция #{position}</span>
              {item.avg_price != null && <span style={{ fontSize: 12, color: "#0D9B68", fontWeight: 600 }}>~{item.avg_price.toLocaleString("ru-RU")} ₽</span>}
            </div>
          </div>
          <div>
            <p style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", marginBottom: 10 }}>Факторы ранжирования</p>
            {item.explanations.length === 0 ? (
              <p style={{ fontSize: 13, color: "#7F8792", fontStyle: "italic" }}>Нет сигналов — ранжирование по текстовому совпадению с запросом</p>
            ) : (
              item.explanations.map((exp, i) => {
                const color = FACTOR_COLORS[exp.factor] || "#264B82";
                const barW = Math.min(Math.abs(exp.weight) / maxWeight * 100, 100);
                const isNeg = exp.weight < 0;
                return (
                  <div key={i} style={{ marginBottom: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 13, color: "#1A1A1A" }}>{exp.reason}</span>
                      <span style={{ fontSize: 12, fontFamily: "monospace", color: isNeg ? "#DB2B21" : color, fontWeight: 700 }}>
                        {isNeg ? exp.weight.toFixed(2) : `+${exp.weight.toFixed(2)}`}
                      </span>
                    </div>
                    <div style={{ height: 6, background: "#E7EEF7", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${barW}%`, background: isNeg ? "#DB2B21" : color, borderRadius: 3 }} />
                    </div>
                    <div style={{ fontSize: 10, color: "#8C8C8C", marginTop: 2 }}>{FACTOR_LABELS[exp.factor] || exp.factor}</div>
                  </div>
                );
              })
            )}
          </div>
          <div style={{ background: "#F8F9FA", borderRadius: 6, padding: "12px 14px" }}>
            <p style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", margin: "0 0 8px" }}>NLP-обработка запроса</p>
            <div style={{ fontSize: 13, color: "#1A1A1A", marginBottom: 6 }}>
              <span style={{ color: "#8C8C8C" }}>Запрос: </span><strong>«{query}»</strong>
            </div>
            <div style={{ fontSize: 11, color: "#7F8792", lineHeight: 1.6 }}>
              pymorphy3 (лемматизация) → SymSpell (опечатки) → синонимы → контекстный омограф → tsvector + BM25 → персонализация профиля → CatBoost rerank
            </div>
          </div>
          <div style={{ borderTop: "1px solid #E7EEF7", paddingTop: 14 }}>
            <p style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", margin: "0 0 8px" }}>Формула score</p>
            <div style={{ fontFamily: "monospace", fontSize: 12, color: "#264B82", background: "#E7EEF7", padding: "8px 12px", borderRadius: 4, lineHeight: 1.7 }}>
              score = 0.40 × text_match<br />
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ 0.50 × name_similarity<br />
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ 0.20 × personalization_delta
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---- CreateProductModal ---- */
function CreateProductModal({ userId, onClose, onCreate }: {
  userId: string;
  onClose: () => void;
  onCreate: (p: MyProduct) => void;
}) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [orderCount, setOrderCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function addTag() {
    const t = tagInput.trim().toLowerCase();
    if (t && !tags.includes(t)) setTags(prev => [...prev, t]);
    setTagInput("");
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !category.trim()) { setError("Заполните название и категорию"); return; }
    setLoading(true); setError("");
    try {
      const p = await api.createProduct({ name: name.trim(), category: category.trim(), tags, description: "", creator_user_id: userId, order_count: orderCount });
      onCreate(p as unknown as MyProduct);
      onClose();
    } catch { setError("Ошибка при добавлении товара"); }
    finally { setLoading(false); }
  }

  return (
    <div onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", display: "flex", alignItems: "center", justifyContent: "center", padding: 16, zIndex: 1001 }}>
      <div style={{ background: "#fff", borderRadius: 10, boxShadow: "0 8px 40px rgba(0,0,0,.25)", width: "100%", maxWidth: 480 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 20px", borderBottom: "1px solid #D4DBE6" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Plus size={16} color="#264B82" />
            <span style={{ fontWeight: 700, fontSize: 15, color: "#1A1A1A" }}>Добавить товар</span>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#8C8C8C" }}><X size={16} /></button>
        </div>
        <form onSubmit={submit} style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          {error && <div style={{ background: "#FDECEA", color: "#DB2B21", padding: "8px 12px", borderRadius: 4, fontSize: 13 }}>{error}</div>}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "#7F8792", display: "block", marginBottom: 4 }}>Название товара *</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Например: Дверная ручка нажимная"
              style={{ width: "100%", padding: "8px 12px", border: "1px solid #D4DBE6", borderRadius: 4, fontSize: 14, boxSizing: "border-box", outline: "none" }} />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "#7F8792", display: "block", marginBottom: 4 }}>Категория *</label>
            <input value={category} onChange={e => setCategory(e.target.value)} placeholder="Например: Фурнитура для дверей металлическая"
              style={{ width: "100%", padding: "8px 12px", border: "1px solid #D4DBE6", borderRadius: 4, fontSize: 14, boxSizing: "border-box", outline: "none" }} />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "#7F8792", display: "block", marginBottom: 4 }}>Теги (вспомогательные слова для поиска)</label>
            <div style={{ display: "flex", gap: 6, marginBottom: 8, flexWrap: "wrap", minHeight: 24 }}>
              {tags.map(t => (
                <span key={t} style={{ background: "#E7EEF7", color: "#264B82", borderRadius: 20, padding: "3px 10px", fontSize: 12, display: "flex", alignItems: "center", gap: 4 }}>
                  {t}
                  <button type="button" onClick={() => setTags(prev => prev.filter(x => x !== t))} style={{ background: "none", border: "none", cursor: "pointer", color: "#8C8C8C", padding: 0, lineHeight: 1, fontSize: 14 }}>×</button>
                </span>
              ))}
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <input value={tagInput} onChange={e => setTagInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addTag(); } }}
                placeholder="Тег + Enter..."
                style={{ flex: 1, padding: "7px 10px", border: "1px solid #D4DBE6", borderRadius: 4, fontSize: 13, outline: "none" }} />
              <button type="button" onClick={addTag} style={{ padding: "7px 12px", background: "#E7EEF7", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 13, color: "#264B82" }}>+</button>
            </div>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "#7F8792", display: "block", marginBottom: 4 }}>Количество заказов</label>
            <input type="number" min={0} value={orderCount} onChange={e => setOrderCount(Math.max(0, Number(e.target.value)))}
              placeholder="0"
              style={{ width: 140, padding: "8px 12px", border: "1px solid #D4DBE6", borderRadius: 4, fontSize: 14, boxSizing: "border-box", outline: "none" }} />
            <span style={{ fontSize: 11, color: "#8C8C8C", marginLeft: 8 }}>влияет на позицию в выдаче</span>
          </div>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button type="button" onClick={onClose} style={{ padding: "8px 18px", border: "1px solid #D4DBE6", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13 }}>Отмена</button>
            <button type="submit" disabled={loading} style={{ padding: "8px 20px", border: "none", borderRadius: 4, background: loading ? "#a3bfe0" : "#0D9B68", color: "#fff", cursor: loading ? "default" : "pointer", fontSize: 13, fontWeight: 600 }}>
              {loading ? "Добавление..." : "Добавить товар"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ---- PromotionModal ---- */
const PROMO_PRICE_PER_DAY = 150;

function PromotionModal({ product, userId, onClose, onDone }: {
  product: MyProduct; userId: string; onClose: () => void; onDone: (p: MyProduct) => void;
}) {
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(false);
  const price = days * PROMO_PRICE_PER_DAY;
  const boost = +(Math.min(0.1 + days * 0.02, 0.5).toFixed(2));

  async function confirm() {
    setLoading(true);
    try {
      const updated = await api.activatePromotion(product.id, { days, creator_user_id: userId });
      onDone(updated as unknown as MyProduct);
    } catch { setLoading(false); }
  }

  return (
    <div onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", display: "flex", alignItems: "center", justifyContent: "center", padding: 16, zIndex: 1002 }}>
      <div style={{ background: "#fff", borderRadius: 10, boxShadow: "0 8px 40px rgba(0,0,0,.25)", width: "100%", maxWidth: 440 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 20px", borderBottom: "1px solid #D4DBE6" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Zap size={16} color="#F67319" />
            <span style={{ fontWeight: 700, fontSize: 15, color: "#1A1A1A" }}>Продвижение товара</span>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#8C8C8C" }}><X size={16} /></button>
        </div>
        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ background: "#E7EEF7", borderRadius: 6, padding: "10px 14px" }}>
            <div style={{ fontWeight: 600, fontSize: 13, color: "#1A1A1A" }}>{product.name}</div>
            {product.category && <div style={{ fontSize: 12, color: "#8C8C8C", marginTop: 2 }}>{product.category}</div>}
          </div>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A" }}>Срок продвижения</label>
              <span style={{ fontSize: 14, fontWeight: 700, color: "#264B82" }}>{days} {days === 1 ? "день" : days < 5 ? "дня" : "дней"}</span>
            </div>
            <input type="range" min={1} max={30} value={days} onChange={e => setDays(Number(e.target.value))}
              style={{ width: "100%", accentColor: "#264B82", cursor: "pointer" }} />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#8C8C8C", marginTop: 2 }}>
              <span>1 день</span><span>30 дней</span>
            </div>
          </div>
          <div style={{ background: "#FEF3EB", borderRadius: 6, padding: "12px 14px", display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
              <span style={{ color: "#7F8792" }}>Буст в поиске</span>
              <span style={{ fontWeight: 700, color: "#F67319" }}>+{(boost * 100).toFixed(0)}%</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
              <span style={{ color: "#7F8792" }}>Стоимость</span>
              <span style={{ fontWeight: 700, color: "#1A1A1A" }}>{price.toLocaleString("ru-RU")} ₽</span>
            </div>
            <div style={{ fontSize: 11, color: "#F67319", marginTop: 2 }}>
              Товар будет отображаться в топе по релевантным запросам
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button onClick={onClose} style={{ padding: "8px 18px", border: "1px solid #D4DBE6", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13 }}>Отмена</button>
            <button onClick={confirm} disabled={loading} style={{ padding: "8px 20px", border: "none", borderRadius: 4, background: loading ? "#a3bfe0" : "#F67319", color: "#fff", cursor: loading ? "default" : "pointer", fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
              <Zap size={13} /> {loading ? "Обработка..." : `Активировать за ${price.toLocaleString("ru-RU")} ₽`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---- MyProductsPanel ---- */
function MyProductsPanel({ products, userId, onClose, onPromote, onProductsChange }: {
  products: MyProduct[]; userId: string; onClose: () => void;
  onPromote: (p: MyProduct) => void;
  onProductsChange: (pp: MyProduct[]) => void;
}) {
  useEffect(() => {
    api.getMyProducts(userId).then(onProductsChange).catch(() => {});
  }, [userId]);

  const now = new Date();

  return (
    <div onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", display: "flex", alignItems: "center", justifyContent: "center", padding: 16, zIndex: 1001 }}>
      <div style={{ background: "#fff", borderRadius: 10, boxShadow: "0 8px 40px rgba(0,0,0,.25)", width: "100%", maxWidth: 560, maxHeight: "80vh", overflow: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 20px", borderBottom: "1px solid #D4DBE6", position: "sticky", top: 0, background: "#fff", zIndex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Package size={16} color="#264B82" />
            <span style={{ fontWeight: 700, fontSize: 15, color: "#1A1A1A" }}>Мои товары</span>
            {products.length > 0 && <span style={{ fontSize: 12, color: "#8C8C8C", background: "#E7EEF7", borderRadius: 20, padding: "1px 8px" }}>{products.length}</span>}
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#8C8C8C" }}><X size={16} /></button>
        </div>
        <div style={{ padding: 16 }}>
          {products.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 20px", color: "#8C8C8C" }}>
              <div style={{ marginBottom: 12 }}><Package size={40} color="#D4DBE6" /></div>
              <p style={{ fontSize: 14, fontWeight: 500, color: "#1A1A1A" }}>У вас нет добавленных товаров</p>
              <p style={{ fontSize: 13 }}>Нажмите «Добавить товар» чтобы разместить свой товар в каталоге</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {products.map(p => {
                const isActive = p.is_promoted && p.promoted_until && new Date(p.promoted_until) > now;
                const daysLeft = isActive && p.promoted_until
                  ? Math.ceil((new Date(p.promoted_until).getTime() - now.getTime()) / 86400000) : 0;
                return (
                  <div key={p.id} style={{ border: `1px solid ${isActive ? "#F67319" : "#D4DBE6"}`, borderRadius: 6, padding: "12px 14px", background: isActive ? "#FFFDF7" : "#fff" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: 14, color: "#1A1A1A" }}>{p.name}</div>
                        {p.category && <div style={{ fontSize: 12, color: "#8C8C8C", marginTop: 2 }}>{p.category}</div>}
                        {p.tags && p.tags.length > 0 && (
                          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
                            {p.tags.map(t => <span key={t} style={{ fontSize: 11, background: "#E7EEF7", color: "#264B82", borderRadius: 20, padding: "2px 8px" }}>{t}</span>)}
                          </div>
                        )}
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6, flexShrink: 0 }}>
                        <span style={{ fontSize: 12, color: "#7F8792" }}>Заказов: <strong style={{ color: "#1A1A1A" }}>{p.order_count ?? 0}</strong></span>
                        {isActive ? (
                          <span style={{ fontSize: 11, background: "#FEF3EB", color: "#F67319", borderRadius: 3, padding: "3px 8px", fontWeight: 600, display: "flex", alignItems: "center", gap: 3 }}>
                            <Zap size={10} /> Продвижение: {daysLeft} дн.
                          </span>
                        ) : (
                          <button onClick={() => onPromote(p)}
                            style={{ fontSize: 12, background: "#264B82", border: "none", color: "#fff", borderRadius: 3, padding: "5px 10px", cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontWeight: 600 }}>
                            <Zap size={11} /> Продвинуть
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
