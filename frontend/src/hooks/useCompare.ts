import { useCallback, useState } from "react";
import { STEResult } from "../api/client";

const MAX = 3;

export function useCompare() {
  const [items, setItems] = useState<STEResult[]>([]);

  const add = useCallback((item: STEResult) => {
    setItems((prev) => {
      if (prev.find((i) => i.id === item.id)) return prev;
      if (prev.length >= MAX) return prev;
      return [...prev, item];
    });
  }, []);

  const remove = useCallback((id: number) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  }, []);

  const clear = useCallback(() => setItems([]), []);

  const has = useCallback(
    (id: number) => items.some((i) => i.id === id),
    [items]
  );

  return { items, add, remove, clear, has, isFull: items.length >= MAX };
}
