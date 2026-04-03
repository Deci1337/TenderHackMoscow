import { useCallback, useRef, useState } from "react";
import { api, SearchResponse } from "../api/client";

export function useSearch(userInn: string, sessionId: string) {
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const search = useCallback(
    async (query: string, offset = 0, limit = 20) => {
      if (!query.trim()) { setResponse(null); return; }
      abortRef.current?.abort();
      abortRef.current = new AbortController();
      setLoading(true);
      setError(null);
      try {
        const data = await api.search(query, userInn, sessionId, limit, offset);
        setResponse(data);
      } catch (e: unknown) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "Search failed");
      } finally {
        setLoading(false);
      }
    },
    [userInn, sessionId]
  );

  return { response, loading, error, search };
}
