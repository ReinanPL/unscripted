/**
 * Aviso vermelho destacado quando a entrada é recusada pelo validador
 * determinístico de robustez (ADR-026 / PRD §8).
 *
 * Diferente de "erro do mestre": aqui o turno NÃO foi consumido, a
 * mensagem do jogador foi preservada no input, e o convite é
 * reformular. Visual e tom refletem isso — é uma intervenção, não
 * uma falha de sistema.
 */

import { useT } from "../i18n";
import type { RobustnessCategory } from "../api/types";

interface RobustnessBannerProps {
  category: RobustnessCategory | string;
  reason: string;
  onDismiss?: () => void;
}

export function RobustnessBanner({
  category,
  reason,
  onDismiss,
}: RobustnessBannerProps) {
  const t = useT();
  const categoryHint =
    t(`robustness.categories.${category}`) ||
    t("robustness.categories.unknown");
  return (
    <div className="robustness-banner" role="alert">
      <div className="robustness-banner__body">
        <h3 className="robustness-banner__title">{t("robustness.title")}</h3>
        <p className="robustness-banner__category">{categoryHint}</p>
        {reason ? (
          <p className="robustness-banner__reason">{reason}</p>
        ) : null}
        <p className="robustness-banner__hint">{t("robustness.hint")}</p>
      </div>
      {onDismiss ? (
        <button
          type="button"
          className="robustness-banner__close"
          onClick={onDismiss}
          aria-label={t("common.close")}
          title={t("common.close")}
        >
          ×
        </button>
      ) : null}
    </div>
  );
}
