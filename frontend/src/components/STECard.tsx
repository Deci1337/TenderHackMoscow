import { Eye, GitCompare, ThumbsDown, ExternalLink } from "lucide-react";
import { STEResult } from "../api/client";

interface Props {
  item: STEResult;
  query: string;
  onAction: (steId: number, action: string) => void;
}

const EXPLANATION_COLORS: Record<string, string> = {
  history: "bg-emerald-50 text-emerald-700 border-emerald-200",
  category: "bg-blue-50 text-blue-700 border-blue-200",
  popularity: "bg-purple-50 text-purple-700 border-purple-200",
  session: "bg-amber-50 text-amber-700 border-amber-200",
  default: "bg-gray-50 text-gray-600 border-gray-200",
};

export default function STECard({ item, query, onAction }: Props) {
  return (
    <div className="bg-white rounded-xl border border-portal-border hover:shadow-md transition-shadow p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-portal-text leading-snug line-clamp-2">
            {item.name}
          </h3>
          {item.category && (
            <p className="text-sm text-portal-text-secondary mt-1">{item.category}</p>
          )}
        </div>
        <span className="shrink-0 text-xs font-mono bg-portal-bg rounded px-2 py-1 text-portal-text-secondary">
          ID: {item.id}
        </span>
      </div>

      {item.explanations.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {item.explanations.map((exp, i) => (
            <span
              key={i}
              className={`text-xs px-2 py-0.5 rounded-full border ${EXPLANATION_COLORS[exp.factor] || EXPLANATION_COLORS.default}`}
            >
              {exp.reason}
            </span>
          ))}
        </div>
      )}

      {item.attributes && Object.keys(item.attributes).length > 0 && (
        <div className="text-xs text-portal-text-secondary flex flex-wrap gap-x-4 gap-y-1 border-t border-portal-border pt-2">
          {Object.entries(item.attributes).slice(0, 4).map(([k, v]) => (
            <span key={k}>
              <span className="font-medium">{k}:</span> {String(v)}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 pt-1 border-t border-portal-border">
        <button
          onClick={() => onAction(item.id, "click")}
          className="flex items-center gap-1.5 text-sm text-portal-blue hover:bg-portal-blue/5 rounded-lg px-3 py-1.5 transition-colors"
        >
          <ExternalLink size={14} /> Подробнее
        </button>
        <button
          onClick={() => onAction(item.id, "compare")}
          className="flex items-center gap-1.5 text-sm text-portal-text-secondary hover:bg-portal-bg rounded-lg px-3 py-1.5 transition-colors"
          title="Добавить к сравнению"
        >
          <GitCompare size={14} /> Сравнить
        </button>
        <button
          onClick={() => onAction(item.id, "like")}
          className="flex items-center gap-1.5 text-sm text-portal-text-secondary hover:bg-portal-bg rounded-lg px-3 py-1.5 transition-colors"
          title="В избранное"
        >
          <Eye size={14} />
        </button>
        <button
          onClick={() => onAction(item.id, "hide")}
          className="ml-auto flex items-center gap-1.5 text-sm text-portal-text-secondary/50 hover:text-red-500 hover:bg-red-50 rounded-lg px-3 py-1.5 transition-colors"
          title="Скрыть (не интересует)"
        >
          <ThumbsDown size={14} />
        </button>
      </div>
    </div>
  );
}
