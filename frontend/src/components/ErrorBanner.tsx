/**
 * Banner de erro do mestre / backend (ADR-020).
 *
 * Tom: mais brando que o RobustnessBanner — aqui o jogador não fez nada
 * de errado. Variante `fatal=true` é usada quando a campanha não existe
 * mais (404 vindo do SSE): expõe botão "Voltar ao início" porque
 * continuar tentando ali não tem efeito.
 *
 * Em qualquer variante, a mensagem do jogador é preservada no input
 * pela tela de jogo — esta camada só comunica o ocorrido.
 */

import { useT } from "../i18n";

interface ErrorBannerProps {
  message: string;
  fatal?: boolean;
  onDismiss?: () => void;
  onRecover?: () => void;
}

export function ErrorBanner({
  message,
  fatal = false,
  onDismiss,
  onRecover,
}: ErrorBannerProps) {
  const t = useT();
  return (
    <div
      className={
        "error-banner" + (fatal ? " error-banner--fatal" : "")
      }
      role="alert"
    >
      <div className="error-banner__body">
        <h3 className="error-banner__title">
          {fatal ? t("errors.fatalTitle") : t("errors.title")}
        </h3>
        <p className="error-banner__message">{message}</p>
        {fatal && onRecover ? (
          <button
            type="button"
            className="error-banner__recover"
            onClick={onRecover}
          >
            {t("errors.recoverToLanding")}
          </button>
        ) : null}
      </div>
      {!fatal && onDismiss ? (
        <button
          type="button"
          className="error-banner__close"
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
