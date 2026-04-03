import { useCallback, useEffect, useState } from "react";
import { api, STEResult, SearchResponse } from "./api/client";
import {
  Search, LogOut, ChevronRight, Loader2, PackageSearch,
  ThumbsDown, GitCompare, HelpCircle, Clock, X
} from "lucide-react";

/* ---------- constants ---------- */
const PAGE_SIZE = 20;
const INDUSTRIES = ["Образование","Здравоохранение","Строительство","IT и связь","ЖКХ","Транспорт","Культура и спорт","Промышленность","Другое"];
const DEMO_USERS = [
  { inn: "7701234567", name: "Школа №1234", industry: "Образование" },
  { inn: "7709876543", name: "Городская больница №5", industry: "Здравоохранение" },
  { inn: "7705551234", name: "СтройМонтаж", industry: "Строительство" },
];
const POPULAR = ["бумага офисная","картридж","компьютер","стул офисный"];
const BADGE: Record<string,string> = {
  history:"background:#E6F7F1;color:#0D9B68", category:"background:#E5F4F5;color:#167C85",
  session:"background:#FEF3EB;color:#F67319", popularity:"background:#F3E8FF;color:#7C3AED",
};

interface User { inn: string; name: string; industry: string }

/* ============================================================
   ROOT
   ============================================================ */
export default function App() {
  const [user, setUser] = useState<User | null>(null);

  if (!user) return <Onboarding onDone={setUser} />;
  return <Main user={user} onLogout={() => setUser(null)} />;
}

/* ============================================================
   ONBOARDING
   ============================================================ */
function Onboarding({ onDone }: { onDone: (u: User) => void }) {
  const [inn, setInn] = useState("");
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (inn && industry) {
      api.onboard(inn, name, undefined, industry).catch(() => {});
      onDone({ inn, name, industry });
    }
  }

  function pick(u: User) {
    api.onboard(u.inn, u.name, undefined, u.industry).catch(() => {});
    onDone(u);
  }

  return (
    <div style={{ minHeight: "100vh", background: "#E7EEF7", display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
      <div style={{ background: "#fff", borderRadius: 8, boxShadow: "0 4px 24px rgba(0,0,0,.12)", width: "100%", maxWidth: 420, overflow: "hidden" }}>
        {/* Header */}
        <div style={{ background: "#264B82", padding: "20px 24px", color: "#fff" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <div style={{ width: 28, height: 28, background: "#fff", borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center", color: "#264B82", fontWeight: 900, fontSize: 12 }}>П</div>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Портал поставщиков</span>
          </div>
          <div style={{ fontWeight: 700, fontSize: 18 }}>Персонализация поиска</div>
          <div style={{ fontSize: 13, color: "#a3bfe0", marginTop: 4 }}>Укажите данные — система подберёт товары</div>
        </div>

        {/* Form */}
        <form onSubmit={submit} style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
          <label style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A" }}>
            ИНН организации *
            <input value={inn} onChange={e => setInn(e.target.value.replace(/\D/g,"").slice(0,12))} placeholder="7701234567" required
              style={{ display: "block", width: "100%", marginTop: 4, padding: "8px 12px", border: "1px solid #D4DBE6", borderRadius: 4, fontSize: 14, outline: "none" }}
            />
          </label>
          <label style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A" }}>
            Название
            <input value={name} onChange={e => setName(e.target.value)} placeholder="ГБОУ Школа №1234"
              style={{ display: "block", width: "100%", marginTop: 4, padding: "8px 12px", border: "1px solid #D4DBE6", borderRadius: 4, fontSize: 14, outline: "none" }}
            />
          </label>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A", marginBottom: 8 }}>Сфера деятельности *</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {INDUSTRIES.map(ind => (
                <button type="button" key={ind} onClick={() => setIndustry(ind)}
                  style={{
                    padding: "6px 12px", borderRadius: 4, fontSize: 13, border: "1px solid",
                    borderColor: industry === ind ? "#264B82" : "#D4DBE6",
                    background: industry === ind ? "#264B82" : "#fff",
                    color: industry === ind ? "#fff" : "#1A1A1A",
                    cursor: "pointer",
                  }}
                >{ind}</button>
              ))}
            </div>
          </div>
          <button type="submit" disabled={!inn || !industry}
            style={{ padding: "10px 0", borderRadius: 4, border: "none", background: (!inn || !industry) ? "#a3bfe0" : "#264B82", color: "#fff", fontWeight: 600, fontSize: 14, cursor: (!inn || !industry) ? "default" : "pointer" }}
          >Начать поиск</button>
        </form>

        {/* Demo */}
        <div style={{ padding: "0 24px 20px" }}>
          <div style={{ fontSize: 11, color: "#8C8C8C", fontWeight: 600, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Демо-пользователи</div>
          {DEMO_USERS.map(u => (
            <button key={u.inn} onClick={() => pick(u)}
              style={{ display: "flex", justifyContent: "space-between", width: "100%", padding: "8px 12px", border: "none", background: "transparent", borderRadius: 4, cursor: "pointer", textAlign: "left", fontSize: 14 }}
              onMouseEnter={e => (e.currentTarget.style.background = "#E7EEF7")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              <span style={{ fontWeight: 500, color: "#1A1A1A" }}>{u.name}</span>
              <span style={{ fontSize: 12, color: "#8C8C8C" }}>{u.industry}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   MAIN PAGE
   ============================================================ */
function Main({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [query, setQuery] = useState("");
  const [inputVal, setInputVal] = useState("");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [modalItem, setModalItem] = useState<STEResult | null>(null);
  const [history, setHistory] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem("sh") || "[]"); } catch { return []; }
  });

  const doSearch = useCallback(async (q: string, off = 0) => {
    if (!q.trim()) return;
    setQuery(q); setOffset(off); setLoading(true);
    const h = [q, ...history.filter(x => x !== q)].slice(0, 5);
    setHistory(h);
    localStorage.setItem("sh", JSON.stringify(h));
    try {
      const data = await api.search(q, user.inn, `s_${Date.now()}`, PAGE_SIZE, off);
      setResponse(data);
    } catch {
      setResponse({ query: q, corrected_query: null, did_you_mean: null, total: 0, results: [] });
    } finally { setLoading(false); }
  }, [user.inn, history]);

  function trackAction(steId: number, action: string) {
    api.logEvent(user.inn, steId, action, `s_${Date.now()}`, query).catch(() => {});
  }

  return (
    <div style={{ minHeight: "100vh", background: "#E7EEF7" }}>
      {/* HEADER */}
      <header style={{ background: "#264B82", color: "#fff" }}>
        <div style={{ maxWidth: 960, margin: "0 auto", padding: "0 16px", height: 48, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 24, height: 24, background: "#fff", borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center", color: "#264B82", fontWeight: 900, fontSize: 10 }}>П</div>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Портал поставщиков</span>
            <span style={{ color: "#a3bfe0", fontSize: 12, marginLeft: 4 }}>/ Умный поиск</span>
          </div>
          <button onClick={onLogout} style={{ background: "rgba(255,255,255,.15)", border: "none", color: "#fff", padding: "4px 12px", borderRadius: 4, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
            {user.name || user.inn} <LogOut size={14} />
          </button>
        </div>
      </header>

      {/* SEARCH BAR */}
      <div style={{ background: "#fff", borderBottom: "1px solid #D4DBE6" }}>
        <div style={{ maxWidth: 960, margin: "0 auto", padding: "20px 16px" }}>
          <h1 style={{ fontSize: 18, fontWeight: 700, color: "#1A1A1A", margin: "0 0 4px" }}>Каталог товаров СТЕ</h1>
          <p style={{ fontSize: 13, color: "#8C8C8C", margin: "0 0 16px" }}>{user.industry} · ИНН {user.inn}</p>
          <form onSubmit={e => { e.preventDefault(); doSearch(inputVal); }} style={{ display: "flex", gap: 8 }}>
            <div style={{ flex: 1, position: "relative" }}>
              <Search size={16} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#8C8C8C" }} />
              <input value={inputVal} onChange={e => setInputVal(e.target.value)} placeholder="Поиск по каталогу СТЕ..."
                style={{ width: "100%", padding: "10px 36px 10px 36px", border: "2px solid #D4DBE6", borderRadius: 6, fontSize: 14, outline: "none" }}
                onFocus={e => (e.target.style.borderColor = "#264B82")}
                onBlur={e => (e.target.style.borderColor = "#D4DBE6")}
              />
              {inputVal && (
                <button type="button" onClick={() => setInputVal("")}
                  style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "#8C8C8C" }}>
                  <X size={16} />
                </button>
              )}
            </div>
            <button type="submit"
              style={{ padding: "0 20px", background: "#264B82", color: "#fff", border: "none", borderRadius: 6, fontWeight: 600, fontSize: 14, cursor: "pointer" }}
            >Найти</button>
          </form>
          {response?.corrected_query && (
            <p style={{ marginTop: 8, fontSize: 13, color: "#F67319" }}>Показаны результаты по запросу <strong>«{response.corrected_query}»</strong></p>
          )}
        </div>
      </div>

      {/* CONTENT */}
      <div style={{ maxWidth: 960, margin: "0 auto", padding: "20px 16px" }}>

        {/* Loading */}
        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: 40, justifyContent: "center", color: "#8C8C8C" }}>
            <Loader2 size={20} className="animate-spin" /> Поиск...
          </div>
        )}

        {/* Results */}
        {!loading && response && response.results.length > 0 && (
          <>
            <p style={{ fontSize: 13, color: "#8C8C8C", marginBottom: 12 }}>
              Найдено <strong style={{ color: "#1A1A1A" }}>{response.total}</strong> результатов по запросу «{response.query}»
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(280px,1fr))", gap: 12 }}>
              {response.results.map(item => (
                <div key={item.id} style={{ background: "#fff", border: "1px solid #D4DBE6", borderRadius: 6, display: "flex", flexDirection: "column" }}>
                  <div style={{ padding: 16, flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <h3 onClick={() => { trackAction(item.id, "click"); setModalItem(item); }}
                        style={{ fontSize: 14, fontWeight: 600, color: "#1A1A1A", margin: 0, cursor: "pointer", lineHeight: 1.3 }}
                        onMouseEnter={e => (e.currentTarget.style.color = "#264B82")}
                        onMouseLeave={e => (e.currentTarget.style.color = "#1A1A1A")}
                      >{item.name}</h3>
                      <span style={{ fontSize: 10, fontFamily: "monospace", color: "#8C8C8C", background: "#E7EEF7", borderRadius: 3, padding: "2px 6px", whiteSpace: "nowrap", height: "fit-content" }}>{item.id}</span>
                    </div>
                    {item.category && <p style={{ fontSize: 12, color: "#8C8C8C", margin: "4px 0 0" }}>{item.category}</p>}
                    {item.explanations.length > 0 && (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
                        {item.explanations.slice(0, 2).map((e, i) => (
                          <span key={i} style={{ fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 3, ...(BADGE[e.factor] ? Object.fromEntries(BADGE[e.factor].split(";").map(s => { const [k,v] = s.split(":"); return [k,v]; })) : { background: "#E7EEF7", color: "#8C8C8C" }) }}>{e.reason}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div style={{ padding: "8px 16px", borderTop: "1px solid #E7EEF7", display: "flex", alignItems: "center", gap: 4 }}>
                    <button onClick={() => { trackAction(item.id, "click"); setModalItem(item); }}
                      style={{ background: "none", border: "none", color: "#264B82", fontSize: 12, fontWeight: 600, cursor: "pointer", padding: "4px 8px", borderRadius: 4, display: "flex", alignItems: "center", gap: 4 }}
                      onMouseEnter={e => (e.currentTarget.style.background = "#E7EEF7")}
                      onMouseLeave={e => (e.currentTarget.style.background = "none")}
                    >Подробнее <ChevronRight size={12} /></button>
                    <button onClick={() => trackAction(item.id, "compare")}
                      style={{ background: "none", border: "none", color: "#8C8C8C", fontSize: 12, cursor: "pointer", padding: "4px 8px", borderRadius: 4, display: "flex", alignItems: "center", gap: 4 }}
                      onMouseEnter={e => (e.currentTarget.style.background = "#E7EEF7")}
                      onMouseLeave={e => (e.currentTarget.style.background = "none")}
                    ><GitCompare size={12} /> Сравнить</button>
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
              <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 20 }}>
                <button disabled={offset === 0} onClick={() => doSearch(query, Math.max(0, offset - PAGE_SIZE))}
                  style={{ padding: "8px 16px", border: "1px solid #D4DBE6", borderRadius: 4, background: "#fff", cursor: offset === 0 ? "default" : "pointer", opacity: offset === 0 ? 0.4 : 1, fontSize: 13 }}
                >Назад</button>
                <span style={{ padding: "8px 12px", fontSize: 13, color: "#8C8C8C" }}>{Math.floor(offset / PAGE_SIZE) + 1} / {Math.ceil(response.total / PAGE_SIZE)}</span>
                <button disabled={offset + PAGE_SIZE >= response.total} onClick={() => doSearch(query, offset + PAGE_SIZE)}
                  style={{ padding: "8px 16px", border: "1px solid #D4DBE6", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13 }}
                >Далее</button>
              </div>
            )}
          </>
        )}

        {/* Empty results */}
        {!loading && response && response.results.length === 0 && (
          <div style={{ textAlign: "center", padding: "60px 0" }}>
            <PackageSearch size={48} style={{ color: "#D4DBE6", margin: "0 auto 12px" }} />
            <p style={{ fontSize: 16, fontWeight: 600, color: "#1A1A1A" }}>По запросу «{query}» ничего не найдено</p>
            <p style={{ fontSize: 13, color: "#8C8C8C", marginTop: 4 }}>Попробуйте другой запрос</p>
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 8, marginTop: 16 }}>
              {POPULAR.map(q => (
                <button key={q} onClick={() => { setInputVal(q); doSearch(q); }}
                  style={{ padding: "6px 14px", border: "1px solid #D4DBE6", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13 }}
                  onMouseEnter={e => { e.currentTarget.style.background = "#264B82"; e.currentTarget.style.color = "#fff"; e.currentTarget.style.borderColor = "#264B82"; }}
                  onMouseLeave={e => { e.currentTarget.style.background = "#fff"; e.currentTarget.style.color = "#1A1A1A"; e.currentTarget.style.borderColor = "#D4DBE6"; }}
                >{q}</button>
              ))}
            </div>
          </div>
        )}

        {/* Initial state */}
        {!loading && !response && (
          <div style={{ textAlign: "center", padding: "60px 0" }}>
            <Search size={48} style={{ color: "#D4DBE6", margin: "0 auto 12px" }} />
            <p style={{ fontSize: 16, color: "#1A1A1A" }}>Начните вводить название товара</p>
            <p style={{ fontSize: 13, color: "#8C8C8C", marginTop: 4, marginBottom: 16 }}>Система учтёт ваш профиль и историю закупок</p>
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 8 }}>
              {POPULAR.map(q => (
                <button key={q} onClick={() => { setInputVal(q); doSearch(q); }}
                  style={{ padding: "6px 14px", border: "1px solid #D4DBE6", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13 }}
                  onMouseEnter={e => { e.currentTarget.style.background = "#264B82"; e.currentTarget.style.color = "#fff"; e.currentTarget.style.borderColor = "#264B82"; }}
                  onMouseLeave={e => { e.currentTarget.style.background = "#fff"; e.currentTarget.style.color = "#1A1A1A"; e.currentTarget.style.borderColor = "#D4DBE6"; }}
                >{q}</button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* MODAL */}
      {modalItem && (
        <div onClick={e => { if (e.target === e.currentTarget) setModalItem(null); }}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", display: "flex", alignItems: "center", justifyContent: "center", padding: 16, zIndex: 999 }}>
          <div style={{ background: "#fff", borderRadius: 8, boxShadow: "0 8px 40px rgba(0,0,0,.2)", width: "100%", maxWidth: 480, maxHeight: "90vh", overflow: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: 20, borderBottom: "1px solid #D4DBE6" }}>
              <div>
                <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1A1A1A", margin: 0 }}>{modalItem.name}</h2>
                {modalItem.category && <p style={{ fontSize: 13, color: "#8C8C8C", margin: "4px 0 0" }}>{modalItem.category}</p>}
              </div>
              <button onClick={() => setModalItem(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#8C8C8C", padding: 4 }}><X size={18} /></button>
            </div>
            <div style={{ padding: 20 }}>
              <span style={{ fontSize: 11, fontFamily: "monospace", color: "#8C8C8C", background: "#E7EEF7", borderRadius: 3, padding: "3px 8px" }}>ID: {modalItem.id}</span>
              {modalItem.explanations.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <p style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", marginBottom: 8 }}>Почему этот результат</p>
                  {modalItem.explanations.map((e, i) => (
                    <p key={i} style={{ fontSize: 14, color: "#1A1A1A", margin: "4px 0", paddingLeft: 12, borderLeft: "3px solid #264B82" }}>{e.reason}</p>
                  ))}
                </div>
              )}
              {modalItem.attributes && Object.keys(modalItem.attributes).length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <p style={{ fontSize: 11, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", marginBottom: 8 }}>Характеристики</p>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                    <tbody>
                      {Object.entries(modalItem.attributes).map(([k, v]) => (
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
            <div style={{ padding: 20, borderTop: "1px solid #D4DBE6", display: "flex", gap: 8 }}>
              <button onClick={() => { trackAction(modalItem.id, "compare"); setModalItem(null); }}
                style={{ padding: "8px 16px", border: "1px solid #D4DBE6", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13, display: "flex", alignItems: "center", gap: 4 }}
              ><GitCompare size={14} /> Сравнить</button>
              <button onClick={() => { trackAction(modalItem.id, "hide"); setModalItem(null); }}
                style={{ marginLeft: "auto", padding: "8px 16px", border: "1px solid rgba(219,43,33,.3)", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 13, color: "#DB2B21", display: "flex", alignItems: "center", gap: 4 }}
              ><ThumbsDown size={14} /> Скрыть</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
