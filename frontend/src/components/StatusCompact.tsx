/**
 * Bloco compacto de status no rodapé da coluna direita.
 *
 * Mostra o mínimo que o jogador olha de relance entre turnos: HP em
 * barra fina, classe e nível, e onde está agora. A ficha completa
 * (atributos, perícias, equipamento) vive no modal, acionado pelo
 * botão "VER FICHA" — o resto do jogo é leitura.
 */

import type { CampaignStateResponse } from "../api/types";
import { useT } from "../i18n";

interface StatusCompactProps {
  state: CampaignStateResponse | null;
  loading: boolean;
  onOpenSheet: () => void;
}

export function StatusCompact({
  state,
  loading,
  onOpenSheet,
}: StatusCompactProps) {
  const t = useT();

  if (loading || !state) {
    return (
      <aside className="status-compact" aria-busy>
        <p className="status-compact__loading">{t("resume.loading")}</p>
      </aside>
    );
  }

  const c = state.character;
  const hpPercent = Math.max(
    0,
    Math.min(100, (c.hp_current / Math.max(1, c.hp_max)) * 100),
  );
  const className = t(`classes.${c.character_class}.name`);

  return (
    <aside className="status-compact" aria-label={t("state.title")}>
      <div className="status-compact__hp">
        <div className="status-compact__hp-row">
          <span className="status-compact__hp-label">{t("state.hpLabel")}</span>
          <span className="status-compact__hp-value">
            {c.hp_current}/{c.hp_max}
          </span>
        </div>
        <div
          className="status-compact__hp-bar"
          role="progressbar"
          aria-valuenow={c.hp_current}
          aria-valuemin={0}
          aria-valuemax={c.hp_max}
        >
          <div
            className="status-compact__hp-fill"
            style={{ width: `${hpPercent}%` }}
          />
        </div>
      </div>

      <p className="status-compact__class">
        {className} · {t("state.levelLabel")} {c.level}
      </p>

      <section className="status-compact__location">
        <h4 className="status-compact__section-title">
          {t("state.locationTitle")}
        </h4>
        <p className="status-compact__location-name">{state.location.name}</p>
        {state.location.description ? (
          <p className="status-compact__location-desc">
            {state.location.description}
          </p>
        ) : null}
      </section>

      <button
        type="button"
        className="status-compact__sheet-btn"
        onClick={onOpenSheet}
      >
        <span>{t("state.openSheet")}</span>
        <kbd className="status-compact__kbd">{t("state.openSheetHint")}</kbd>
      </button>
    </aside>
  );
}
