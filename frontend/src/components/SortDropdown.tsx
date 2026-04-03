import { ArrowDownAZ, Flame, SlidersHorizontal } from "lucide-react";

export type SortBy = "relevance" | "popularity" | "name";

const OPTIONS: { value: SortBy; label: string; icon: React.ReactNode }[] = [
  { value: "relevance", label: "По релевантности", icon: <SlidersHorizontal size={14} /> },
  { value: "popularity", label: "По популярности", icon: <Flame size={14} /> },
  { value: "name", label: "По алфавиту", icon: <ArrowDownAZ size={14} /> },
];

interface Props {
  value: SortBy;
  onChange: (v: SortBy) => void;
  total?: number;
}

export default function SortDropdown({ value, onChange, total }: Props) {
  return (
    <div className="flex items-center gap-3">
      {total !== undefined && (
        <span className="text-sm text-portal-text-secondary">
          Найдено: <span className="font-semibold text-portal-text">{total}</span>
        </span>
      )}
      <div className="flex items-center gap-1 bg-white border border-portal-border rounded-lg p-1">
        {OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md transition-colors ${
              value === opt.value
                ? "bg-portal-blue text-white"
                : "text-portal-text-secondary hover:bg-portal-bg"
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
