import { useT } from "../i18n";
import { useSession } from "../state/session";

export function Landing() {
  const t = useT();
  const { goTo } = useSession();

  return (
    <div className="landing">
      <div className="landing__frame">
        <h1 className="landing__title">{t("landing.welcome")}</h1>
        <p className="landing__intro">{t("landing.intro")}</p>

        <div className="landing__actions">
          <button
            type="button"
            className="landing__action landing__action--primary"
            onClick={() => goTo("create")}
          >
            {t("landing.newCampaign")}
          </button>
          <button
            type="button"
            className="landing__action"
            onClick={() => goTo("resume")}
          >
            {t("landing.resumeCampaign")}
          </button>
        </div>
      </div>
    </div>
  );
}
