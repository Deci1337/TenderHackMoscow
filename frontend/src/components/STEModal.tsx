import { useEffect } from "react";
import { X, GitCompare, ThumbsDown, Heart } from "lucide-react";
import { STEResult } from "../api/client";

interface Props {
  item: STEResult;
  onClose: () => void;
  onAction: (steId: number, action: string) => void;
}

export default function STEModal({ item, onClose, onAction }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between p-5 border-b border-portal-border">
          <div>
            <h2 className="font-bold text-portal-text text-lg leading-snug">{item.name}</h2>
            {item.category && (
              <p className="text-sm text-portal-text-secondary mt-0.5">{item.category}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-3 p-1.5 rounded-lg hover:bg-portal-bg text-portal-text-secondary"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="flex items-center gap-2 text-xs text-portal-text-secondary">
            <span className="font-mono bg-portal-bg px-2 py-1 rounded">ID: {item.id}</span>
          </div>

          {item.explanations.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-portal-text-secondary mb-2">
                Почему этот результат
              </p>
              <ul className="space-y-1.5">
                {item.explanations.map((exp, i) => (
                  <li key={i} className="text-sm flex items-start gap-2">
                    <span className="mt-0.5 w-1.5 h-1.5 rounded-full bg-portal-blue shrink-0" />
                    {exp.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {item.attributes && Object.keys(item.attributes).length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-portal-text-secondary mb-2">
                Характеристики
              </p>
              <table className="w-full text-sm border-collapse">
                <tbody>
                  {Object.entries(item.attributes).map(([k, v]) => (
                    <tr key={k} className="border-b border-portal-border last:border-0">
                      <td className="py-1.5 pr-3 font-medium text-portal-text w-1/2">{k}</td>
                      <td className="py-1.5 text-portal-text-secondary">{String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="p-5 border-t border-portal-border flex gap-2">
          <button
            onClick={() => { onAction(item.id, "compare"); onClose(); }}
            className="flex items-center gap-1.5 text-sm px-4 py-2 border border-portal-border rounded-lg hover:bg-portal-bg transition-colors"
          >
            <GitCompare size={14} /> Сравнить
          </button>
          <button
            onClick={() => { onAction(item.id, "like"); onClose(); }}
            className="flex items-center gap-1.5 text-sm px-4 py-2 border border-portal-border rounded-lg hover:bg-portal-bg transition-colors"
          >
            <Heart size={14} /> В избранное
          </button>
          <button
            onClick={() => { onAction(item.id, "hide"); onClose(); }}
            className="ml-auto flex items-center gap-1.5 text-sm px-4 py-2 text-red-500 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
          >
            <ThumbsDown size={14} /> Скрыть
          </button>
        </div>
      </div>
    </div>
  );
}
