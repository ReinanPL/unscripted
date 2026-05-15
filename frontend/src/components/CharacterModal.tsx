/**
 * Modal de ficha completa do personagem.
 *
 * Acionado por botão "VER FICHA" no rodapé da coluna direita. Usa o
 * `<dialog>` nativo (showModal) para ganhar foco preso, fechamento
 * por ESC e backdrop semitransparente sem CSS extra. Conteúdo: ficha
 * (HP, atributos, perícias, equipamento), localização atual,
 * inventário e objetivos cumpridos — toda a informação que vivia na
 * coluna esquerda antes do layout ser reorganizado.
 */

import { useEffect, useRef } from "react";

import type { CampaignStateResponse } from "../api/types";
import { useT } from "../i18n";
import { CharacterSheet } from "./CharacterSheet";

interface CharacterModalProps {
  open: boolean;
  onClose: () => void;
  state: CampaignStateResponse | null;
}

export function CharacterModal({ open, onClose, state }: CharacterModalProps) {
  const t = useT();
  const ref = useRef<HTMLDialogElement | null>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  function handleCancel(event: React.SyntheticEvent<HTMLDialogElement>) {
    // ESC dispara onCancel; o `<dialog>` fecharia sozinho, mas
    // queremos manter o estado React sincronizado.
    event.preventDefault();
    onClose();
  }

  function handleBackdropClick(event: React.MouseEvent<HTMLDialogElement>) {
    // Cliques no backdrop chegam com target === o próprio <dialog>.
    if (event.target === ref.current) onClose();
  }

  if (!state) return null;

  return (
    <dialog
      ref={ref}
      className="character-modal"
      onCancel={handleCancel}
      onClick={handleBackdropClick}
      aria-label={t("state.title")}
    >
      <div className="character-modal__panel">
        <header className="character-modal__header">
          <h2 className="character-modal__title">{t("state.title")}</h2>
          <button
            type="button"
            className="character-modal__close"
            onClick={onClose}
            aria-label={t("common.close")}
          >
            ×
          </button>
        </header>

        <div className="character-modal__body">
          <CharacterSheet character={state.character} variant="panel" />

          <section className="character-modal__section">
            <h4 className="character-modal__section-title">
              {t("state.locationTitle")}
            </h4>
            <p className="character-modal__location-name">
              {state.location.name}
            </p>
            {state.location.description ? (
              <p className="character-modal__location-desc">
                {state.location.description}
              </p>
            ) : null}
          </section>

          <section className="character-modal__section">
            <h4 className="character-modal__section-title">
              {t("state.inventoryTitle")}
            </h4>
            {state.inventory.length === 0 ? (
              <p className="character-modal__empty">
                {t("state.inventoryEmpty")}
              </p>
            ) : (
              <ul className="character-modal__list">
                {state.inventory.map((item) => (
                  <li key={item.name} className="character-modal__item">
                    <span>{item.name}</span>
                    {item.quantity > 1 ? (
                      <span className="character-modal__item-qty">
                        ×{item.quantity}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="character-modal__section">
            <h4 className="character-modal__section-title">
              {t("state.objectivesTitle")}
            </h4>
            {state.flags.objectives_completed.length === 0 ? (
              <p className="character-modal__empty">
                {t("state.objectivesEmpty")}
              </p>
            ) : (
              <ul className="character-modal__list">
                {state.flags.objectives_completed.map((obj) => (
                  <li key={obj}>{obj}</li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </dialog>
  );
}
