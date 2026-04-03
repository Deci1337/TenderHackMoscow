import { ChevronDown, LogOut } from "lucide-react";

interface Props {
  currentUser: { inn: string; name: string | null; industry: string | null } | null;
  onSwitchUser: () => void;
}

export default function Header({ currentUser, onSwitchUser }: Props) {
  return (
    <header className="bg-portal-blue shadow-md">
      {/* Top bar — logo + nav */}
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-white rounded flex items-center justify-center">
              <span className="text-portal-blue font-black text-sm leading-none">МП</span>
            </div>
            <div className="flex flex-col">
              <span className="text-white font-semibold text-sm leading-tight tracking-wide">
                Портал поставщиков
              </span>
              <span className="text-blue-300 text-xs leading-tight">zakupki.mos.ru</span>
            </div>
          </div>

          {/* Nav links — desktop */}
          <nav className="hidden md:flex items-center gap-1">
            {["Каталог", "Закупки", "Контракты", "Аналитика"].map((item) => (
              <span
                key={item}
                className="text-blue-200 hover:text-white text-sm px-3 py-1.5 rounded cursor-default transition-colors"
              >
                {item}
              </span>
            ))}
          </nav>

          {/* User info */}
          {currentUser && (
            <button
              onClick={onSwitchUser}
              className="flex items-center gap-2 bg-white/10 hover:bg-white/20 rounded-lg px-3 py-1.5 text-sm transition-colors group"
            >
              <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-xs font-bold text-white">
                {(currentUser.name || currentUser.inn).charAt(0).toUpperCase()}
              </div>
              <div className="text-left hidden sm:block">
                <div className="text-white font-medium leading-tight text-xs">
                  {currentUser.name || `ИНН ${currentUser.inn}`}
                </div>
                {currentUser.industry && (
                  <div className="text-blue-300 text-2xs leading-tight">{currentUser.industry}</div>
                )}
              </div>
              <ChevronDown size={14} className="text-blue-300 group-hover:text-white transition-colors" />
            </button>
          )}
        </div>
      </div>

      {/* Breadcrumb / search hint strip */}
      <div className="bg-portal-blue-hover border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 py-1.5 flex items-center gap-2 text-xs text-blue-300">
          <span>Главная</span>
          <span>/</span>
          <span className="text-white">Умный поиск СТЕ</span>
          {currentUser?.industry && (
            <>
              <span>/</span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-400" />
                Персонализация активна
              </span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
