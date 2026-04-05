import { useEffect, useState } from "react";
import { Brain, X } from "lucide-react";
import { api, UserInterestSummary } from "../api/client";

interface SessionClick {
  steId: number;
  category: string;
  name: string;
}

interface InterestPanelProps {
  userInn: string;
  userLabel: string;
  lastQuery: string;
  sessionClicks: SessionClick[];
  onClose: () => void;
}

const MOCK_INTERESTS: UserInterestSummary = {
  inn: "demo",
  label: "Демо-пользователь",
  top_categories: [
    { category: "Канцелярские товары", click_count: 8, contract_count: 45, weight: 0.72, trend: "rising", last_interaction_days: 0 },
    { category: "Мебель офисная", click_count: 3, contract_count: 20, weight: 0.45, trend: "stable", last_interaction_days: 2 },
    { category: "IT-оборудование", click_count: 1, contract_count: 12, weight: 0.28, trend: "fading", last_interaction_days: 18 },
  ],
  session_clicks_total: 12,
  recent_query: null,
  active_interests: ["Канцелярские товары", "Мебель офисная"],
  fading_interests: ["IT-оборудование"],
  last_updated: new Date().toISOString(),
};

function trendIcon(t: string) { return t === "rising" ? "↑" : t === "fading" ? "↓" : "→"; }
function trendColor(t: string) { return t === "rising" ? "#0D9B68" : t === "fading" ? "#DB2B21" : "#8C8C8C"; }
function trendLabel(t: string, days: number) {
  if (t === "rising") return "Интерес растёт";
  if (t === "fading") return `Не интересовались ${days} дн. — приоритет снижается`;
  return "Стабильный интерес";
}

export function InterestPanel({ userInn, userLabel, lastQuery, sessionClicks, onClose }: InterestPanelProps) {
  const [data, setData] = useState<UserInterestSummary | null>(null);

  useEffect(() => {
    setData(null);
    api.getUserInterests(userInn)
      .then(setData)
      .catch(() => setData({ ...MOCK_INTERESTS, inn: userInn, label: userLabel }));
  }, [userInn, sessionClicks.length]);

  const displayData = data ?? { ...MOCK_INTERESTS, inn: userInn, label: userLabel };

  // Count session clicks per category
  const sessionCatCounts: Record<string, number> = {};
  sessionClicks.forEach(c => { sessionCatCounts[c.category] = (sessionCatCounts[c.category] ?? 0) + 1; });

  // Merge session click_count into top_categories
  const enriched = displayData.top_categories.map(cat => ({
    ...cat,
    click_count: sessionCatCounts[cat.category] ?? cat.click_count,
  }));

  return (
    <div style={{
      position: "fixed", right: 0, top: 0, bottom: 0, width: 320,
      background: "#fff", boxShadow: "-4px 0 24px rgba(0,0,0,.14)",
      zIndex: 200, overflowY: "auto", display: "flex", flexDirection: "column",
    }}>
      {/* header */}
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

      {/* session stats */}
      <div style={{ padding: "10px 16px", borderBottom: "1px solid #E7EEF7", background: "#F8FAFE", flexShrink: 0 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 6 }}>Текущая сессия</div>
        <div style={{ display: "flex", gap: 16, fontSize: 13 }}>
          <span><b>{sessionClicks.length}</b> кликов</span>
          {lastQuery && <span style={{ color: "#8C8C8C" }}>«<b style={{ color: "#1A1A1A" }}>{lastQuery}</b>»</span>}
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

      {/* categories */}
      <div style={{ padding: "12px 16px", flex: 1 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#8C8C8C", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 12 }}>Как система понимает интересы</div>
        {enriched.length === 0 ? (
          <p style={{ fontSize: 13, color: "#8C8C8C", fontStyle: "italic" }}>История закупок не загружена</p>
        ) : (
          enriched.map(cat => (
            <div key={cat.category} style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A" }}>{cat.category}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: "#264B82" }}>{Math.round(cat.weight * 100)}%</span>
              </div>
              <div style={{ height: 6, background: "#E7EEF7", borderRadius: 3, marginBottom: 4, overflow: "hidden" }}>
                <div style={{
                  height: "100%",
                  width: `${cat.weight * 100}%`,
                  background: cat.trend === "fading" ? "#F67319" : "#264B82",
                  borderRadius: 3,
                  transition: "width .5s",
                }} />
              </div>
              <div style={{ fontSize: 11, color: "#8C8C8C" }}>
                {cat.click_count > 0 && `${cat.click_count} кликов · `}
                {cat.contract_count} контрактов в истории
              </div>
              <div style={{ fontSize: 11, color: trendColor(cat.trend), marginTop: 2 }}>
                {trendIcon(cat.trend)} {trendLabel(cat.trend, cat.last_interaction_days)}
              </div>
            </div>
          ))
        )}
      </div>

      {/* system conclusion */}
      {displayData.active_interests.length > 0 && (
        <div style={{ padding: "12px 16px", background: "#E6F7F1", borderTop: "1px solid #B2DFD0", flexShrink: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#0D9B68", textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 6 }}>Вывод системы</div>
          <div style={{ fontSize: 12, color: "#1A1A1A", lineHeight: 1.6 }}>
            {lastQuery ? (
              <>По запросу <b>«{lastQuery}»</b> система показывает товары из <b>{displayData.active_interests[0]}</b> — эта категория наиболее активна сейчас.</>
            ) : (
              <>Приоритетная категория: <b>{displayData.active_interests[0]}</b>.</>
            )}
          </div>
          {displayData.fading_interests.length > 0 && (
            <div style={{ fontSize: 11, color: "#F67319", marginTop: 6 }}>
              Угасает: {displayData.fading_interests.join(", ")} — снижаем приоритет
            </div>
          )}
        </div>
      )}
    </div>
  );
}
