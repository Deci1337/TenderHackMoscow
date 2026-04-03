import { PackageSearch, Search, Tag, Lightbulb } from "lucide-react";

const POPULAR_QUERIES = ["бумага офисная", "картридж", "компьютер", "стул офисный", "принтер"];

const TIPS = [
  { icon: <Search size={14} />, text: "Используйте более общий запрос" },
  { icon: <Tag size={14} />, text: "Попробуйте синоним или аббревиатуру" },
  { icon: <Lightbulb size={14} />, text: "Укажите только ключевое слово без характеристик" },
];

interface Props {
  query: string;
  onQueryClick: (q: string) => void;
}

export default function EmptyState({ query, onQueryClick }: Props) {
  return (
    <div className="text-center py-16 text-portal-text-secondary">
      <PackageSearch size={48} className="mx-auto mb-4 opacity-40" />
      <p className="text-lg font-semibold text-portal-text">
        По запросу «{query}» ничего не найдено
      </p>

      <ul className="mt-4 space-y-1.5 text-sm max-w-xs mx-auto text-left">
        {TIPS.map((tip, i) => (
          <li key={i} className="flex items-center gap-2">
            <span className="text-portal-text-secondary">{tip.icon}</span>
            {tip.text}
          </li>
        ))}
      </ul>

      <div className="mt-6">
        <p className="text-xs uppercase tracking-wide font-medium text-portal-text-secondary mb-2">
          Популярные запросы
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          {POPULAR_QUERIES.map((q) => (
            <button
              key={q}
              onClick={() => onQueryClick(q)}
              className="text-sm px-3 py-1.5 rounded-full border border-portal-border hover:bg-portal-blue hover:text-white hover:border-portal-blue transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
