const API_BASE = "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export interface RankingExplanation {
  reason: string;
  factor: string;
  weight: number;
}

export interface STEResult {
  id: number;
  name: string;
  category: string | null;
  attributes: Record<string, unknown> | null;
  score: number;
  explanations: RankingExplanation[];
}

export interface SearchResponse {
  query: string;
  corrected_query: string | null;
  did_you_mean: string | null;
  total: number;
  results: STEResult[];
}

export interface UserProfile {
  inn: string;
  name: string | null;
  region: string | null;
  industry: string | null;
  top_categories: string[];
  total_contracts: number;
}

export interface SuggestResponse {
  suggestions: string[];
}

export const api = {
  search(query: string, userInn: string, sessionId: string, limit = 20, offset = 0) {
    return request<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify({ query, user_inn: userInn, session_id: sessionId, limit, offset }),
    });
  },

  logEvent(userInn: string, steId: number, eventType: string, sessionId: string, query?: string) {
    return request<{ id: number; created_at: string }>("/events", {
      method: "POST",
      body: JSON.stringify({
        user_inn: userInn, ste_id: steId, event_type: eventType,
        session_id: sessionId, query,
      }),
    });
  },

  suggest(q: string) {
    return request<SuggestResponse>(`/search/suggest?q=${encodeURIComponent(q)}`);
  },

  onboard(inn: string, name?: string, region?: string, industry?: string) {
    return request<UserProfile>("/users/onboarding", {
      method: "POST",
      body: JSON.stringify({ inn, name, region, industry }),
    });
  },

  getUser(inn: string) {
    return request<UserProfile>(`/users/${inn}`);
  },
};
