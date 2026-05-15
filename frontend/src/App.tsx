import { useT } from "./i18n";

export function App() {
  const t = useT();
  return (
    <main>
      <h1>{t("app.title")}</h1>
      <p>{t("app.tagline")}</p>
    </main>
  );
}
