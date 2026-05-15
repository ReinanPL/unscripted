import { useEffect, useRef } from "react";

/**
 * Hook que retorna o valor anterior de uma prop/state, ou `null`
 * no primeiro render. Útil para reagir a mudanças (ex.: queda de HP).
 */
export function usePrevious<T>(value: T): T | null {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    ref.current = value;
  }, [value]);
  return ref.current;
}
