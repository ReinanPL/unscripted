/**
 * Tipos e Context do roteamento state-driven (ADR-037).
 *
 * Em arquivo separado do Provider para que o react-refresh funcione:
 * o arquivo do Provider só exporta componente; o hook e os tipos vivem
 * aqui.
 */

import { createContext, useContext } from "react";

export type Screen = "landing" | "create" | "resume" | "play";

export interface SessionContextValue {
  screen: Screen;
  campaignId: string | null;
  goTo: (screen: Screen) => void;
  startCampaign: (campaignId: string) => void;
  reset: () => void;
}

export const SessionContext = createContext<SessionContextValue | null>(null);

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error("useSession must be used inside <SessionProvider>");
  }
  return ctx;
}
