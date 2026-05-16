/**
 * Tela de jogo. Orquestra:
 *   - carregamento do log, do estado e do grafo iniciais
 *   - envio da ação (POST /campaigns/{id}/action) com streaming SSE
 *   - preservação do input em caso de erro/recusa (ADR-020)
 *   - exibição do estado, do grafo e do painel de pensamento do mestre
 */

import { useEffect, useState } from "react";

import {
  getCampaignGraph,
  getCampaignLog,
  getCampaignState,
  getTurnTrace,
  isNetworkError,
  isNotFound,
  streamAction,
  ttsToBlob,
} from "../api";
import type {
  ActionEvent,
  CampaignStateResponse,
  GraphResponse,
} from "../api/types";
import { ActionInput } from "../components/ActionInput";
import { CharacterModal } from "../components/CharacterModal";
import { ErrorBanner } from "../components/ErrorBanner";
import { Layout } from "../components/Layout";
import { LocationGraph } from "../components/LocationGraph";
import { MasterThinking } from "../components/MasterThinking";
import { MasterThoughtPanel } from "../components/MasterThoughtPanel";
import { Narration, type NarrationTurn } from "../components/Narration";
import { RobustnessBanner } from "../components/RobustnessBanner";
import { SceneImage } from "../components/SceneImage";
import { StatusCompact } from "../components/StatusCompact";
import { TtsToggle } from "../components/TtsToggle";
import { useT } from "../i18n";
import { useAudioQueue } from "../state/useAudioQueue";
import { useSession } from "../state/session";
import { usePrevious } from "../state/usePrevious";
import { useTtsToggle } from "../state/useTtsToggle";

type Banner =
  | { kind: "robustness"; category: string; reason: string }
  | { kind: "error"; message: string; fatal?: boolean };

export function Play() {
  const t = useT();
  const { campaignId, reset } = useSession();
  const [turns, setTurns] = useState<NarrationTurn[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [banner, setBanner] = useState<Banner | null>(null);
  const [state, setState] = useState<CampaignStateResponse | null>(null);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  // Número do último turno consumido nesta sessão.
  // Decisão da Fase 6: começa null mesmo após retomada — sem
  // navegação em traces históricos na v1.
  const [lastTurnNumber, setLastTurnNumber] = useState<number | null>(null);
  const [showSheet, setShowSheet] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useTtsToggle();
  const audioQueue = useAudioQueue();

  function handleTtsToggle(next: boolean) {
    setTtsEnabled(next);
    if (next) {
      // Liga: destrava autoplay tocando um buffer silencioso dentro do
      // user gesture (click). Sem isso, o blob real que chegar depois
      // do `done` do SSE seria bloqueado pela política de autoplay.
      audioQueue.unlock();
    } else {
      // Desliga mid-turno: interrompe áudio que estiver tocando e
      // esvazia a fila (ADR-049).
      audioQueue.clear();
    }
  }

  // Atalho global: tecla "C" alterna o modal da ficha. Ignora quando
  // o foco está num input/textarea (jogador digitando ação) ou quando
  // há modificador (Ctrl+C, Cmd+C continuam funcionando).
  useEffect(() => {
    function handler(ev: KeyboardEvent) {
      if (ev.key.toLowerCase() !== "c") return;
      if (ev.ctrlKey || ev.altKey || ev.metaKey) return;
      const active = document.activeElement;
      if (active) {
        const tag = active.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA") return;
        if ((active as HTMLElement).isContentEditable) return;
      }
      ev.preventDefault();
      setShowSheet((v) => !v);
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Pulso de dano (PRD §6.6) — quando HP cai entre dois turnos.
  const [damageFlash, setDamageFlash] = useState(false);
  const prevHp = usePrevious(state?.character.hp_current ?? null);

  useEffect(() => {
    const curr = state?.character.hp_current;
    if (prevHp === null || curr === undefined) return;
    if (curr < prevHp) {
      setDamageFlash(true);
      const handle = setTimeout(() => setDamageFlash(false), 820);
      return () => clearTimeout(handle);
    }
  }, [state?.character.hp_current, prevHp]);

  useEffect(() => {
    if (!damageFlash) return;
    document.body.classList.add("fx-damage-flash");
    return () => document.body.classList.remove("fx-damage-flash");
  }, [damageFlash]);

  // Bootstrap: carrega state + log + graph na entrada.
  useEffect(() => {
    if (!campaignId) return;
    let cancelled = false;

    async function bootstrap(id: string) {
      try {
        const [s, l, g] = await Promise.all([
          getCampaignState(id),
          getCampaignLog(id),
          getCampaignGraph(id),
        ]);
        if (cancelled) return;
        setState(s);
        setGraph(g);
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
      } catch (cause) {
        if (cancelled) return;
        if (isNotFound(cause)) {
          setBanner({
            kind: "error",
            message: t("errors.campaignNotFound"),
            fatal: true,
          });
        } else {
          setBanner({ kind: "error", message: t("errors.backendDown") });
        }
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
    // Diagnóstico: console.warn sobrevive a qualquer filtro default.
    console.warn("[tts] submit", { ttsEnabled });
    if (ttsEnabled) {
      // Destrava autoplay aproveitando este click como user gesture.
      // Cobre o caso "toggle restaurado do localStorage sem click direto"
      // — sem isso, o blob real cai num play() bloqueado silenciosamente.
      audioQueue.unlock();
    }
    setBanner(null);

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
    let consumedTurnNumber: number | null = null;
    let consumedNarration = "";
    try {
      for await (const ev of streamAction(campaignId, text)) {
        consumed = consumeEvent(ev, {
          setTurns,
          setBanner,
          setInput,
          setLastTurnNumber,
          fallbackInput: text,
          t,
          onTurnComplete: (narration) => {
            consumedNarration = narration;
          },
        });
        if (consumed) {
          if (ev.type === "done" && ev.turn_number != null) {
            consumedTurnNumber = ev.turn_number;
          }
          break;
        }
      }
    } catch (cause) {
      // Falha de rede ou de protocolo: restaura input e remove turn provisório.
      setTurns((prev) => prev.slice(0, -1));
      setInput(text);
      setBanner({
        kind: "error",
        message: isNetworkError(cause)
          ? t("errors.backendDown")
          : t("errors.actionFailed"),
      });
    } finally {
      setStreaming(false);
      if (consumed && campaignId) {
        // TTS turno-inteiro (Bloco 2 / ADR-049): com toggle ligado e
        // narração disponível, pede o áudio do turno e enfileira no
        // useAudioQueue. Sincronia frase-a-frase entra no Bloco 3.
        if (ttsEnabled && consumedNarration) {
          console.info("[tts] requesting", consumedNarration.length, "chars");
          ttsToBlob(consumedNarration)
            .then((blob) => {
              if (blob) {
                console.info("[tts] received blob", blob.size, "bytes");
                audioQueue.enqueue(blob);
              } else {
                console.warn("[tts] backend returned empty audio");
              }
            })
            .catch((err) => {
              console.error("[tts] request failed", err);
            });
        }

        // Recarrega state e graph para refletir mutacoes deterministicas
        // (location nova, locations_revealed expandido).
        getCampaignState(campaignId)
          .then(setState)
          .catch(() => undefined);
        getCampaignGraph(campaignId)
          .then(setGraph)
          .catch(() => undefined);
        // Busca trace e classifica critico se houve rolagem com margem
        // grande, atualizando o ultimo turn (Narration aplica destaque).
        if (consumedTurnNumber !== null) {
          getTurnTrace(campaignId, consumedTurnNumber)
            .then((resp) => {
              const margin = resp.trace.roll_outcome?.check.margin;
              if (margin === undefined) return;
              const outcome: NarrationTurn["outcome"] =
                margin >= 10
                  ? "crit-success"
                  : margin <= -10
                    ? "crit-fail"
                    : undefined;
              if (!outcome) return;
              setTurns((prev) => {
                if (prev.length === 0) return prev;
                const copy = prev.slice();
                copy[copy.length - 1] = {
                  ...copy[copy.length - 1],
                  outcome,
                };
                return copy;
              });
            })
            .catch(() => undefined);
        }
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
    <>
    <Layout
      onExit={reset}
      headerExtras={
        <TtsToggle enabled={ttsEnabled} onChange={handleTtsToggle} />
      }
      narration={
        <>
          {banner !== null ? (
            banner.kind === "robustness" ? (
              <RobustnessBanner
                category={banner.category}
                reason={banner.reason}
                onDismiss={() => setBanner(null)}
              />
            ) : (
              <ErrorBanner
                message={banner.message}
                fatal={banner.fatal}
                onDismiss={() => setBanner(null)}
                onRecover={reset}
              />
            )
          ) : null}
          <Narration turns={turns} thinking={streaming} />
          {streaming ? <MasterThinking /> : null}
        </>
      }
      inputBar={
        <ActionInput
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          disabled={streaming || bootstrapping}
          focusKey={turns.length}
          onVoiceUnavailable={() =>
            setBanner({
              kind: "error",
              message: t("voice.notAvailable"),
            })
          }
        />
      }
      thoughtPanel={
        <MasterThoughtPanel
          campaignId={campaignId}
          lastTurnNumber={lastTurnNumber}
        />
      }
      scene={
        <>
          {state ? (
            <SceneImage
              chapterDir="01"
              imageId={`img-${state.location.id.replace(/_/g, "-")}`}
              sceneName={state.location.name}
            />
          ) : null}
          <LocationGraph graph={graph} loading={bootstrapping} />
          <StatusCompact
            state={state}
            loading={bootstrapping}
            onOpenSheet={() => setShowSheet(true)}
          />
        </>
      }
    />
    <CharacterModal
      open={showSheet}
      onClose={() => setShowSheet(false)}
      state={state}
    />
    </>
  );
}

interface ConsumeArgs {
  setTurns: React.Dispatch<React.SetStateAction<NarrationTurn[]>>;
  setBanner: React.Dispatch<React.SetStateAction<Banner | null>>;
  setInput: React.Dispatch<React.SetStateAction<string>>;
  setLastTurnNumber: React.Dispatch<React.SetStateAction<number | null>>;
  fallbackInput: string;
  t: (key: string) => string;
  /** Recebe a narração consolidada (narração + falas de NPC) quando o
   *  turno fecha com `done`. Usado pelo Play para disparar TTS. */
  onTurnComplete?: (narration: string) => void;
}

function consolidatedNarration(turn: NarrationTurn): string {
  const parts: string[] = [];
  const main = turn.narrationChunks.join("").trim();
  if (main) parts.push(main);
  for (const npc of turn.npcChunks) {
    const text = npc.text.trim();
    if (text) parts.push(text);
  }
  return parts.join("\n\n");
}

function consumeEvent(ev: ActionEvent, args: ConsumeArgs): boolean {
  const {
    setTurns,
    setBanner,
    setInput,
    setLastTurnNumber,
    fallbackInput,
    t,
    onTurnComplete,
  } = args;

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
      setTurns((prev) => {
        const next = updateLast(prev, (turn) => ({
          ...turn,
          turnNumber: ev.turn_number ?? null,
        }));
        // Captura narração consolidada antes de retornar.
        if (next.length > 0 && onTurnComplete) {
          onTurnComplete(consolidatedNarration(next[next.length - 1]));
        }
        return next;
      });
      if (ev.turn_number !== null && ev.turn_number !== undefined) {
        setLastTurnNumber(ev.turn_number);
      }
      return true;
    }
    case "rejected": {
      // ADR-026: turno NÃO consumido. Remove o provisório, restaura
      // o input do jogador.
      setTurns((prev) => prev.slice(0, -1));
      setInput(fallbackInput);
      setBanner({
        kind: "robustness",
        category: ev.category ?? "unknown",
        reason: ev.text,
      });
      return true;
    }
    case "error_preserve_input": {
      setTurns((prev) => prev.slice(0, -1));
      setInput(fallbackInput);
      setBanner({
        kind: "error",
        message: ev.text || t("errors.actionFailed"),
      });
      return true;
    }
    case "error":
    default: {
      // Backend sinalizou erro fatal (geralmente: campanha sumiu/expirou).
      // Mantemos o input para o caso de o jogador querer copiar; a recuperação
      // dele é voltar à landing, não tentar de novo.
      setTurns((prev) => prev.slice(0, -1));
      setInput(fallbackInput);
      setBanner({
        kind: "error",
        message: ev.text || t("errors.campaignNotFound"),
        fatal: true,
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

