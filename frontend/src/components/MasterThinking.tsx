/**
 * Feedback de processamento durante o turno (PRD §6.8).
 *
 * Aparece entre o último turno renderizado e o input do jogador. Três
 * pontos serifados pulsando em sequência — não é spinner, não é
 * "loading" genérico. É a leitura do mestre olhando o jogador e
 * pensando.
 */

import { useT } from "../i18n";

export function MasterThinking() {
  const t = useT();
  return (
    <div className="master-thinking" role="status" aria-live="polite">
      <span className="master-thinking__text">{t("play.masterThinking")}</span>
      <span className="master-thinking__dots" aria-hidden="true">
        <span className="master-thinking__dot" />
        <span className="master-thinking__dot" />
        <span className="master-thinking__dot" />
      </span>
    </div>
  );
}
