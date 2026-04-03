import { useState } from "react";

interface Props {
  onComplete: (inn: string, name: string, industry: string) => void;
}

const INDUSTRIES = [
  { label: "Образование", icon: "🎓" },
  { label: "Здравоохранение", icon: "🏥" },
  { label: "Строительство", icon: "🏗️" },
  { label: "IT и связь", icon: "💻" },
  { label: "ЖКХ", icon: "🏠" },
  { label: "Транспорт", icon: "🚌" },
  { label: "Культура и спорт", icon: "🎭" },
  { label: "Промышленность", icon: "🏭" },
  { label: "Другое", icon: "📋" },
];

const DEMO_USERS = [
  { inn: "7701234567", name: "Школа №1234", industry: "Образование" },
  { inn: "7709876543", name: "Городская больница №5", industry: "Здравоохранение" },
  { inn: "7705551234", name: "СтройМонтаж", industry: "Строительство" },
];

export default function OnboardingModal({ onComplete }: Props) {
  const [inn, setInn] = useState("");
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inn && industry) onComplete(inn, name, industry);
  };

  return (
    <div className="min-h-screen bg-portal-bg flex items-center justify-center p-4">
      {/* Background decorative strip */}
      <div className="fixed top-0 inset-x-0 h-1.5 bg-portal-blue" />

      <div className="bg-white rounded-portal shadow-modal max-w-lg w-full overflow-hidden">
        {/* Blue header band */}
        <div className="bg-portal-blue px-8 py-6">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 bg-white rounded flex items-center justify-center">
              <span className="text-portal-blue font-black text-sm">МП</span>
            </div>
            <span className="text-white font-semibold">Портал поставщиков</span>
          </div>
          <h2 className="text-white text-xl font-bold mt-3">Персонализация поиска</h2>
          <p className="text-blue-200 text-sm mt-1">
            Укажите данные организации — система подберёт наиболее релевантные товары
          </p>
        </div>

        <div className="px-8 py-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-portal-text mb-1.5">
                ИНН организации <span className="text-portal-error">*</span>
              </label>
              <input
                value={inn}
                onChange={(e) => setInn(e.target.value.replace(/\D/g, "").slice(0, 12))}
                placeholder="Например: 7701234567"
                className="w-full px-4 py-2.5 border border-portal-border rounded-portal text-sm
                           focus:border-portal-blue focus:outline-none focus:ring-2 focus:ring-portal-blue/20
                           transition-colors"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-portal-text mb-1.5">
                Название организации
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Например: ГБОУ Школа №1234"
                className="w-full px-4 py-2.5 border border-portal-border rounded-portal text-sm
                           focus:border-portal-blue focus:outline-none focus:ring-2 focus:ring-portal-blue/20
                           transition-colors"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-portal-text mb-2">
                Сфера деятельности <span className="text-portal-error">*</span>
              </label>
              <div className="grid grid-cols-3 gap-2">
                {INDUSTRIES.map((ind) => (
                  <button
                    key={ind.label}
                    type="button"
                    onClick={() => setIndustry(ind.label)}
                    className={`flex flex-col items-center gap-1 px-2 py-3 rounded-portal text-xs border transition-all ${
                      industry === ind.label
                        ? "bg-portal-blue-pale border-portal-blue text-portal-blue font-semibold"
                        : "bg-white border-portal-border text-portal-text-secondary hover:border-portal-blue hover:text-portal-text"
                    }`}
                  >
                    <span className="text-lg leading-none">{ind.icon}</span>
                    <span className="text-center leading-tight">{ind.label}</span>
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={!inn || !industry}
              className="w-full bg-portal-blue hover:bg-portal-blue-hover disabled:opacity-40
                         disabled:cursor-not-allowed text-white font-semibold py-3 rounded-portal
                         transition-colors text-sm shadow-sm"
            >
              Начать поиск
            </button>
          </form>

          <div className="mt-5 pt-4 border-t border-portal-border-light">
            <p className="text-xs text-portal-text-muted mb-2 uppercase tracking-wide font-medium">
              Быстрый вход — демо
            </p>
            <div className="flex flex-col gap-1">
              {DEMO_USERS.map((u) => (
                <button
                  key={u.inn}
                  onClick={() => onComplete(u.inn, u.name, u.industry)}
                  className="text-left text-sm px-3 py-2 rounded-portal hover:bg-portal-bg
                             transition-colors flex items-center justify-between group"
                >
                  <span className="text-portal-text group-hover:text-portal-blue transition-colors font-medium">
                    {u.name}
                  </span>
                  <span className="text-xs text-portal-text-muted">{u.industry}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
