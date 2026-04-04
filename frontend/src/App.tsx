import {
  useCallback, useEffect, useRef, useState,
  type CSSProperties, type FormEvent, type ReactNode,
} from "react";
import { api, STEResult, SearchResponse, CategoryFacet } from "./api/client";
import {
  Search, LogOut, ChevronRight, ChevronDown, Loader2, PackageSearch,
  ThumbsDown, GitCompare, X, SlidersHorizontal, ArrowUpDown, Clock, Star
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
  const [user, setUser] = useState<User | null>(null);
  if (!user) return <Onboarding onDone={setUser} />;
  return <Main user={user} onLogout={() => setUser(null)} />;
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
function Main({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [query, setQuery] = useState("");
  const [inputVal, setInputVal] = useState("");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [modalItem, setModalItem] = useState<STEResult | null>(null);
  const [sortBy, setSortBy] = useState("relevance");
  const [category, setCategory] = useState<string | null>(null);
  const [facets, setFacets] = useState<CategoryFacet[]>([]);
  const [showFilters, setShowFilters] = useState(true);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [history] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem("sh") || "[]"); } catch { return []; }
  });
  const [sessionId] = useState(() => `s_${Date.now()}`);
  const suggestTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestRef = useRef<HTMLDivElement>(null);

  useEffect(() => { api.facets().then(r => setFacets(r.categories)).catch(() => {}); }, []);

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

  function trackAction(steId: number, action: string) {
    api.logEvent(user.id, steId, action, sessionId, query).catch(() => {});
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
          <button onClick={onLogout} style={{ background: "rgba(255,255,255,.15)", border: "none", color: "#fff", padding: "4px 12px", borderRadius: 4, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
            {user.label} <LogOut size={14} />
          </button>
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
                          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                            <span style={{ fontSize: 11, fontWeight: 700, color: "#264B82", background: "#E7EEF7", borderRadius: 3, padding: "1px 6px", fontFamily: "monospace" }}>#{offset + idx + 1}</span>
                            <h3 onClick={() => { trackAction(item.id, "click"); setModalItem(item); }}
                              style={{ fontSize: 14, fontWeight: 600, color: "#1A1A1A", margin: 0, cursor: "pointer", lineHeight: 1.35 }}
                              onMouseEnter={e => (e.currentTarget.style.color = "#264B82")}
                              onMouseLeave={e => (e.currentTarget.style.color = "#1A1A1A")}
                            >{item.name}</h3>
                          </div>
                          {item.category && <p style={{ fontSize: 12, color: "#8C8C8C", margin: "2px 0 0" }}>{item.category}</p>}
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
                          <span style={{ fontSize: 10, fontFamily: "monospace", color: "#8C8C8C", background: "#E7EEF7", borderRadius: 3, padding: "2px 6px" }}>ID {item.id}</span>
                          <span style={{ fontSize: 10, fontFamily: "monospace", color: "#264B82" }}>score: {item.score.toFixed(3)}</span>
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
                      <Btn onClick={() => { trackAction(item.id, "click"); setModalItem(item); }} color="#264B82"><ChevronRight size={12} /> Подробнее</Btn>
                      <Btn onClick={() => trackAction(item.id, "compare")} color="#8C8C8C"><GitCompare size={12} /> Сравнить</Btn>
                      <Btn onClick={() => trackAction(item.id, "like")} color="#0D9B68"><Star size={12} /> Нравится</Btn>
                      <button onClick={() => trackAction(item.id, "hide")}
                        style={{ background: "none", border: "none", color: "#C9D1DF", fontSize: 12, cursor: "pointer", padding: "4px 8px", borderRadius: 4, marginLeft: "auto" }}
                        onMouseEnter={e => { e.currentTarget.style.color = "#DB2B21"; e.currentTarget.style.background = "#FDECEA"; }}
                        onMouseLeave={e => { e.currentTarget.style.color = "#C9D1DF"; e.currentTarget.style.background = "none"; }}
                      ><ThumbsDown size={12} /></button>
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

      {/* MODAL */}
      {modalItem && <DetailModal item={modalItem} onClose={() => setModalItem(null)} trackAction={trackAction} />}

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

function DetailModal({ item, onClose, trackAction }: { item: STEResult; onClose: () => void; trackAction: (id: number, a: string) => void }) {
  const openedAt = useRef(Date.now());

  function handleClose() {
    const elapsed = Date.now() - openedAt.current;
    // Closed in under 4s without any positive action = bounce signal
    if (elapsed < 4000) trackAction(item.id, "bounce");
    onClose();
  }

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
          {item.attributes && Object.keys(item.attributes).length > 0 && (
            <div>
              <p style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", marginBottom: 8 }}>Характеристики</p>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                <tbody>
                  {Object.entries(item.attributes).map(([k, v]) => (
                    <tr key={k} style={{ borderBottom: "1px solid #E7EEF7" }}>
                      <td style={{ padding: "6px 8px 6px 0", fontWeight: 500, color: "#1A1A1A", width: "45%" }}>{k}</td>
                      <td style={{ padding: "6px 0", color: "#8C8C8C" }}>{String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <div style={{ padding: "14px 20px", borderTop: "1px solid #D4DBE6", display: "flex", gap: 8 }}>
          <button onClick={() => { trackAction(item.id, "like"); }}
            style={{ padding: "8px 16px", border: "1px solid #0D9B68", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13, color: "#0D9B68", display: "flex", alignItems: "center", gap: 4 }}
          ><Star size={14} /> Нравится</button>
          <button onClick={() => { trackAction(item.id, "compare"); }}
            style={{ padding: "8px 16px", border: "1px solid #D4DBE6", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13, display: "flex", alignItems: "center", gap: 4 }}
          ><GitCompare size={14} /> Сравнить</button>
          <button onClick={() => { trackAction(item.id, "hide"); handleClose(); }}
            style={{ marginLeft: "auto", padding: "8px 16px", border: "1px solid rgba(219,43,33,.3)", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13, color: "#DB2B21", display: "flex", alignItems: "center", gap: 4 }}
          ><ThumbsDown size={14} /> Скрыть</button>
        </div>
      </div>
    </div>
  );
}
