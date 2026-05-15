import { useT } from "./i18n";
import { Layout } from "./components/Layout";

export function App() {
  const t = useT();
  return (
    <Layout
      variant="single"
      narration={
        <div className="placeholder">
          <h1>{t("app.title")}</h1>
          <p>{t("app.tagline")}</p>
        </div>
      }
    />
  );
}
