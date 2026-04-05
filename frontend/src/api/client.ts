const API_BASE = "/api/v1";

async function request<T>(path: string, options?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const { timeoutMs = 20000, ...fetchOpts } = options || {};
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: ctrl.signal,
      ...fetchOpts,
    });
    if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
    return res.json();
  } finally {
    clearTimeout(timer);
  }
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
  snippet?: string | null;
  avg_price?: number | null;
  price_trend?: "up" | "down" | "stable" | null;
  tags?: string[];
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

export interface CategoryFacet {
  name: string;
  count: number;
}

export interface FacetsResponse {
  categories: CategoryFacet[];
}

export interface PopularQuery {
  query: string;
  count: number;
}

export interface PopularQueriesResponse {
  queries: PopularQuery[];
}

export interface CategoryInterest {
  category: string;
  click_count: number;
  contract_count: number;
  weight: number;
  trend: "rising" | "stable" | "fading";
  last_interaction_days: number;
}

export interface UserInterestSummary {
  inn: string;
  label: string | null;
  top_categories: CategoryInterest[];
  session_clicks_total: number;
  recent_query: string | null;
  active_interests: string[];
  fading_interests: string[];
  last_updated: string;
}

export const api = {
  search(
    query: string,
    userInn: string,
    sessionId: string,
    limit = 20,
    offset = 0,
    sortBy = "relevance",
    category?: string,
    interests: string[] = [],
  ) {
    return request<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify({
        query, user_inn: userInn, session_id: sessionId,
        limit, offset, sort_by: sortBy, interests,
        ...(category ? { category } : {}),
      }),
    });
  },

  logEvent(userInn: string, steId: number, eventType: string, sessionId: string, query?: string, meta?: Record<string, unknown>) {
    return request<{ id: number; created_at: string }>("/events", {
      method: "POST",
      body: JSON.stringify({
        user_inn: userInn, ste_id: steId, event_type: eventType,
        session_id: sessionId, query, meta,
      }),
    });
  },

  suggest(q: string) {
    return request<SuggestResponse>(`/search/suggest?q=${encodeURIComponent(q)}`);
  },

  facets() {
    return request<FacetsResponse>("/search/facets");
  },

  popularQueries() {
    return request<PopularQueriesResponse>("/search/popular");
  },

  onboard(userId: string, interests: string[]) {
    return request<UserProfile>("/users/onboarding", {
      method: "POST",
      body: JSON.stringify({ inn: userId, industry: interests[0] ?? null, interests }),
    });
  },

  getUser(inn: string) {
    return request<UserProfile>(`/users/${inn}`);
  },

  getUserInterests(inn: string) {
    return request<UserInterestSummary>(`/users/${inn}/interests`);
  },

  getUserCategories(inn: string) {
    return request<CategoryFacet[]>(`/users/${inn}/categories`);
  },
};
