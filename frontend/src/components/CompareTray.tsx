import { X, BarChart2 } from "lucide-react";
import { STEResult } from "../api/client";

interface Props {
  items: STEResult[];
  onRemove: (id: number) => void;
  onOpen: () => void;
  onClear: () => void;
}

export default function CompareTray({ items, onRemove, onOpen, onClear }: Props) {
  if (!items.length) return null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-40 bg-white border-t border-portal-border shadow-xl">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
        <BarChart2 size={18} className="text-portal-blue shrink-0" />
        <span className="text-sm font-semibold text-portal-text shrink-0">
          Сравнение ({items.length}/3):
        </span>

        <div className="flex items-center gap-2 flex-1 overflow-x-auto min-w-0">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-1.5 bg-portal-bg border border-portal-border rounded-lg px-3 py-1.5 shrink-0"
            >
              <span className="text-sm text-portal-text max-w-[160px] truncate">{item.name}</span>
              <button
                onClick={() => onRemove(item.id)}
                className="text-portal-text-secondary hover:text-red-500 transition-colors ml-1"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onClear}
            className="text-sm text-portal-text-secondary hover:text-portal-text transition-colors"
          >
            Очистить
          </button>
          <button
            onClick={onOpen}
            disabled={items.length < 2}
            className="text-sm bg-portal-blue text-white px-4 py-1.5 rounded-lg hover:bg-portal-blue/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Сравнить →
          </button>
        </div>
      </div>
    </div>
  );
}
