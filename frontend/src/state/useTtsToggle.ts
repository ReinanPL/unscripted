import { useCallback, useEffect, useState } from "react";

/**
 * Toggle de narração falada (TTS), persistido em `localStorage`.
 *
 * - Default: OFF. Liga TTS = custo extra ao backend (~$0.001/turno);
 *   acessibilidade nem sempre quer voz; jogador escolhe.
 * - Persistência sobrevive a F5 e fechar/abrir o navegador.
 * - Chave: `unscripted.tts_enabled`. Valores: "true" | "false".
 * - Se `localStorage` estiver indisponível (contexto inseguro, modo
 *   privado restrito), o estado vive só em memória — o jogador pode
 *   ligar/desligar, mas não persiste. Não é fatal.
 *
 * Decisão registrada em ADR-049.
 */

const STORAGE_KEY = "unscripted.tts_enabled";

function readInitial(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function useTtsToggle(): [boolean, (next: boolean) => void] {
  const [enabled, setEnabledState] = useState<boolean>(readInitial);

  // Sincroniza outras abas/janelas via evento `storage`.
  useEffect(() => {
    function onStorage(event: StorageEvent) {
      if (event.key !== STORAGE_KEY) return;
      setEnabledState(event.newValue === "true");
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const setEnabled = useCallback((next: boolean) => {
    setEnabledState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next ? "true" : "false");
    } catch {
      // localStorage indisponível — estado vive só em memória.
    }
  }, []);

  return [enabled, setEnabled];
}
