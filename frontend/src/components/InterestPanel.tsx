import { useEffect, useState } from "react";
import { Brain, X } from "lucide-react";
import { api, UserInterestSummary, CategoryInterest } from "../api/client";

interface SessionClick {
  steId: number;
  category: string;
  name: string;
}

interface LearningEntry {
  action: "like" | "dislike";
  itemName: string;
  query: string;
  lesson: string;
  timestamp: number;
}

interface InterestPanelProps {
  userInn: string;
  userLabel: string;
  lastQuery: string;
  sessionClicks: SessionClick[];
  learningLog: LearningEntry[];
  onClose: () => void;
}

// Per-user mocks with realistic data matching each demo profile
const USER_MOCKS: Record<string, UserInterestSummary> = {
  "7701234567": {
    inn: "7701234567",
    label: "Школа №1234",
    top_categories: [
      { category: "Канцелярские товары", click_count: 0, contract_count: 45, weight: 0.72, trend: "stable", last_interaction_days: 3 },
      { category: "Мебель офисная",      click_count: 0, contract_count: 20, weight: 0.45, trend: "stable", last_interaction_days: 5 },
      { category: "IT-оборудование",     click_count: 0, contract_count: 12, weight: 0.28, trend: "stable", last_interaction_days: 10 },
      { category: "Спортивный инвентарь",click_count: 0, contract_count: 8,  weight: 0.12, trend: "fading", last_interaction_days: 48 },
    ],
    session_clicks_total: 0,
    recent_query: null,
    active_interests: ["Канцелярские товары", "Мебель офисная"],
    fading_interests: ["Спортивный инвентарь"],
    last_updated: new Date().toISOString(),
  },
  "7709876543": {
    inn: "7709876543",
    label: "Городская больница №5",
    top_categories: [
      { category: "Медицинские товары",   click_count: 0, contract_count: 80, weight: 0.85, trend: "stable", last_interaction_days: 2 },
      { category: "Расходные материалы", click_count: 0, contract_count: 60, weight: 0.65, trend: "stable", last_interaction_days: 4 },
      { category: "Хозяйственные товары",click_count: 0, contract_count: 25, weight: 0.35, trend: "stable", last_interaction_days: 7 },
      { category: "IT-оборудование",     click_count: 0, contract_count: 15, weight: 0.18, trend: "fading", last_interaction_days: 62 },
    ],
    session_clicks_total: 0,
    recent_query: null,
    active_interests: ["Медицинские товары", "Расходные материалы"],
    fading_interests: ["IT-оборудование"],
    last_updated: new Date().toISOString(),
  },
  "7705551234": {
    inn: "7705551234",
    label: "СтройМонтаж ООО",
    top_categories: [
      { category: "Стройматериалы",      click_count: 0, contract_count: 120, weight: 0.90, trend: "stable", last_interaction_days: 1 },
      { category: "Электротехника",      click_count: 0, contract_count: 55,  weight: 0.65, trend: "stable", last_interaction_days: 3 },
      { category: "Инструменты",         click_count: 0, contract_count: 30,  weight: 0.45, trend: "stable", last_interaction_days: 5 },
      { category: "Хозяйственные товары",click_count: 0, contract_count: 18,  weight: 0.22, trend: "fading", last_interaction_days: 35 },
    ],
    session_clicks_total: 0,
    recent_query: null,
    active_interests: ["Стройматериалы", "Электротехника"],
    fading_interests: ["Хозяйственные товары"],
    last_updated: new Date().toISOString(),
  },
};

function getMockForUser(inn: string, label: string): UserInterestSummary {
  return USER_MOCKS[inn] ?? {
    inn, label,
    top_categories: [],
    session_clicks_total: 0,
    recent_query: null,
    active_interests: [],
    fading_interests: [],
    last_updated: new Date().toISOString(),
  };
}

function trendIcon(t: string) {
  return t === "rising" ? "↑" : t === "fading" ? "↓" : "→";
}
function trendColor(t: string) {
  return t === "rising" ? "#0D9B68" : t === "fading" ? "#DB2B21" : "#8C8C8C";
}

function getCategoryDetail(cat: CategoryInterest): { line1: string; line2: string | null } {
  const { category, click_count, contract_count, trend, last_interaction_days } = cat;

  // Основная строка — что есть в истории
  let line1 = "";
  if (contract_count > 0) {
    line1 = `${contract_count} заказов по категории «${category}» в истории закупок`;
  } else if (click_count > 0) {
    line1 = `${click_count} кликов в текущей сессии`;
  } else {
    line1 = "Новый интерес — данных пока нет";
  }

  // Если в текущей сессии были клики — дополнить
  if (click_count > 0 && contract_count > 0) {
    line1 = `${contract_count} заказов в истории · ${click_count} ${click_count === 1 ? "клик" : "клика"} сегодня`;
  }

  // Вторая строка — тренд
  let line2: string | null = null;
  if (trend === "rising") {
    line2 = "Интерес растёт — система повышает приоритет";
  } else if (trend === "fading") {
    const days = last_interaction_days;
    let period: string;
    if (days < 0 || days > 365) {
      period = "давно";
    } else if (days >= 30) {
      period = "более месяца";
    } else if (days >= 14) {
      period = `${days} дней`;
    } else {
      period = `${days} ${days === 1 ? "день" : "дня"}`;
    }
    line2 = `Не просматривали ${period} — приоритет снижен`;
  }

  return { line1, line2 };
}

export function InterestPanel({ userInn, userLabel, lastQuery, sessionClicks, learningLog, onClose }: InterestPanelProps) {
  const [data, setData] = useState<UserInterestSummary | null>(null);

  useEffect(() => {
    setData(null);
    api.getUserInterests(userInn)
      .then(setData)
      .catch(() => setData(getMockForUser(userInn, userLabel)));
  }, [userInn, sessionClicks.length]);

  const displayData = data ?? getMockForUser(userInn, userLabel);

  // Count session clicks per category
  const sessionCatCounts: Record<string, number> = {};
  sessionClicks.forEach(c => { sessionCatCounts[c.category] = (sessionCatCounts[c.category] ?? 0) + 1; });

  // Merge live session click counts into categories
  const enriched = displayData.top_categories.map(cat => ({
    ...cat,
    click_count: sessionCatCounts[cat.category] ?? cat.click_count,
    trend: sessionCatCounts[cat.category] ? "rising" as const : cat.trend,
  }));

  // Add session-only categories (clicked but not in history)
  const newSessionCats = Object.entries(sessionCatCounts)
    .filter(([cat]) => !enriched.some(e => e.category === cat))
    .map(([cat, cnt]): CategoryInterest => ({
      category: cat, click_count: cnt, contract_count: 0,
      weight: Math.min(cnt * 0.1, 0.3), trend: "rising", last_interaction_days: 0,
    }));

  const allCategories = [...enriched, ...newSessionCats]
    .sort((a, b) => b.weight - a.weight);

  return (
    <div style={{
      position: "fixed", right: 0, top: 0, bottom: 0, width: 340,
      background: "#fff", boxShadow: "-4px 0 24px rgba(0,0,0,.14)",
      zIndex: 200, overflowY: "auto", display: "flex", flexDirection: "column",
    }}>
      {/* Header */}
      <div style={{ background: "#264B82", color: "#fff", padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Brain size={16} color="#fff" />
          <div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>Профиль интересов</div>
            <div style={{ fontSize: 11, color: "#a3bfe0", marginTop: 1 }}>{userLabel}</div>
          </div>
        </div>
        <button onClick={onClose} style={{ background: "rgba(255,255,255,.15)", border: "none", color: "#fff", cursor: "pointer", borderRadius: 4, padding: "4px 6px", lineHeight: 1 }}>
          <X size={14} />
        </button>
      </div>

      {/* Session stats */}
      <div style={{ padding: "10px 16px", borderBottom: "1px solid #E7EEF7", background: "#F8FAFE", flexShrink: 0 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 6 }}>Текущая сессия</div>
        <div style={{ display: "flex", gap: 16, fontSize: 13 }}>
          <span><b>{sessionClicks.length}</b> кликов</span>
          {lastQuery && <span style={{ color: "#8C8C8C" }}>Запрос: «<b style={{ color: "#1A1A1A" }}>{lastQuery}</b>»</span>}
        </div>
        {sessionClicks.length > 0 && (
          <div style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: 4 }}>
            {Object.entries(sessionCatCounts).map(([cat, cnt]) => (
              <span key={cat} style={{ fontSize: 10, background: "#E7EEF7", color: "#264B82", borderRadius: 20, padding: "2px 8px", fontWeight: 600 }}>
                {cat} ×{cnt}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Category interests */}
      <div style={{ padding: "12px 16px", flex: 1 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 12 }}>
          Как система понимает интересы
        </div>

        {allCategories.length === 0 ? (
          <div style={{ padding: "20px 0", textAlign: "center" }}>
            <div style={{ fontSize: 13, color: "#8C8C8C" }}>История закупок не загружена</div>
            <div style={{ fontSize: 12, color: "#8C8C8C", marginTop: 6 }}>Начните искать — система начнёт отслеживать интересы</div>
          </div>
        ) : (
          allCategories.map(cat => {
            const { line1, line2 } = getCategoryDetail(cat);
            return (
              <div key={cat.category} style={{ marginBottom: 18, paddingBottom: 14, borderBottom: "1px solid #F0F3F8" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: "#1A1A1A" }}>{cat.category}</span>
                  <span style={{ fontSize: 13, fontWeight: 800, color: "#264B82" }}>{Math.round(cat.weight * 100)}%</span>
                </div>
                {/* Progress bar */}
                <div style={{ height: 6, background: "#E7EEF7", borderRadius: 3, marginBottom: 6, overflow: "hidden" }}>
                  <div style={{
                    height: "100%",
                    width: `${cat.weight * 100}%`,
                    background: cat.trend === "fading" ? "#F67319" : cat.trend === "rising" ? "#0D9B68" : "#264B82",
                    borderRadius: 3,
                    transition: "width .5s",
                  }} />
                </div>
                {/* Line 1: contract/click count */}
                <div style={{ fontSize: 11, color: "#555", lineHeight: 1.5 }}>{line1}</div>
                {/* Line 2: trend explanation */}
                {line2 && (
                  <div style={{ fontSize: 11, color: trendColor(cat.trend), marginTop: 3, display: "flex", alignItems: "center", gap: 4 }}>
                    <span style={{ fontWeight: 700 }}>{trendIcon(cat.trend)}</span>
                    {line2}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Learning log */}
      {learningLog.length > 0 && (
        <div style={{ padding: "12px 16px", borderTop: "1px solid #E7EEF7" }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#264B82", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 8 }}>
            Дообучение нейросети ({learningLog.length})
          </div>
          {learningLog.slice(-5).reverse().map((entry, i) => (
            <div key={i} style={{ marginBottom: 8, padding: "6px 8px", background: entry.action === "like" ? "#F0FFF7" : "#FFF5F5", borderRadius: 4, fontSize: 11 }}>
              <div style={{ display: "flex", gap: 4, alignItems: "center", marginBottom: 2 }}>
                <span style={{ fontWeight: 700, color: entry.action === "like" ? "#0D9B68" : "#DB2B21" }}>
                  {entry.action === "like" ? "+" : "-"}
                </span>
                <span style={{ fontWeight: 600, color: "#1A1A1A" }}>«{entry.itemName}»</span>
              </div>
              <div style={{ color: "#7F8792", lineHeight: 1.4 }}>{entry.lesson}</div>
            </div>
          ))}
        </div>
      )}

      {/* System conclusion */}
      {(displayData.active_interests.length > 0 || sessionClicks.length > 0) && (
        <div style={{ padding: "12px 16px", background: "#E6F7F1", borderTop: "1px solid #B2DFD0", flexShrink: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#0D9B68", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 6 }}>Вывод системы</div>
          <div style={{ fontSize: 12, color: "#1A1A1A", lineHeight: 1.6 }}>
            {lastQuery ? (
              <>
                По запросу «<b>{lastQuery}</b>» система приоритизирует категорию{" "}
                <b>{displayData.active_interests[0] ?? allCategories[0]?.category}</b> —
                она наиболее активна ({allCategories[0]?.contract_count ?? 0} заказов).
              </>
            ) : (
              <>
                Приоритетная категория: <b>{displayData.active_interests[0] ?? allCategories[0]?.category}</b>{" "}
                ({allCategories[0]?.contract_count ?? 0} заказов в истории).
              </>
            )}
          </div>
          {displayData.fading_interests.length > 0 && (
            <div style={{ fontSize: 11, color: "#F67319", marginTop: 6, lineHeight: 1.5 }}>
              Снижен приоритет: {displayData.fading_interests.join(", ")} — давно не просматривались
            </div>
          )}
        </div>
      )}
    </div>
  );
}
