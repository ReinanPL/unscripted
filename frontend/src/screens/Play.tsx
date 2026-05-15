/**
 * Tela de jogo. Orquestra:
 *   - carregamento do log e do estado iniciais
 *   - envio da ação (POST /campaigns/{id}/action) com streaming SSE
 *   - preservação do input em caso de erro/recusa (ADR-020)
 *   - exibição do estado, do grafo e do painel de pensamento do mestre
 *
 * Painéis ainda em construção: state, scene/graph e trace recebem
 * placeholders nas próximas tarefas (6.11, 6.12, 6.13).
 */

import { useEffect, useState } from "react";

import {
  getCampaignLog,
  getCampaignState,
  isNetworkError,
  streamAction,
} from "../api";
import type { ActionEvent, CampaignStateResponse } from "../api/types";
import { ActionInput } from "../components/ActionInput";
import { Layout } from "../components/Layout";
import { Narration, type NarrationTurn } from "../components/Narration";
import { useT } from "../i18n";
import { useSession } from "../state/session";

interface ErrorBanner {
  message: string;
  variant: "robustness" | "error";
}

export function Play() {
  const t = useT();
  const { campaignId, reset } = useSession();
  const [turns, setTurns] = useState<NarrationTurn[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<ErrorBanner | null>(null);
  const [state, setState] = useState<CampaignStateResponse | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);

  // Bootstrap: carrega state + log na entrada.
  useEffect(() => {
    if (!campaignId) return;
    let cancelled = false;

    async function bootstrap(id: string) {
      try {
        const [s, l] = await Promise.all([
          getCampaignState(id),
          getCampaignLog(id),
        ]);
        if (cancelled) return;
        setState(s);
        setTurns(
          l.history.map(
            (entry): NarrationTurn => ({
              turnNumber: entry.turn,
              playerAction: entry.player_action,
              narrationChunks: [entry.narration],
              npcChunks: [],
            }),
          ),
        );
      } catch {
        if (cancelled) return;
        setError({ message: t("errors.backendDown"), variant: "error" });
      } finally {
        if (!cancelled) setBootstrapping(false);
      }
    }

    bootstrap(campaignId);
    return () => {
      cancelled = true;
    };
  }, [campaignId, t]);

  async function handleSubmit() {
    if (!campaignId || streaming) return;
    const text = input.trim();
    if (!text) return;
    setError(null);

    const provisional: NarrationTurn = {
      turnNumber: null,
      playerAction: text,
      narrationChunks: [],
      npcChunks: [],
    };
    setTurns((prev) => [...prev, provisional]);
    setStreaming(true);
    setInput("");

    let consumed = false;
    try {
      for await (const ev of streamAction(campaignId, text)) {
        consumed = consumeEvent(ev, {
          setTurns,
          setError,
          setInput,
          fallbackInput: text,
          t,
        });
        if (consumed) break;
      }
    } catch (cause) {
      // Falha de rede ou de protocolo: restaura input e remove turn provisório.
      setTurns((prev) => prev.slice(0, -1));
      setInput(text);
      setError({
        message: isNetworkError(cause)
          ? t("errors.backendDown")
          : t("errors.actionFailed"),
        variant: "error",
      });
    } finally {
      setStreaming(false);
      // Após done: recarrega state para refletir mutações deterministicas.
      if (consumed && campaignId) {
        getCampaignState(campaignId)
          .then(setState)
          .catch(() => undefined);
      }
    }
  }

  if (!campaignId) {
    // Defesa em profundidade — não deveria ocorrer.
    return (
      <Layout
        variant="single"
        narration={
          <div className="placeholder">
            <p>{t("errors.campaignNotFound")}</p>
          </div>
        }
      />
    );
  }

  return (
    <Layout
      state={
        <StatePanelPlaceholder
          loading={bootstrapping}
          state={state}
          onExit={reset}
        />
      }
      narration={
        <div className="play">
          {error ? (
            <div
              className={`play__banner play__banner--${error.variant}`}
              role="alert"
            >
              {error.message}
            </div>
          ) : null}
          <Narration turns={turns} thinking={streaming} />
          {streaming ? (
            <div className="play__thinking" aria-live="polite">
              {t("play.masterThinking")}
            </div>
          ) : null}
          <ActionInput
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            disabled={streaming || bootstrapping}
            focusKey={turns.length}
          />
        </div>
      }
      scene={<ScenePlaceholder />}
    />
  );
}

interface ConsumeArgs {
  setTurns: React.Dispatch<React.SetStateAction<NarrationTurn[]>>;
  setError: React.Dispatch<React.SetStateAction<ErrorBanner | null>>;
  setInput: React.Dispatch<React.SetStateAction<string>>;
  fallbackInput: string;
  t: (key: string) => string;
}

function consumeEvent(ev: ActionEvent, args: ConsumeArgs): boolean {
  const { setTurns, setError, setInput, fallbackInput, t } = args;

  switch (ev.type) {
    case "chunk": {
      setTurns((prev) =>
        updateLast(prev, (turn) => ({
          ...turn,
          narrationChunks: [...turn.narrationChunks, ev.text],
        })),
      );
      return false;
    }
    case "npc_chunk": {
      const npcId = ev.npc_id ?? "npc";
      setTurns((prev) =>
        updateLast(prev, (turn) => {
          const existing = turn.npcChunks.findIndex((g) => g.id === npcId);
          if (existing === -1) {
            return {
              ...turn,
              npcChunks: [...turn.npcChunks, { id: npcId, text: ev.text }],
            };
          }
          const npcChunks = turn.npcChunks.slice();
          npcChunks[existing] = {
            id: npcId,
            text: npcChunks[existing].text + ev.text,
          };
          return { ...turn, npcChunks };
        }),
      );
      return false;
    }
    case "done": {
      setTurns((prev) =>
        updateLast(prev, (turn) => ({
          ...turn,
          turnNumber: ev.turn_number ?? null,
        })),
      );
      return true;
    }
    case "rejected": {
      // ADR-026: turno NÃO consumido. Remove o provisório, restaura
      // o input do jogador.
      setTurns((prev) => prev.slice(0, -1));
      setInput(fallbackInput);
      const category = ev.category ?? "unknown";
      const detail =
        t(`robustness.categories.${category}`) ||
        t("robustness.categories.unknown");
      const reason = ev.text ? ` — ${ev.text}` : "";
      setError({
        message: `${detail}${reason}`,
        variant: "robustness",
      });
      return true;
    }
    case "error_preserve_input": {
      setTurns((prev) => prev.slice(0, -1));
      setInput(fallbackInput);
      setError({
        message: ev.text || t("errors.actionFailed"),
        variant: "error",
      });
      return true;
    }
    case "error":
    default: {
      setTurns((prev) => prev.slice(0, -1));
      setInput(fallbackInput);
      setError({
        message: ev.text || t("errors.generic"),
        variant: "error",
      });
      return true;
    }
  }
}

function updateLast<T>(arr: T[], updater: (item: T) => T): T[] {
  if (arr.length === 0) return arr;
  const copy = arr.slice();
  copy[copy.length - 1] = updater(copy[copy.length - 1]);
  return copy;
}

// Placeholders das outras zonas — substituídos nos próximos commits.

interface StatePanelPlaceholderProps {
  loading: boolean;
  state: CampaignStateResponse | null;
  onExit: () => void;
}

function StatePanelPlaceholder({
  loading,
  state,
  onExit,
}: StatePanelPlaceholderProps) {
  const t = useT();
  return (
    <div className="state-panel-placeholder">
      <h2 className="state-panel-placeholder__title">{t("state.title")}</h2>
      {loading || !state ? (
        <p className="state-panel-placeholder__loading">
          {t("resume.loading")}
        </p>
      ) : (
        <ul className="state-panel-placeholder__list">
          <li>{state.character.name}</li>
          <li>
            HP {state.character.hp_current}/{state.character.hp_max}
          </li>
          <li>{state.location.name}</li>
        </ul>
      )}
      <button
        type="button"
        className="state-panel-placeholder__exit"
        onClick={onExit}
      >
        {t("resume.back")}
      </button>
    </div>
  );
}

function ScenePlaceholder() {
  const t = useT();
  return (
    <div className="scene-placeholder">
      <h2 className="scene-placeholder__title">{t("graph.title")}</h2>
      <p className="scene-placeholder__hint">{t("graph.empty")}</p>
    </div>
  );
}
