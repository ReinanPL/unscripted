/**
 * Zona de narração: a coluna central da tela de jogo.
 *
 * Renderiza turnos como uma sequência: ação do jogador → narração do
 * mestre → fala de NPC (quando há). Chunks da narração vão sendo
 * adicionados em tempo real (SSE) — o último turno pode estar em
 * andamento.
 *
 * Cada turno usa `useTypewriter` para revelar o texto em ritmo
 * editorial (~40 chars/s) em vez do ritmo bruto do LLM, que é rápido
 * demais para leitura de RPG. Turnos já fechados (turnNumber !== null)
 * pulam a animação — útil ao retomar uma campanha com history pronto.
 *
 * Sem framework de bolhas de chat — a aparência é de leitura, não
 * de mensagem. Fala de NPC sai destacada como bloco lateral em
 * itálico.
 */

import { useEffect, useRef } from "react";

import { useT } from "../i18n";
import { useTypewriter } from "../state/useTypewriter";

const CHARS_PER_SECOND = 40;

export interface NpcChunkGroup {
  id: string;
  text: string;
}

export interface NarrationTurn {
  /** number quando o turno encerrou (done), null enquanto em andamento. */
  turnNumber: number | null;
  playerAction: string;
  narrationChunks: string[];
  npcChunks: NpcChunkGroup[];
  /** Destaque visual quando a rolagem deu margem critica (PRD §6.6). */
  outcome?: "crit-success" | "crit-fail";
}

interface NarrationProps {
  turns: NarrationTurn[];
  thinking: boolean;
}

export function Narration({ turns, thinking }: NarrationProps) {
  const t = useT();
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll para o final quando turns ou thinking mudam.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [turns, thinking]);

  return (
    <div className="narration" ref={scrollRef}>
      {turns.length === 0 && !thinking ? (
        <p className="narration__empty">{t("play.inputPlaceholder")}</p>
      ) : null}

      {turns.map((turn, idx) => (
        <NarrationTurnView
          key={idx}
          turn={turn}
          isLast={idx === turns.length - 1}
        />
      ))}
    </div>
  );
}

interface NarrationTurnViewProps {
  turn: NarrationTurn;
  isLast: boolean;
}

function NarrationTurnView({ turn, isLast }: NarrationTurnViewProps) {
  const t = useT();
  const fullNarration = turn.narrationChunks.join("");
  // Turnos vindos do log (já fechados) ou turnos persistidos pulam a
  // animação. Só o último turno em andamento usa o typewriter pra
  // controlar a cadência.
  const displayed = useTypewriter(fullNarration, CHARS_PER_SECOND, {
    skip: turn.turnNumber !== null && !isLast,
  });
  const isStreaming = turn.turnNumber === null;
  const showCursor = isStreaming && isLast;

  return (
    <article
      className={
        "narration__turn" +
        (turn.outcome ? ` narration__turn--${turn.outcome}` : "")
      }
    >
      {turn.playerAction ? (
        <p className="narration__player" aria-label="Ação do jogador">
          {turn.playerAction}
        </p>
      ) : null}

      {fullNarration ? (
        <p
          className={
            "narration__master" +
            (turn.playerAction ? "" : " narration__master--opening")
          }
        >
          {displayed}
          {showCursor ? (
            <span className="narration__cursor" aria-hidden="true" />
          ) : null}
        </p>
      ) : null}

      {turn.npcChunks.map((npc, npcIdx) => (
        <NpcChunkView
          key={`${npc.id}-${npcIdx}`}
          npc={npc}
          t={t}
          skip={turn.turnNumber !== null && !isLast}
        />
      ))}
    </article>
  );
}

interface NpcChunkViewProps {
  npc: NpcChunkGroup;
  t: ReturnType<typeof useT>;
  skip: boolean;
}

function NpcChunkView({ npc, t, skip }: NpcChunkViewProps) {
  const displayed = useTypewriter(npc.text, CHARS_PER_SECOND, { skip });
  return (
    <aside className="narration__npc" aria-label={`Fala de ${npc.id}`}>
      <header className="narration__npc-name">{npc.id}</header>
      <p className="narration__npc-text">
        {t("play.npcSpeakingPrefix")}
        {displayed}
      </p>
    </aside>
  );
}
