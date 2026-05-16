import type { ReactNode } from "react";
import { useT } from "../i18n";

interface LayoutProps {
  narration: ReactNode;
  inputBar?: ReactNode;
  thoughtPanel?: ReactNode;
  scene?: ReactNode;
  variant?: "play" | "single";
  /** Quando presente em variant="play", mostra o botão VOLTAR no header. */
  onExit?: () => void;
  /** Controles extras (ex.: toggle TTS) renderizados antes do VOLTAR no header. */
  headerExtras?: ReactNode;
}

export function Layout({
  narration,
  inputBar,
  thoughtPanel,
  scene,
  variant = "play",
  onExit,
  headerExtras,
}: LayoutProps) {
  const t = useT();
  return (
    <div className={`layout layout--${variant}`}>
      <header className="layout__header">
        <h1 className="layout__title">{t("app.title")}</h1>
        <div className="layout__header-actions">
          {headerExtras}
          {onExit ? (
            <button
              type="button"
              className="layout__exit"
              onClick={onExit}
              title={t("resume.back")}
            >
              {t("resume.back")}
            </button>
          ) : null}
        </div>
      </header>
      {variant === "play" ? (
        <>
          <section
            className="layout__zone layout__zone--narration"
            aria-label="Narração"
          >
            {narration}
            {inputBar}
            {thoughtPanel}
          </section>
          <aside className="layout__zone layout__zone--scene" aria-label="Cena">
            {scene}
          </aside>
        </>
      ) : (
        <section className="layout__zone layout__zone--single">
          {narration}
        </section>
      )}
    </div>
  );
}
