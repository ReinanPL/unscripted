/**
 * Tela de criação de partida.
 *
 * Mostra os heróis disponíveis lado a lado com prévia da ficha. Quando
 * o jogador confirma, chama POST /campaigns e exibe o ID anônimo
 * destacado — sem login, sem conta, esse código é a única forma de
 * retomar (ADR-013).
 */

import { useState } from "react";

import { createCampaign, isNetworkError } from "../api";
import { CharacterSheet } from "../components/CharacterSheet";
import { CHARACTER_ORDER, CHARACTER_PRESETS } from "../data/characters";
import { useT } from "../i18n";
import { useSession } from "../state/session";
import type { CharacterClass } from "../api/types";

type Phase =
  | { kind: "choosing" }
  | { kind: "submitting"; chosen: CharacterClass }
  | { kind: "ready"; chosen: CharacterClass; campaignId: string }
  | { kind: "error"; chosen: CharacterClass; message: string };

export function CreateCampaign() {
  const t = useT();
  const { goTo, startCampaign } = useSession();
  const [phase, setPhase] = useState<Phase>({ kind: "choosing" });
  const [selected, setSelected] = useState<CharacterClass>(CHARACTER_ORDER[0]);

  async function handleConfirm() {
    setPhase({ kind: "submitting", chosen: selected });
    try {
      const resp = await createCampaign({ character: selected });
      setPhase({ kind: "ready", chosen: selected, campaignId: resp.campaign_id });
    } catch (error) {
      const message = isNetworkError(error)
        ? t("errors.backendDown")
        : t("errors.generic");
      setPhase({ kind: "error", chosen: selected, message });
    }
  }

  if (phase.kind === "ready") {
    return (
      <SavedIdPanel
        campaignId={phase.campaignId}
        onEnter={() => startCampaign(phase.campaignId)}
      />
    );
  }

  const submitting = phase.kind === "submitting";

  return (
    <div className="create">
      <header className="create__header">
        <h2 className="create__title">{t("create.title")}</h2>
        <p className="create__subtitle">{t("create.subtitle")}</p>
      </header>

      <div className="create__grid">
        {CHARACTER_ORDER.map((cls) => {
          const isSelected = selected === cls;
          const preset = CHARACTER_PRESETS[cls];
          const classMeta = t(`classes.${cls}.name`);
          const classTagline = t(`classes.${cls}.tagline`);
          return (
            <button
              key={cls}
              type="button"
              disabled={submitting}
              className={
                "create__card" + (isSelected ? " create__card--selected" : "")
              }
              onClick={() => setSelected(cls)}
              aria-pressed={isSelected}
            >
              <div className="create__card-head">
                <h3 className="create__card-class">{classMeta}</h3>
                <p className="create__card-tagline">{classTagline}</p>
              </div>
              <CharacterSheet character={preset} variant="preview" />
            </button>
          );
        })}
      </div>

      {phase.kind === "error" ? (
        <p className="create__error" role="alert">
          {phase.message}
        </p>
      ) : null}

      <div className="create__footer">
        <button
          type="button"
          className="create__back"
          onClick={() => goTo("landing")}
          disabled={submitting}
        >
          {t("resume.back")}
        </button>
        <button
          type="button"
          className="create__confirm"
          onClick={handleConfirm}
          disabled={submitting}
        >
          {submitting ? t("create.creating") : t("create.start")}
        </button>
      </div>
    </div>
  );
}

interface SavedIdPanelProps {
  campaignId: string;
  onEnter: () => void;
}

function SavedIdPanel({ campaignId, onEnter }: SavedIdPanelProps) {
  const t = useT();
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(campaignId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard pode falhar em http (Vite dev é seguro). Silenciar.
    }
  }

  return (
    <div className="saved-id">
      <h2 className="saved-id__heading">{t("create.saveIdHeading")}</h2>
      <p className="saved-id__hint">{t("create.saveIdHint")}</p>
      <div className="saved-id__code-wrap">
        <code className="saved-id__code">{campaignId}</code>
        <button
          type="button"
          className="saved-id__copy"
          onClick={handleCopy}
          aria-label="Copiar identificador"
        >
          {copied ? "✓" : "⎘"}
        </button>
      </div>
      <button
        type="button"
        className="saved-id__enter"
        onClick={onEnter}
        autoFocus
      >
        {t("create.start")}
      </button>
    </div>
  );
}
