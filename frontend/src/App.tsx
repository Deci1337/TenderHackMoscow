import { useCallback, useState } from "react";
import { api, STEResult } from "./api/client";
import { useEvents } from "./hooks/useEvents";
import { useSearch } from "./hooks/useSearch";
import { Search, LogOut, ChevronRight, Loader2, PackageSearch, ThumbsDown, GitCompare, HelpCircle, Clock, X } from "lucide-react";

const PAGE_SIZE = 20;

const INDUSTRIES = [
  "Образование", "Здравоохранение", "Строительство", "IT и связь",
  "ЖКХ", "Транспорт", "Культура и спорт", "Промышленность", "Другое",
];

const DEMO_USERS = [
  { inn: "7701234567", name: "Школа №1234", industry: "Образование" },
  { inn: "7709876543", name: "Городская больница №5", industry: "Здравоохранение" },
  { inn: "7705551234", name: "СтройМонтаж", industry: "Строительство" },
];

const POPULAR_QUERIES = ["бумага офисная", "картридж", "компьютер", "стул офисный"];

interface User { inn: string; name: string; industry: string }

/* ============================== APP ============================== */

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [sessionId] = useState(() => `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`);

  if (!user) return <Onboarding onDone={setUser} />;
  return <MainPage user={user} sessionId={sessionId} onLogout={() => setUser(null)} />;
}

/* ========================== ONBOARDING =========================== */

function Onboarding({ onDone }: { onDone: (u: User) => void }) {
  const [inn, setInn] = useState("");
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inn || !industry) return;
    api.onboard(inn, name, undefined, industry).catch(() => {});
    onDone({ inn, name, industry });
  };

  const pick = (u: typeof DEMO_USERS[0]) => {
    api.onboard(u.inn, u.name, undefined, u.industry).catch(() => {});
    onDone(u);
  };

  return (
    <div className="min-h-screen bg-[#E7EEF7] flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg w-full max-w-md overflow-hidden">
        <div className="bg-[#264B82] px-6 py-5 text-white">
          <div className="flex items-center gap-2 text-sm font-semibold mb-3">
            <div className="w-7 h-7 bg-white rounded flex items-center justify-center text-[#264B82] font-black text-xs">П</div>
            Портал поставщиков
          </div>
          <h2 className="text-lg font-bold">Персонализация поиска</h2>
          <p className="text-blue-200 text-sm mt-1">Укажите данные — система подберёт релевантные товары</p>
        </div>

        <form onSubmit={submit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#1A1A1A] mb-1">ИНН организации *</label>
            <input
              value={inn}
              onChange={e => setInn(e.target.value.replace(/\D/g, "").slice(0, 12))}
              placeholder="7701234567"
              required
              className="w-full px-3 py-2 border border-[#D4DBE6] rounded text-sm focus:border-[#264B82] focus:ring-2 focus:ring-[#264B82]/20 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[#1A1A1A] mb-1">Название</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="ГБОУ Школа №1234"
              className="w-full px-3 py-2 border border-[#D4DBE6] rounded text-sm focus:border-[#264B82] focus:ring-2 focus:ring-[#264B82]/20 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[#1A1A1A] mb-1.5">Сфера деятельности *</label>
            <div className="flex flex-wrap gap-2">
              {INDUSTRIES.map(ind => (
                <button
                  type="button"
                  key={ind}
                  onClick={() => setIndustry(ind)}
                  className={`px-3 py-1.5 rounded text-sm border transition-all ${
                    industry === ind
                      ? "bg-[#264B82] text-white border-[#264B82]"
                      : "bg-white text-[#1A1A1A] border-[#D4DBE6] hover:border-[#264B82]"
                  }`}
                >
                  {ind}
                </button>
              ))}
            </div>
          </div>
          <button
            type="submit"
            disabled={!inn || !industry}
            className="w-full bg-[#264B82] hover:bg-[#1C3A6B] disabled:opacity-40 text-white font-semibold py-2.5 rounded text-sm transition-colors"
          >
            Начать поиск
          </button>
        </form>

        <div className="px-6 pb-5 pt-0">
          <p className="text-xs text-[#8C8C8C] mb-2 font-medium uppercase tracking-wide">Демо</p>
          {DEMO_USERS.map(u => (
            <button
              key={u.inn}
              onClick={() => pick(u)}
              className="w-full text-left text-sm px-3 py-2 rounded hover:bg-[#E7EEF7] transition-colors flex justify-between"
            >
              <span className="font-medium text-[#1A1A1A]">{u.name}</span>
              <span className="text-xs text-[#8C8C8C]">{u.industry}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ========================== MAIN PAGE ============================ */

function MainPage({ user, sessionId, onLogout }: { user: User; sessionId: string; onLogout: () => void }) {
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [modalItem, setModalItem] = useState<STEResult | null>(null);
  const { response, loading, search } = useSearch(user.inn, sessionId);
  const { trackClick, trackBounce, track } = useEvents(user.inn, sessionId);

  const doSearch = useCallback((q: string, off = 0) => {
    setQuery(q);
    setOffset(off);
    search(q, off, PAGE_SIZE);
  }, [search]);

  const handleAction = useCallback((steId: number, action: string) => {
    if (action === "click") { trackClick(steId, query); setTimeout(() => trackBounce(steId, query), 2500); }
    else track(steId, action, query);
  }, [track, trackClick, trackBounce, query]);

  return (
    <div className="min-h-screen bg-[#E7EEF7]">
      {/* HEADER */}
      <header className="bg-[#264B82]">
        <div className="max-w-6xl mx-auto px-4 h-12 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-white rounded flex items-center justify-center text-[#264B82] font-black text-[10px]">П</div>
            <span className="text-white font-semibold text-sm">Портал поставщиков</span>
            <span className="text-blue-300 text-xs ml-1 hidden sm:inline">/ Умный поиск СТЕ</span>
          </div>
          <button onClick={onLogout} className="flex items-center gap-1.5 text-blue-200 hover:text-white text-xs transition-colors">
            <span className="hidden sm:inline">{user.name || user.inn}</span>
            <LogOut size={14} />
          </button>
        </div>
      </header>

      {/* SEARCH SECTION */}
      <div className="bg-white border-b border-[#D4DBE6]">
        <div className="max-w-6xl mx-auto px-4 py-5">
          <h1 className="text-lg font-bold text-[#1A1A1A] mb-1">Каталог товаров СТЕ</h1>
          <p className="text-sm text-[#8C8C8C] mb-4">
            Персонализированный поиск · {user.industry} · ИНН {user.inn}
          </p>
          <SearchInput onSearch={q => doSearch(q, 0)} loading={loading} corrected={response?.corrected_query || null} />
        </div>
      </div>

      {/* RESULTS */}
      <div className="max-w-6xl mx-auto px-4 py-5">
        {loading && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-white rounded border border-[#D4DBE6] p-4 animate-pulse">
                <div className="h-4 bg-[#E7EEF7] rounded w-3/4 mb-2" />
                <div className="h-3 bg-[#E7EEF7] rounded w-1/2 mb-3" />
                <div className="h-3 bg-[#E7EEF7] rounded w-full" />
              </div>
            ))}
          </div>
        )}

        {!loading && response && response.results.length > 0 && (
          <>
            <p className="text-sm text-[#8C8C8C] mb-3">
              Найдено <span className="font-semibold text-[#1A1A1A]">{response.total}</span> результатов
              по запросу «{response.query}»
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {response.results.map(item => (
                <Card key={item.id} item={item} onAction={handleAction} onOpen={() => { handleAction(item.id, "click"); setModalItem(item); }} />
              ))}
            </div>
            {response.total > PAGE_SIZE && (
              <div className="flex justify-center gap-2 mt-5">
                <button
                  disabled={offset === 0}
                  onClick={() => doSearch(query, Math.max(0, offset - PAGE_SIZE))}
                  className="px-4 py-2 text-sm border border-[#D4DBE6] rounded bg-white hover:bg-[#E7EEF7] disabled:opacity-40 transition-colors"
                >
                  Назад
                </button>
                <span className="px-3 py-2 text-sm text-[#8C8C8C]">
                  {Math.floor(offset / PAGE_SIZE) + 1} / {Math.ceil(response.total / PAGE_SIZE)}
                </span>
                <button
                  disabled={offset + PAGE_SIZE >= response.total}
                  onClick={() => doSearch(query, offset + PAGE_SIZE)}
                  className="px-4 py-2 text-sm border border-[#D4DBE6] rounded bg-white hover:bg-[#E7EEF7] disabled:opacity-40 transition-colors"
                >
                  Далее
                </button>
              </div>
            )}
          </>
        )}

        {!loading && response && response.results.length === 0 && (
          <div className="text-center py-16">
            <PackageSearch size={48} className="mx-auto mb-3 text-[#D4DBE6]" />
            <p className="text-lg font-semibold text-[#1A1A1A]">По запросу «{query}» ничего не найдено</p>
            <p className="text-sm text-[#8C8C8C] mt-1 mb-4">Попробуйте другой запрос или выберите из популярных</p>
            <div className="flex flex-wrap justify-center gap-2">
              {POPULAR_QUERIES.map(q => (
                <button key={q} onClick={() => doSearch(q)} className="text-sm px-3 py-1.5 rounded border border-[#D4DBE6] hover:bg-[#264B82] hover:text-white hover:border-[#264B82] transition-colors">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {!loading && !response && (
          <div className="text-center py-16">
            <Search size={48} className="mx-auto mb-3 text-[#D4DBE6]" />
            <p className="text-lg text-[#1A1A1A]">Начните вводить название товара</p>
            <p className="text-sm text-[#8C8C8C] mt-1 mb-4">Система учтёт ваш профиль и историю закупок</p>
            <div className="flex flex-wrap justify-center gap-2">
              {POPULAR_QUERIES.map(q => (
                <button key={q} onClick={() => doSearch(q)} className="text-sm px-3 py-1.5 rounded border border-[#D4DBE6] hover:bg-[#264B82] hover:text-white hover:border-[#264B82] transition-colors">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* MODAL */}
      {modalItem && <DetailModal item={modalItem} onClose={() => setModalItem(null)} onAction={handleAction} />}
    </div>
  );
}

/* ========================= SEARCH INPUT ========================== */

function SearchInput({ onSearch, loading, corrected }: { onSearch: (q: string) => void; loading: boolean; corrected: string | null }) {
  const [val, setVal] = useState("");
  const [history] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem("sh") || "[]"); } catch { return []; }
  });
  const [showHist, setShowHist] = useState(false);

  const submit = (q: string) => {
    if (!q.trim()) return;
    const h = [q, ...history.filter(x => x !== q)].slice(0, 5);
    localStorage.setItem("sh", JSON.stringify(h));
    setShowHist(false);
    onSearch(q.trim());
  };

  return (
    <div className="relative">
      <form onSubmit={e => { e.preventDefault(); submit(val); }}>
        <div className="relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#8C8C8C]" />
          <input
            value={val}
            onChange={e => setVal(e.target.value)}
            onFocus={() => { if (!val && history.length) setShowHist(true); }}
            onBlur={() => setTimeout(() => setShowHist(false), 200)}
            placeholder="Поиск по каталогу СТЕ..."
            className="w-full pl-10 pr-20 py-3 border-2 border-[#D4DBE6] rounded-lg text-sm
                       focus:border-[#264B82] focus:ring-2 focus:ring-[#264B82]/20 outline-none
                       bg-white text-[#1A1A1A] placeholder:text-[#8C8C8C]"
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
            {loading && <Loader2 size={16} className="animate-spin text-[#264B82]" />}
            {val && (
              <button type="button" onClick={() => { setVal(""); }} className="text-[#8C8C8C] hover:text-[#1A1A1A] p-1">
                <X size={16} />
              </button>
            )}
            <button type="submit" className="bg-[#264B82] hover:bg-[#1C3A6B] text-white px-3 py-1.5 rounded text-xs font-medium transition-colors">
              Найти
            </button>
          </div>
        </div>
      </form>

      {showHist && history.length > 0 && (
        <div className="absolute z-30 top-full mt-1 w-full bg-white rounded-lg border border-[#D4DBE6] shadow-lg overflow-hidden">
          <p className="px-3 py-1.5 text-[10px] text-[#8C8C8C] uppercase tracking-wide font-medium border-b border-[#E7EEF7]">Недавние</p>
          {history.map((h, i) => (
            <button key={i} onMouseDown={() => { setVal(h); submit(h); }} className="w-full text-left px-3 py-2 text-sm hover:bg-[#E7EEF7] flex items-center gap-2 transition-colors">
              <Clock size={12} className="text-[#8C8C8C]" /> {h}
            </button>
          ))}
        </div>
      )}

      {corrected && (
        <p className="mt-2 text-sm text-[#F67319]">
          Показаны результаты по запросу <strong>«{corrected}»</strong>
        </p>
      )}
    </div>
  );
}

/* ============================ CARD ================================ */

const BADGE: Record<string, string> = {
  history: "bg-[#E6F7F1] text-[#0D9B68]",
  category: "bg-[#E5F4F5] text-[#167C85]",
  session: "bg-[#FEF3EB] text-[#F67319]",
  popularity: "bg-[#F3E8FF] text-[#7C3AED]",
};

function Card({ item, onAction, onOpen }: { item: STEResult; onAction: (id: number, a: string) => void; onOpen: () => void }) {
  return (
    <div className="bg-white rounded border border-[#D4DBE6] hover:shadow-md transition-shadow flex flex-col">
      <div className="p-4 flex-1">
        <div className="flex justify-between gap-2 mb-1">
          <h3
            className="text-sm font-semibold text-[#1A1A1A] leading-snug line-clamp-2 cursor-pointer hover:text-[#264B82] transition-colors"
            onClick={onOpen}
          >
            {item.name}
          </h3>
          <span className="text-[10px] font-mono text-[#8C8C8C] bg-[#E7EEF7] rounded px-1.5 py-0.5 shrink-0 h-fit">{item.id}</span>
        </div>
        {item.category && <p className="text-xs text-[#8C8C8C] mb-2">{item.category}</p>}

        {item.explanations.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {item.explanations.slice(0, 2).map((e, i) => (
              <span key={i} className={`text-[10px] font-medium px-2 py-0.5 rounded ${BADGE[e.factor] || "bg-[#E7EEF7] text-[#8C8C8C]"}`}>
                {e.reason}
              </span>
            ))}
            {item.explanations.length > 2 && (
              <span className="text-[10px] text-[#8C8C8C] flex items-center gap-0.5"><HelpCircle size={10} />+{item.explanations.length - 2}</span>
            )}
          </div>
        )}

        {item.attributes && Object.keys(item.attributes).length > 0 && (
          <div className="text-[11px] text-[#8C8C8C] flex flex-wrap gap-x-3 gap-y-0.5 border-t border-[#E7EEF7] pt-2">
            {Object.entries(item.attributes).slice(0, 3).map(([k, v]) => (
              <span key={k}><span className="font-medium">{k}:</span> {String(v)}</span>
            ))}
          </div>
        )}
      </div>

      <div className="px-4 py-2 border-t border-[#E7EEF7] flex items-center gap-1 text-xs">
        <button onClick={onOpen} className="text-[#264B82] hover:bg-[#E7EEF7] rounded px-2 py-1 font-medium flex items-center gap-1 transition-colors">
          Подробнее <ChevronRight size={12} />
        </button>
        <button onClick={() => onAction(item.id, "compare")} className="text-[#8C8C8C] hover:bg-[#E7EEF7] rounded px-2 py-1 flex items-center gap-1 transition-colors">
          <GitCompare size={12} /> Сравнить
        </button>
        <button onClick={() => onAction(item.id, "hide")} className="ml-auto text-[#C9D1DF] hover:text-[#DB2B21] rounded px-2 py-1 transition-colors">
          <ThumbsDown size={12} />
        </button>
      </div>
    </div>
  );
}

/* ========================= DETAIL MODAL ========================== */

function DetailModal({ item, onClose, onAction }: { item: STEResult; onClose: () => void; onAction: (id: number, a: string) => void }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-start p-5 border-b border-[#D4DBE6]">
          <div>
            <h2 className="font-bold text-[#1A1A1A] text-base">{item.name}</h2>
            {item.category && <p className="text-sm text-[#8C8C8C] mt-0.5">{item.category}</p>}
          </div>
          <button onClick={onClose} className="text-[#8C8C8C] hover:text-[#1A1A1A] p-1 transition-colors"><X size={18} /></button>
        </div>
        <div className="p-5 space-y-4">
          <p className="text-xs font-mono text-[#8C8C8C] bg-[#E7EEF7] rounded inline-block px-2 py-1">ID: {item.id}</p>

          {item.explanations.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-[#8C8C8C] uppercase mb-1.5">Почему этот результат</p>
              <ul className="space-y-1">
                {item.explanations.map((e, i) => (
                  <li key={i} className="text-sm flex items-start gap-2 text-[#1A1A1A]">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[#264B82] shrink-0" />
                    {e.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {item.attributes && Object.keys(item.attributes).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-[#8C8C8C] uppercase mb-1.5">Характеристики</p>
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(item.attributes).map(([k, v]) => (
                    <tr key={k} className="border-b border-[#E7EEF7]">
                      <td className="py-1.5 pr-3 font-medium text-[#1A1A1A] w-1/2">{k}</td>
                      <td className="py-1.5 text-[#8C8C8C]">{String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <div className="p-5 border-t border-[#D4DBE6] flex gap-2">
          <button onClick={() => { onAction(item.id, "compare"); onClose(); }} className="text-sm px-4 py-2 border border-[#D4DBE6] rounded hover:bg-[#E7EEF7] transition-colors flex items-center gap-1">
            <GitCompare size={14} /> Сравнить
          </button>
          <button onClick={() => { onAction(item.id, "hide"); onClose(); }} className="ml-auto text-sm px-4 py-2 text-[#DB2B21] border border-[#DB2B21]/30 rounded hover:bg-[#FDECEA] transition-colors flex items-center gap-1">
            <ThumbsDown size={14} /> Скрыть
          </button>
        </div>
      </div>
    </div>
  );
}
