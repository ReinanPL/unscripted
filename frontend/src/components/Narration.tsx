/**
 * Zona de narração: a coluna central da tela de jogo.
 *
 * Renderiza turnos como uma sequência: ação do jogador → narração do
 * mestre → fala de NPC (quando há). Chunks da narração vão sendo
 * adicionados em tempo real (SSE) — o último turno pode estar em
 * andamento.
 *
 * Sem framework de bolhas de chat — a aparência é de leitura, não
 * de mensagem. Fala de NPC sai destacada como bloco lateral em
 * itálico.
 */

import { useEffect, useRef } from "react";

import { useT } from "../i18n";

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
        <article key={idx} className="narration__turn">
          <p className="narration__player" aria-label="Ação do jogador">
            {turn.playerAction}
          </p>

          {turn.narrationChunks.length > 0 ? (
            <p className="narration__master">
              {turn.narrationChunks.join("")}
              {turn.turnNumber === null && idx === turns.length - 1 ? (
                <span className="narration__cursor" aria-hidden="true" />
              ) : null}
            </p>
          ) : null}

          {turn.npcChunks.map((npc, npcIdx) => (
            <aside
              key={`${npc.id}-${npcIdx}`}
              className="narration__npc"
              aria-label={`Fala de ${npc.id}`}
            >
              <header className="narration__npc-name">{npc.id}</header>
              <p className="narration__npc-text">
                {t("play.npcSpeakingPrefix")}
                {npc.text}
              </p>
            </aside>
          ))}
        </article>
      ))}
    </div>
  );
}
