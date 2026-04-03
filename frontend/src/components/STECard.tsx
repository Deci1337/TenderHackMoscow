import { useState } from "react";
import { GitCompare, ThumbsDown, ChevronRight, HelpCircle } from "lucide-react";
import { STEResult } from "../api/client";
import STEModal from "./STEModal";

interface Props {
  item: STEResult;
  query: string;
  onAction: (steId: number, action: string) => void;
  inCompare?: boolean;
}

const BADGE_STYLE: Record<string, string> = {
  history:    "bg-portal-success-bg text-portal-success border-portal-success/20",
  category:   "bg-portal-info-bg text-portal-info border-portal-info/20",
  popularity: "bg-purple-50 text-purple-700 border-purple-200",
  session:    "bg-portal-warning-bg text-portal-warning border-portal-warning/20",
  default:    "bg-portal-bg text-portal-text-secondary border-portal-border",
};

export default function STECard({ item, query, onAction, inCompare = false }: Props) {
  const [showModal, setShowModal] = useState(false);

  return (
    <>
      <div className="bg-white rounded-portal border border-portal-border shadow-card hover:shadow-card-hover transition-shadow flex flex-col">
        {/* Card body */}
        <div className="p-4 flex-1 flex flex-col gap-3">
          {/* Title + ID */}
          <div className="flex items-start gap-2">
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-portal-text text-sm leading-snug line-clamp-2">
                {item.name}
              </h3>
              {item.category && (
                <p className="text-xs text-portal-text-secondary mt-0.5 truncate">{item.category}</p>
              )}
            </div>
            <span className="shrink-0 text-2xs font-mono bg-portal-bg border border-portal-border rounded px-1.5 py-0.5 text-portal-text-muted">
              {item.id}
            </span>
          </div>

          {/* Explanation badges */}
          {item.explanations.length > 0 && (
            <div className="flex flex-wrap gap-1 items-center">
              {item.explanations.slice(0, 2).map((exp, i) => (
                <span
                  key={i}
                  className={`text-2xs px-2 py-0.5 rounded border font-medium ${BADGE_STYLE[exp.factor] ?? BADGE_STYLE.default}`}
                >
                  {exp.reason}
                </span>
              ))}
              <button
                onClick={() => setShowModal(true)}
                title="Почему этот товар здесь?"
                className="text-portal-text-muted hover:text-portal-blue transition-colors"
              >
                <HelpCircle size={13} />
              </button>
            </div>
          )}

          {/* Attributes preview */}
          {item.attributes && Object.keys(item.attributes).length > 0 && (
            <div className="text-2xs text-portal-text-secondary flex flex-wrap gap-x-3 gap-y-0.5 pt-2 border-t border-portal-border-light">
              {Object.entries(item.attributes).slice(0, 3).map(([k, v]) => (
                <span key={k}>
                  <span className="font-medium text-portal-text-secondary">{k}:</span>{" "}
                  <span>{String(v)}</span>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Action bar */}
        <div className="px-4 py-2.5 border-t border-portal-border-light flex items-center gap-1">
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1 text-xs text-portal-blue hover:bg-portal-blue-pale rounded px-2 py-1.5 transition-colors font-medium"
          >
            Подробнее <ChevronRight size={12} />
          </button>

          <button
            onClick={() => onAction(item.id, "compare")}
            className={`flex items-center gap-1 text-xs rounded px-2 py-1.5 transition-colors ${
              inCompare
                ? "text-portal-blue bg-portal-blue-pale font-medium"
                : "text-portal-text-secondary hover:bg-portal-bg"
            }`}
            title={inCompare ? "Убрать из сравнения" : "Добавить к сравнению"}
          >
            <GitCompare size={12} />
            {inCompare ? "В сравнении" : "Сравнить"}
          </button>

          <button
            onClick={() => onAction(item.id, "hide")}
            className="ml-auto text-portal-text-muted hover:text-portal-error hover:bg-portal-error-bg rounded px-2 py-1.5 transition-colors"
            title="Не интересует"
          >
            <ThumbsDown size={13} />
          </button>
        </div>
      </div>

      {showModal && (
        <STEModal item={item} onClose={() => setShowModal(false)} onAction={onAction} />
      )}
    </>
  );
}
