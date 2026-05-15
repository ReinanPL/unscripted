/**
 * Painel "pensamento do mestre" (PRD §6.7).
 *
 * Drawer recolhível ancorado no rodapé: exibe o trace do último
 * turno consumido — ruling do Referee, trechos recuperados do RAG,
 * resultado da rolagem, consequência aplicada, reação de NPC.
 * Mostra `error` quando o turno tropeçou.
 *
 * Comportamento na retomada (decisão da Fase 6): inicia recolhido e,
 * quando aberto pela primeira vez sem turno na sessão atual, mostra
 * uma mensagem de espera. Navegação em traces históricos não é v1.
 */

import { useEffect, useState } from "react";

import { getTurnTrace } from "../api";
import type { TurnTrace } from "../api/types";
import { useT } from "../i18n";

interface MasterThoughtPanelProps {
  campaignId: string;
  /** Número do último turno completado nesta sessão. null se ainda nenhum. */
  lastTurnNumber: number | null;
}

export function MasterThoughtPanel({
  campaignId,
  lastTurnNumber,
}: MasterThoughtPanelProps) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [trace, setTrace] = useState<TurnTrace | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (lastTurnNumber === null) {
      setTrace(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setErrorMessage(null);
    getTurnTrace(campaignId, lastTurnNumber)
      .then((resp) => {
        if (cancelled) return;
        setTrace(resp.trace);
      })
      .catch(() => {
        if (cancelled) return;
        setErrorMessage(t("errors.generic"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [campaignId, lastTurnNumber, t]);

  return (
    <aside
      className={
        "thought-panel" + (open ? " thought-panel--open" : "")
      }
      aria-label={t("trace.title")}
    >
      <button
        type="button"
        className="thought-panel__toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="thought-panel-body"
      >
        <span className="thought-panel__caret" aria-hidden="true">
          {open ? "▾" : "▴"}
        </span>
        <span className="thought-panel__label">{t("trace.title")}</span>
        {lastTurnNumber !== null ? (
          <span className="thought-panel__turn">#{lastTurnNumber}</span>
        ) : null}
      </button>

      {open ? (
        <div id="thought-panel-body" className="thought-panel__body">
          <TraceBody
            trace={trace}
            loading={loading}
            errorMessage={errorMessage}
            hasTurn={lastTurnNumber !== null}
          />
        </div>
      ) : null}
    </aside>
  );
}

interface TraceBodyProps {
  trace: TurnTrace | null;
  loading: boolean;
  errorMessage: string | null;
  hasTurn: boolean;
}

function TraceBody({ trace, loading, errorMessage, hasTurn }: TraceBodyProps) {
  const t = useT();
  if (!hasTurn) {
    return <p className="thought-panel__empty">{t("trace.empty")}</p>;
  }
  if (loading) {
    return <p className="thought-panel__empty">{t("resume.loading")}</p>;
  }
  if (errorMessage) {
    return (
      <p className="thought-panel__error" role="alert">
        {errorMessage}
      </p>
    );
  }
  if (!trace) return null;

  return (
    <div className="thought-panel__sections">
      {trace.error ? (
        <section
          className="thought-panel__section thought-panel__section--error"
          role="alert"
        >
          <h4 className="thought-panel__section-title">
            {t("errors.actionFailed")}
          </h4>
          <p>{trace.error}</p>
        </section>
      ) : null}

      <RulingBlock trace={trace} />
      <RetrievalBlock
        title={t("trace.retrievalRulesTitle")}
        items={trace.retrieval_rules}
      />
      <RetrievalBlock
        title={t("trace.retrievalLoreTitle")}
        items={trace.retrieval_lore}
      />
      <RollBlock trace={trace} />
      <ConsequenceBlock trace={trace} />
      <NpcReactionBlock trace={trace} />
    </div>
  );
}

function RulingBlock({ trace }: { trace: TurnTrace }) {
  const t = useT();
  const ruling = trace.ruling;
  if (!ruling) return null;
  return (
    <section className="thought-panel__section">
      <h4 className="thought-panel__section-title">{t("trace.rulingTitle")}</h4>
      {ruling.precisa_rolagem ? (
        <dl className="thought-panel__dl">
          {ruling.pericia ? (
            <>
              <dt>{t("trace.rulingSkill")}</dt>
              <dd>{ruling.pericia}</dd>
            </>
          ) : null}
          {ruling.dificuldade !== null && ruling.dificuldade !== undefined ? (
            <>
              <dt>{t("trace.rulingDifficulty")}</dt>
              <dd>DC {ruling.dificuldade}</dd>
            </>
          ) : null}
          {ruling.motivo_dificuldade ? (
            <>
              <dt>{t("trace.rulingReason")}</dt>
              <dd>{ruling.motivo_dificuldade}</dd>
            </>
          ) : null}
        </dl>
      ) : (
        <p className="thought-panel__paragraph">{t("trace.rulingNoRoll")}</p>
      )}
    </section>
  );
}

function RetrievalBlock({
  title,
  items,
}: {
  title: string;
  items: TurnTrace["retrieval_rules"];
}) {
  const t = useT();
  return (
    <section className="thought-panel__section">
      <h4 className="thought-panel__section-title">{title}</h4>
      {items.length === 0 ? (
        <p className="thought-panel__empty">{t("trace.retrievalEmpty")}</p>
      ) : (
        <ul className="thought-panel__retrieval">
          {items.map((snippet, idx) => (
            <li key={idx} className="thought-panel__snippet">
              <header className="thought-panel__snippet-source">
                {t("trace.retrievalSource")}: {snippet.source}
              </header>
              <p className="thought-panel__snippet-content">
                {snippet.content}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function RollBlock({ trace }: { trace: TurnTrace }) {
  const t = useT();
  if (!trace.roll_outcome) return null;
  const { roll, check } = trace.roll_outcome;
  return (
    <section className="thought-panel__section">
      <h4 className="thought-panel__section-title">{t("trace.rollTitle")}</h4>
      <dl className="thought-panel__dl">
        <dt>{t("trace.rollNotation")}</dt>
        <dd>
          {roll.notation} → [{roll.rolls.join(", ")}]
          {roll.modifier !== 0
            ? ` ${roll.modifier > 0 ? "+" : ""}${roll.modifier}`
            : ""}
        </dd>
        <dt>{t("trace.rollTotal")}</dt>
        <dd>
          <strong>{roll.total}</strong>
          {roll.advantage ? " (vantagem)" : ""}
          {roll.disadvantage ? " (desvantagem)" : ""}
        </dd>
        <dt>{t("trace.rollOutcome")}</dt>
        <dd
          className={
            check.success
              ? "thought-panel__outcome thought-panel__outcome--success"
              : "thought-panel__outcome thought-panel__outcome--failure"
          }
        >
          {check.success ? t("trace.rollSuccess") : t("trace.rollFailure")}{" "}
          ({check.margin >= 0 ? "+" : ""}
          {check.margin} vs DC {check.difficulty})
        </dd>
      </dl>
    </section>
  );
}

function ConsequenceBlock({ trace }: { trace: TurnTrace }) {
  const t = useT();
  const c = trace.consequence_applied;
  if (!c) return null;
  return (
    <section className="thought-panel__section">
      <h4 className="thought-panel__section-title">
        {t("trace.consequenceTitle")}
      </h4>
      <ul className="thought-panel__list">
        {c.hp_delta !== null && c.hp_delta !== undefined && c.hp_delta !== 0 ? (
          <li>
            HP {c.hp_delta > 0 ? "+" : ""}
            {c.hp_delta}
          </li>
        ) : null}
        {c.new_location ? <li>Locação: {c.new_location.name}</li> : null}
        {c.items_added.map((i) => (
          <li key={`add-${i.name}`}>
            + {i.name}
            {i.quantity > 1 ? ` ×${i.quantity}` : ""}
          </li>
        ))}
        {c.items_removed.map((i) => (
          <li key={`rem-${i.name}`}>
            − {i.name}
            {i.quantity > 1 ? ` ×${i.quantity}` : ""}
          </li>
        ))}
        {c.events_occurred.map((e) => (
          <li key={`ev-${e}`}>Evento: {e}</li>
        ))}
        {c.objectives_completed.map((o) => (
          <li key={`obj-${o}`}>Objetivo cumprido: {o}</li>
        ))}
      </ul>
    </section>
  );
}

function NpcReactionBlock({ trace }: { trace: TurnTrace }) {
  const t = useT();
  if (!trace.npc_reaction) return null;
  return (
    <section className="thought-panel__section">
      <h4 className="thought-panel__section-title">
        {t("trace.npcReactionTitle")}
        {trace.npc_id ? ` — ${trace.npc_id}` : ""}
      </h4>
      <p className="thought-panel__paragraph thought-panel__paragraph--italic">
        {trace.npc_reaction}
      </p>
    </section>
  );
}
