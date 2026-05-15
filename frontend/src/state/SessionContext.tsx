/**
 * Roteamento state-driven (ADR-037).
 *
 * 4 telas — landing, create, resume, play — controladas por um state em
 * Context. React Router seria overkill nesse cenário. Não há URLs
 * deep-linkable na v1 (ADR-013).
 *
 * O `campaignId` mora aqui depois que a partida é criada/retomada. Resetar
 * volta para a landing e descarta o id.
 */

import {
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { SessionContext, type Screen, type SessionContextValue } from "./session";

interface SessionProviderProps {
  children: ReactNode;
  initialScreen?: Screen;
}

export function SessionProvider({
  children,
  initialScreen = "landing",
}: SessionProviderProps) {
  const [screen, setScreen] = useState<Screen>(initialScreen);
  const [campaignId, setCampaignId] = useState<string | null>(null);

  const goTo = useCallback((next: Screen) => {
    setScreen(next);
  }, []);

  const startCampaign = useCallback((id: string) => {
    setCampaignId(id);
    setScreen("play");
  }, []);

  const reset = useCallback(() => {
    setCampaignId(null);
    setScreen("landing");
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({ screen, campaignId, goTo, startCampaign, reset }),
    [screen, campaignId, goTo, startCampaign, reset],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}
