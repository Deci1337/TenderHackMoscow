import { Building2 } from "lucide-react";

interface Props {
  currentUser: { inn: string; name: string | null; industry: string | null } | null;
  onSwitchUser: () => void;
}

export default function Header({ currentUser, onSwitchUser }: Props) {
  return (
    <header className="bg-portal-blue text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Building2 size={28} />
          <div>
            <h1 className="text-lg font-bold leading-tight">Портал Поставщиков</h1>
            <p className="text-xs text-blue-200">Умный поиск продукции</p>
          </div>
        </div>

        {currentUser && (
          <button
            onClick={onSwitchUser}
            className="flex items-center gap-2 bg-white/10 hover:bg-white/20 rounded-lg px-3 py-2 text-sm transition-colors"
          >
            <span className="font-medium">{currentUser.name || currentUser.inn}</span>
            {currentUser.industry && (
              <span className="bg-white/20 rounded px-2 py-0.5 text-xs">
                {currentUser.industry}
              </span>
            )}
          </button>
        )}
      </div>
    </header>
  );
}
