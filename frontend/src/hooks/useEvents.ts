import { useCallback, useRef } from "react";
import { api } from "../api/client";

export function useEvents(userInn: string, sessionId: string) {
  const lastClickTime = useRef<Record<number, number>>({});

  const track = useCallback(
    (steId: number, eventType: string, query?: string) => {
      api.logEvent(userInn, steId, eventType, sessionId, query).catch(() => {});
    },
    [userInn, sessionId]
  );

  const trackClick = useCallback(
    (steId: number, query?: string) => {
      lastClickTime.current[steId] = Date.now();
      track(steId, "click", query);
    },
    [track]
  );

  const trackBounce = useCallback(
    (steId: number, query?: string) => {
      const clickedAt = lastClickTime.current[steId];
      if (clickedAt && Date.now() - clickedAt < 3000) {
        track(steId, "bounce", query);
      }
    },
    [track]
  );

  return { track, trackClick, trackBounce };
}
