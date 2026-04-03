import { useEffect } from "react";
import { X } from "lucide-react";
import { STEResult } from "../api/client";

interface Props {
  items: STEResult[];
  onClose: () => void;
}

function allKeys(items: STEResult[]): string[] {
  const keys = new Set<string>();
  for (const item of items) {
    if (item.attributes) Object.keys(item.attributes).forEach((k) => keys.add(k));
  }
  return Array.from(keys);
}

export default function CompareModal({ items, onClose }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const attrKeys = allKeys(items);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center p-4 overflow-y-auto"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl my-8">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-portal-border">
          <h2 className="font-bold text-portal-text text-lg">Сравнение товаров</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-portal-bg text-portal-text-secondary"
          >
            <X size={18} />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-portal-border">
                <th className="text-left px-5 py-3 font-semibold text-portal-text-secondary w-1/4">
                  Характеристика
                </th>
                {items.map((item) => (
                  <th key={item.id} className="text-left px-5 py-3 font-semibold text-portal-text">
                    <div className="line-clamp-2">{item.name}</div>
                    {item.category && (
                      <div className="text-xs font-normal text-portal-text-secondary mt-0.5">
                        {item.category}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* ID row */}
              <tr className="border-b border-portal-border bg-portal-bg/30">
                <td className="px-5 py-2.5 font-medium text-portal-text-secondary">ID (СТЕ)</td>
                {items.map((item) => (
                  <td key={item.id} className="px-5 py-2.5 font-mono text-xs">{item.id}</td>
                ))}
              </tr>

              {/* Score row */}
              <tr className="border-b border-portal-border">
                <td className="px-5 py-2.5 font-medium text-portal-text-secondary">Релевантность</td>
                {items.map((item) => (
                  <td key={item.id} className="px-5 py-2.5">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 rounded-full bg-portal-border w-24 overflow-hidden">
                        <div
                          className="h-full bg-portal-blue rounded-full"
                          style={{ width: `${Math.min(item.score * 100, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-portal-text-secondary">
                        {(item.score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                ))}
              </tr>

              {/* Explanations row */}
              <tr className="border-b border-portal-border bg-portal-bg/30">
                <td className="px-5 py-2.5 font-medium text-portal-text-secondary">Почему в выдаче</td>
                {items.map((item) => (
                  <td key={item.id} className="px-5 py-2.5">
                    {item.explanations.length > 0 ? (
                      <ul className="space-y-0.5">
                        {item.explanations.map((e, i) => (
                          <li key={i} className="text-xs text-portal-text-secondary flex items-start gap-1">
                            <span className="mt-1 w-1 h-1 rounded-full bg-portal-blue shrink-0" />
                            {e.reason}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-xs text-portal-text-secondary">—</span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Attribute rows */}
              {attrKeys.map((key, idx) => {
                const vals = items.map((item) =>
                  item.attributes ? String(item.attributes[key] ?? "—") : "—"
                );
                const allSame = vals.every((v) => v === vals[0]);
                return (
                  <tr
                    key={key}
                    className={`border-b border-portal-border ${idx % 2 === 0 ? "" : "bg-portal-bg/30"}`}
                  >
                    <td className="px-5 py-2.5 font-medium text-portal-text-secondary">{key}</td>
                    {vals.map((val, i) => (
                      <td
                        key={i}
                        className={`px-5 py-2.5 ${
                          !allSame ? "font-semibold text-portal-text" : "text-portal-text-secondary"
                        }`}
                      >
                        {val}
                      </td>
                    ))}
                  </tr>
                );
              })}

              {attrKeys.length === 0 && (
                <tr>
                  <td
                    colSpan={items.length + 1}
                    className="px-5 py-6 text-center text-portal-text-secondary text-sm"
                  >
                    Характеристики не указаны
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
