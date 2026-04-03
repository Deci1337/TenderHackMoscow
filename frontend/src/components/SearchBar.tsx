import { Loader2, Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

interface Props {
  onSearch: (query: string) => void;
  loading: boolean;
  correctedQuery: string | null;
  didYouMean: string | null;
}

export default function SearchBar({ onSearch, loading, correctedQuery, didYouMean }: Props) {
  const [value, setValue] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const suggestRef = useRef<ReturnType<typeof setTimeout>>();
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Debounced search
  useEffect(() => {
    clearTimeout(debounceRef.current);
    if (value.trim().length >= 2) {
      debounceRef.current = setTimeout(() => onSearch(value.trim()), 400);
    }
    return () => clearTimeout(debounceRef.current);
  }, [value, onSearch]);

  // Debounced autocomplete
  useEffect(() => {
    clearTimeout(suggestRef.current);
    if (value.trim().length >= 2) {
      suggestRef.current = setTimeout(async () => {
        try {
          const data = await api.suggest(value.trim());
          setSuggestions(data.suggestions);
          setShowSuggestions(data.suggestions.length > 0);
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

  // Close suggestions on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const selectSuggestion = (s: string) => {
    setValue(s);
    setShowSuggestions(false);
    onSearch(s);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setShowSuggestions(false);
    if (value.trim()) onSearch(value.trim());
  };

  const handleClear = () => {
    setValue("");
    setSuggestions([]);
    setShowSuggestions(false);
    onSearch("");
  };

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
            onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
            placeholder="Введите название товара или СТЕ..."
            className="w-full pl-12 pr-12 py-4 rounded-xl border-2 border-portal-border bg-white
                       text-base focus:border-portal-blue focus:outline-none focus:ring-2
                       focus:ring-portal-blue/20 shadow-sm transition-all
                       placeholder:text-portal-text-secondary/60"
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
              className="absolute right-4 top-1/2 -translate-y-1/2 text-portal-text-secondary
                         hover:text-portal-text transition-colors"
            >
              <X size={20} />
            </button>
          )}
        </form>

        {/* Autocomplete dropdown */}
        {showSuggestions && (
          <ul className="absolute z-20 top-full mt-1 w-full bg-white rounded-xl border
                         border-portal-border shadow-lg overflow-hidden">
            {suggestions.map((s, i) => (
              <li key={i}>
                <button
                  type="button"
                  onMouseDown={() => selectSuggestion(s)}
                  className="w-full text-left px-5 py-3 text-sm hover:bg-portal-bg
                             transition-colors border-b border-portal-border last:border-0"
                >
                  <Search size={12} className="inline mr-2 text-portal-text-secondary" />
                  {s}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Typo correction notice */}
      {correctedQuery && correctedQuery !== value && (
        <div className="px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg text-sm flex items-center gap-2">
          <span className="text-amber-700">
            Показаны результаты по запросу{" "}
            <strong>"{correctedQuery}"</strong>
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
