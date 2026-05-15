/**
 * Painel lateral de estado do jogador.
 *
 * Consome o GET /state — exibe ficha do personagem (via CharacterSheet),
 * inventário, localização atual, objetivos cumpridos. Nada de estado
 * oculto (o backend já filtra; o frontend reflete só o que vem).
 *
 * O botão "voltar" desconecta da partida e leva à landing — o id
 * anônimo continua sendo a forma de retomar.
 */

import type { CampaignStateResponse } from "../api/types";
import { useT } from "../i18n";
import { CharacterSheet } from "./CharacterSheet";

interface StatePanelProps {
  state: CampaignStateResponse | null;
  loading: boolean;
  onExit: () => void;
}

export function StatePanel({ state, loading, onExit }: StatePanelProps) {
  const t = useT();

  return (
    <div className="state-panel">
      <header className="state-panel__header">
        <h2 className="state-panel__title">{t("state.title")}</h2>
      </header>

      <div className="state-panel__body">
        {loading || !state ? (
          <p className="state-panel__loading">{t("resume.loading")}</p>
        ) : (
          <>
            <CharacterSheet character={state.character} variant="panel" />

            <section className="state-panel__section">
              <h4 className="state-panel__section-title">
                {t("state.locationTitle")}
              </h4>
              <p className="state-panel__location-name">
                {state.location.name}
              </p>
              {state.location.description ? (
                <p className="state-panel__location-desc">
                  {state.location.description}
                </p>
              ) : null}
            </section>

            <section className="state-panel__section">
              <h4 className="state-panel__section-title">
                {t("state.inventoryTitle")}
              </h4>
              {state.inventory.length === 0 ? (
                <p className="state-panel__empty">
                  {t("state.inventoryEmpty")}
                </p>
              ) : (
                <ul className="state-panel__list">
                  {state.inventory.map((item) => (
                    <li key={item.name} className="state-panel__item">
                      <span>{item.name}</span>
                      {item.quantity > 1 ? (
                        <span className="state-panel__item-qty">
                          ×{item.quantity}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="state-panel__section">
              <h4 className="state-panel__section-title">
                {t("state.objectivesTitle")}
              </h4>
              {state.flags.objectives_completed.length === 0 ? (
                <p className="state-panel__empty">
                  {t("state.objectivesEmpty")}
                </p>
              ) : (
                <ul className="state-panel__list">
                  {state.flags.objectives_completed.map((obj) => (
                    <li key={obj}>{obj}</li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>

      <footer className="state-panel__footer">
        <button
          type="button"
          className="state-panel__exit"
          onClick={onExit}
          title={t("resume.back")}
        >
          {t("resume.back")}
        </button>
      </footer>
    </div>
  );
}
