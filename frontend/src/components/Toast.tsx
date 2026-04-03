import { X, CheckCircle, Info, AlertTriangle } from "lucide-react";
import { Toast as ToastType } from "../hooks/useToast";

const ICONS = {
  success: <CheckCircle size={16} className="text-emerald-500 shrink-0" />,
  info: <Info size={16} className="text-blue-500 shrink-0" />,
  warning: <AlertTriangle size={16} className="text-amber-500 shrink-0" />,
};

const BG = {
  success: "bg-emerald-50 border-emerald-200",
  info: "bg-blue-50 border-blue-200",
  warning: "bg-amber-50 border-amber-200",
};

interface Props {
  toasts: ToastType[];
  onRemove: (id: number) => void;
}

export default function ToastContainer({ toasts, onRemove }: Props) {
  if (!toasts.length) return null;
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 w-full max-w-sm px-4">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-center gap-2 px-4 py-3 rounded-xl border shadow-md text-sm text-portal-text ${BG[t.type]}`}
        >
          {ICONS[t.type]}
          <span className="flex-1">{t.message}</span>
          <button onClick={() => onRemove(t.id)} className="text-portal-text-secondary hover:text-portal-text">
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
