import { ArrowDownAZ, Flame, SlidersHorizontal } from "lucide-react";

export type SortBy = "relevance" | "popularity" | "name";

const OPTIONS: { value: SortBy; label: string; icon: React.ReactNode }[] = [
  { value: "relevance", label: "По релевантности", icon: <SlidersHorizontal size={12} /> },
  { value: "popularity", label: "По популярности", icon: <Flame size={12} /> },
  { value: "name", label: "По алфавиту", icon: <ArrowDownAZ size={12} /> },
];

interface Props {
  value: SortBy;
  onChange: (v: SortBy) => void;
  total?: number;
}

export default function SortDropdown({ value, onChange, total }: Props) {
  return (
    <div className="flex items-center justify-between flex-wrap gap-3">
      {total !== undefined && (
        <p className="text-sm text-portal-text-secondary">
          Найдено: <span className="font-semibold text-portal-text">{total.toLocaleString("ru-RU")}</span> результатов
        </p>
      )}
      <div className="flex items-center gap-0.5 bg-portal-bg border border-portal-border rounded-portal p-0.5">
        {OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded transition-colors ${
              value === opt.value
                ? "bg-white text-portal-blue shadow-sm font-semibold border border-portal-border"
                : "text-portal-text-secondary hover:text-portal-text"
            }`}
          >
            {opt.icon}
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
