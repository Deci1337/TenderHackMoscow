import { Users } from "lucide-react";
import { useState } from "react";

interface DemoUser {
  inn: string;
  name: string;
  industry: string;
}

const DEMO_USERS: DemoUser[] = [
  { inn: "7701234567", name: "Школа №1234", industry: "Образование" },
  { inn: "7709876543", name: "Городская больница №5", industry: "Здравоохранение" },
  { inn: "7705551234", name: "СтройМонтаж", industry: "Строительство" },
  { inn: "0000000000", name: "Новый пользователь", industry: "" },
];

interface Props {
  currentInn: string;
  onSwitch: (inn: string, name: string, industry: string) => void;
}

export default function DemoSwitcher({ currentInn, onSwitch }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="fixed bottom-4 right-4 z-40">
      <div className="relative">
        {open && (
          <div className="absolute bottom-full right-0 mb-2 bg-white rounded-xl shadow-xl border border-portal-border p-3 w-72">
            <p className="text-xs font-semibold text-portal-text-secondary mb-2 uppercase tracking-wide">
              Симуляция пользователя
            </p>
            {DEMO_USERS.map((u) => (
              <button
                key={u.inn}
                onClick={() => { onSwitch(u.inn, u.name, u.industry); setOpen(false); }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  currentInn === u.inn
                    ? "bg-portal-blue/10 text-portal-blue font-medium"
                    : "hover:bg-portal-bg text-portal-text"
                }`}
              >
                <div className="font-medium">{u.name}</div>
                {u.industry && <div className="text-xs text-portal-text-secondary">{u.industry}</div>}
              </button>
            ))}
          </div>
        )}
        <button
          onClick={() => setOpen(!open)}
          className="bg-portal-accent text-white rounded-full p-3 shadow-lg hover:shadow-xl transition-shadow"
          title="Демо: переключить пользователя"
        >
          <Users size={20} />
        </button>
      </div>
    </div>
  );
}
