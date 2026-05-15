import type { ReactNode } from "react";
import { useT } from "../i18n";

interface LayoutProps {
  state?: ReactNode;
  narration: ReactNode;
  inputBar?: ReactNode;
  thoughtPanel?: ReactNode;
  scene?: ReactNode;
  variant?: "play" | "single";
}

export function Layout({
  state,
  narration,
  inputBar,
  thoughtPanel,
  scene,
  variant = "play",
}: LayoutProps) {
  const t = useT();
  return (
    <div className={`layout layout--${variant}`}>
      <header className="layout__header">
        <h1 className="layout__title">{t("app.title")}</h1>
      </header>
      {variant === "play" ? (
        <>
          <aside className="layout__zone layout__zone--state" aria-label="Ficha">
            {state}
          </aside>
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
