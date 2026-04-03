import { ChevronLeft, ChevronRight } from "lucide-react";

interface Props {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (offset: number) => void;
}

export default function Pagination({ total, limit, offset, onPageChange }: Props) {
  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  if (totalPages <= 1) return null;

  const pages: (number | "...")[] = [];
  for (let p = 1; p <= totalPages; p++) {
    if (p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1) {
      pages.push(p);
    } else if (pages[pages.length - 1] !== "...") {
      pages.push("...");
    }
  }

  return (
    <div className="flex items-center justify-center gap-1 mt-8">
      <button
        onClick={() => onPageChange(Math.max(0, offset - limit))}
        disabled={currentPage === 1}
        className="p-2 rounded-lg hover:bg-portal-bg disabled:opacity-30 transition-colors"
      >
        <ChevronLeft size={16} />
      </button>

      {pages.map((p, i) =>
        p === "..." ? (
          <span key={i} className="px-2 py-1 text-portal-text-secondary text-sm">…</span>
        ) : (
          <button
            key={i}
            onClick={() => onPageChange((p - 1) * limit)}
            className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${
              p === currentPage
                ? "bg-portal-blue text-white"
                : "hover:bg-portal-bg text-portal-text"
            }`}
          >
            {p}
          </button>
        )
      )}

      <button
        onClick={() => onPageChange(offset + limit)}
        disabled={currentPage === totalPages}
        className="p-2 rounded-lg hover:bg-portal-bg disabled:opacity-30 transition-colors"
      >
        <ChevronRight size={16} />
      </button>
    </div>
  );
}
