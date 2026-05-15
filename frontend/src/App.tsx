import { Layout } from "./components/Layout";
import { useT } from "./i18n";
import { CreateCampaign } from "./screens/CreateCampaign";
import { Landing } from "./screens/Landing";
import { useSession } from "./state/session";
import { SessionProvider } from "./state/SessionContext";

export function App() {
  return (
    <SessionProvider>
      <Router />
    </SessionProvider>
  );
}

function Router() {
  const { screen } = useSession();

  if (screen === "landing") {
    return <Layout variant="single" narration={<Landing />} />;
  }
  if (screen === "create") {
    return <Layout variant="single" narration={<CreateCampaign />} />;
  }

  return <Placeholder screen={screen} />;
}

function Placeholder({ screen }: { screen: string }) {
  const t = useT();
  return (
    <Layout
      variant="single"
      narration={
        <div className="placeholder">
          <h1>{t("app.title")}</h1>
          <p>
            Tela <strong>{screen}</strong> ainda em construção.
          </p>
        </div>
      }
    />
  );
}
