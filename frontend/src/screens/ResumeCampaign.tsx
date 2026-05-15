/**
 * Tela de retomada de partida.
 *
 * Não há login na v1 (ADR-013) — o ID anônimo é a única forma de
 * voltar para uma partida em andamento. A tela valida o ID chamando
 * GET /state (404 ⇒ não existe). Sucesso entra direto na tela de
 * jogo.
 */

import { useState } from "react";

import {
  ApiError,
  getCampaignState,
  isNetworkError,
  isNotFound,
} from "../api";
import { useT } from "../i18n";
import { useSession } from "../state/session";

const UUID_RE =
  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

type Phase =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string };

export function ResumeCampaign() {
  const t = useT();
  const { goTo, startCampaign } = useSession();
  const [id, setId] = useState("");
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  const idClean = id.trim();
  const idLooksValid = UUID_RE.test(idClean);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!idLooksValid || phase.kind === "loading") return;
    setPhase({ kind: "loading" });
    try {
      await getCampaignState(idClean);
      startCampaign(idClean);
    } catch (error) {
      if (isNotFound(error)) {
        setPhase({ kind: "error", message: t("resume.notFound") });
      } else if (isNetworkError(error)) {
        setPhase({ kind: "error", message: t("errors.backendDown") });
      } else if (error instanceof ApiError) {
        setPhase({ kind: "error", message: t("resume.error") });
      } else {
        setPhase({ kind: "error", message: t("errors.generic") });
      }
    }
  }

  const loading = phase.kind === "loading";

  return (
    <div className="resume">
      <header className="resume__header">
        <h2 className="resume__title">{t("resume.title")}</h2>
        <p className="resume__subtitle">{t("resume.subtitle")}</p>
      </header>

      <form className="resume__form" onSubmit={handleSubmit}>
        <label className="resume__label" htmlFor="resume-id">
          {t("resume.idLabel")}
        </label>
        <input
          id="resume-id"
          type="text"
          inputMode="text"
          autoComplete="off"
          autoFocus
          spellCheck={false}
          className="resume__input"
          placeholder={t("resume.idPlaceholder")}
          value={id}
          onChange={(e) => {
            setId(e.target.value);
            if (phase.kind === "error") setPhase({ kind: "idle" });
          }}
          disabled={loading}
        />

        {phase.kind === "error" ? (
          <p className="resume__error" role="alert">
            {phase.message}
          </p>
        ) : null}

        <div className="resume__actions">
          <button
            type="button"
            className="resume__back"
            onClick={() => goTo("landing")}
            disabled={loading}
          >
            {t("resume.back")}
          </button>
          <button
            type="submit"
            className="resume__submit"
            disabled={!idLooksValid || loading}
          >
            {loading ? t("resume.loading") : t("resume.submit")}
          </button>
        </div>
      </form>
    </div>
  );
}
