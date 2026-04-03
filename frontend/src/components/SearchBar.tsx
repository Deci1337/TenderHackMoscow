import { Clock, Loader2, Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

const HISTORY_KEY = "search_history";
const MAX_HISTORY = 5;

function loadHistory(): string[] {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch { return []; }
}

function saveHistory(query: string) {
  const prev = loadHistory().filter((q) => q !== query);
  localStorage.setItem(HISTORY_KEY, JSON.stringify([query, ...prev].slice(0, MAX_HISTORY)));
}

interface Props {
  onSearch: (query: string) => void;
  loading: boolean;
  correctedQuery: string | null;
  didYouMean: string | null;
}

export default function SearchBar({ onSearch, loading, correctedQuery }: Props) {
  const [value, setValue] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [history, setHistory] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const suggestRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    if (value.trim().length >= 2) {
      debounceRef.current = setTimeout(() => onSearch(value.trim()), 400);
    }
    return () => clearTimeout(debounceRef.current);
  }, [value, onSearch]);

  useEffect(() => {
    clearTimeout(suggestRef.current);
    if (value.trim().length >= 2) {
      suggestRef.current = setTimeout(async () => {
        try {
          const data = await api.suggest(value.trim());
          setSuggestions(data.suggestions);
          setShowSuggestions(data.suggestions.length > 0);
          setShowHistory(false);
        } catch {
          setSuggestions([]);
        }
      }, 200);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
    return () => clearTimeout(suggestRef.current);
  }, [value]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
        setShowHistory(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleFocus = () => {
    if (!value.trim()) {
      const h = loadHistory();
      if (h.length) { setHistory(h); setShowHistory(true); }
    }
  };

  const select = (s: string) => {
    setValue(s);
    setShowSuggestions(false);
    setShowHistory(false);
    saveHistory(s);
    onSearch(s);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setShowSuggestions(false);
    setShowHistory(false);
    if (value.trim()) { saveHistory(value.trim()); onSearch(value.trim()); }
  };

  const handleClear = () => {
    setValue("");
    setSuggestions([]);
    setShowSuggestions(false);
    setShowHistory(false);
    onSearch("");
  };

  const dropdownItems = showSuggestions
    ? suggestions.map((s) => ({ label: s, isHistory: false }))
    : showHistory
    ? history.map((s) => ({ label: s, isHistory: true }))
    : [];

  return (
    <div className="w-full max-w-3xl mx-auto space-y-2">
      <div ref={wrapperRef} className="relative">
        <form onSubmit={handleSubmit}>
          <Search
            className="absolute left-4 top-1/2 -translate-y-1/2 text-portal-text-secondary"
            size={20}
          />
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onFocus={handleFocus}
            placeholder="Введите название товара или СТЕ..."
            className="w-full pl-12 pr-12 py-4 rounded-portal border-2 border-portal-border bg-white
                       text-base text-portal-black focus:border-portal-blue focus:outline-none
                       focus:ring-2 focus:ring-portal-blue/20 shadow-sm transition-all
                       placeholder:text-portal-gray-text"
          />
          {loading && (
            <Loader2
              className="absolute right-12 top-1/2 -translate-y-1/2 text-portal-blue animate-spin"
              size={20}
            />
          )}
          {value && (
            <button
              type="button"
              onClick={handleClear}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-portal-text-secondary hover:text-portal-text transition-colors"
            >
              <X size={20} />
            </button>
          )}
        </form>

        {dropdownItems.length > 0 && (
          <ul className="absolute z-20 top-full mt-1 w-full bg-white rounded-portal border border-portal-border shadow-modal overflow-hidden">
            {showHistory && (
              <li className="px-5 py-2 text-xs font-medium text-portal-text-secondary uppercase tracking-wide border-b border-portal-border">
                Недавние запросы
              </li>
            )}
            {dropdownItems.map(({ label, isHistory }, i) => (
              <li key={i}>
                <button
                  type="button"
                  onMouseDown={() => select(label)}
                  className="w-full text-left px-5 py-3 text-sm hover:bg-portal-bg transition-colors border-b border-portal-border last:border-0 flex items-center gap-2"
                >
                  {isHistory
                    ? <Clock size={12} className="text-portal-text-secondary shrink-0" />
                    : <Search size={12} className="text-portal-text-secondary shrink-0" />
                  }
                  {label}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {correctedQuery && correctedQuery !== value && (
        <div className="px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg text-sm flex items-center gap-2">
          <span className="text-portal-orange">
            Показаны результаты по запросу <strong>"{correctedQuery}"</strong>
          </span>
          <button
            onClick={() => { setValue(correctedQuery); onSearch(correctedQuery); }}
            className="ml-auto text-portal-blue hover:underline font-medium shrink-0"
          >
            Использовать
          </button>
        </div>
      )}
    </div>
  );
}
