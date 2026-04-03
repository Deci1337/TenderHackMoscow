import { useEffect, useState } from "react";
import { Filter, X } from "lucide-react";
import { api, CategoryFacet } from "../api/client";

interface Props {
  selectedCategory: string | null;
  onSelect: (category: string | null) => void;
}

export default function FilterPanel({ selectedCategory, onSelect }: Props) {
  const [facets, setFacets] = useState<CategoryFacet[]>([]);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    api.facets().then((r) => setFacets(r.categories)).catch(() => {});
  }, []);

  if (!facets.length) return null;

  return (
    <div className="bg-white rounded-xl border border-portal-border p-4 space-y-3">
      <div className="flex items-center justify-between">
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="flex items-center gap-2 text-sm font-semibold text-portal-text"
        >
          <Filter size={14} className="text-portal-blue" />
          Категории
        </button>
        {selectedCategory && (
          <button
            onClick={() => onSelect(null)}
            className="flex items-center gap-1 text-xs text-portal-text-secondary hover:text-red-500 transition-colors"
          >
            <X size={12} /> Сбросить
          </button>
        )}
      </div>

      {!collapsed && (
        <ul className="space-y-0.5 max-h-72 overflow-y-auto">
          {facets.map((f) => (
            <li key={f.name}>
              <button
                onClick={() => onSelect(selectedCategory === f.name ? null : f.name)}
                className={`w-full text-left flex items-center justify-between px-2 py-1.5 rounded-lg text-sm transition-colors ${
                  selectedCategory === f.name
                    ? "bg-portal-blue/10 text-portal-blue font-medium"
                    : "text-portal-text hover:bg-portal-bg"
                }`}
              >
                <span className="truncate pr-2" title={f.name}>{f.name}</span>
                <span className="shrink-0 text-xs text-portal-text-secondary">{f.count}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
