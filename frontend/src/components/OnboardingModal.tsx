import { useState } from "react";
import { Building2 } from "lucide-react";

interface Props {
  onComplete: (inn: string, name: string, industry: string) => void;
}

const INDUSTRIES = [
  "Образование",
  "Здравоохранение",
  "Строительство",
  "IT и связь",
  "ЖКХ",
  "Транспорт",
  "Культура и спорт",
  "Промышленность",
  "Другое",
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
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="bg-portal-blue rounded-xl p-2.5">
            <Building2 className="text-white" size={24} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-portal-text">Добро пожаловать</h2>
            <p className="text-sm text-portal-text-secondary">
              Расскажите о себе, чтобы мы подобрали для вас наиболее подходящие товары
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">ИНН организации *</label>
            <input
              value={inn}
              onChange={(e) => setInn(e.target.value)}
              placeholder="Введите ИНН"
              className="w-full px-4 py-2.5 border border-portal-border rounded-lg focus:border-portal-blue focus:outline-none focus:ring-2 focus:ring-portal-blue/20"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Название организации</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Например: Школа №1234"
              className="w-full px-4 py-2.5 border border-portal-border rounded-lg focus:border-portal-blue focus:outline-none focus:ring-2 focus:ring-portal-blue/20"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Сфера деятельности *</label>
            <div className="flex flex-wrap gap-2">
              {INDUSTRIES.map((ind) => (
                <button
                  key={ind}
                  type="button"
                  onClick={() => setIndustry(ind)}
                  className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                    industry === ind
                      ? "bg-portal-blue text-white border-portal-blue"
                      : "bg-white text-portal-text border-portal-border hover:border-portal-blue"
                  }`}
                >
                  {ind}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={!inn || !industry}
            className="w-full bg-portal-blue text-white font-semibold py-3 rounded-xl hover:bg-portal-blue-hover disabled:opacity-40 transition-colors"
          >
            Начать поиск
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-portal-border">
          <p className="text-xs text-portal-text-secondary mb-2 font-medium">
            Быстрый вход (демо-режим):
          </p>
          <div className="flex flex-col gap-1.5">
            {DEMO_USERS.map((u) => (
              <button
                key={u.inn}
                onClick={() => onComplete(u.inn, u.name, u.industry)}
                className="text-left text-sm px-3 py-2 rounded-lg hover:bg-portal-bg transition-colors text-portal-text-secondary hover:text-portal-text"
              >
                <span className="font-medium">{u.name}</span>{" "}
                <span className="text-xs">({u.industry}, ИНН: {u.inn})</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
