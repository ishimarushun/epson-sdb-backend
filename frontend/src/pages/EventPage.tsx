import { useQuery } from "@tanstack/react-query";

import { getPublicConfig } from "../api/publicConfig";
import { ErrorBanner } from "../components/ErrorBanner";
import { LandingPage } from "../components/LandingPage";
import { PrintForm } from "../components/PrintForm";

export function EventPage() {
  const config = useQuery({ queryKey: ["public-config"], queryFn: getPublicConfig });

  if (config.isLoading) {
    return <main className="mx-auto flex min-h-screen max-w-2xl items-center px-5 text-ink">Loading...</main>;
  }

  if (config.error || !config.data) {
    return (
      <main className="mx-auto flex min-h-screen max-w-2xl items-center px-5">
        <ErrorBanner message={config.error?.message ?? "Could not load event configuration."} />
      </main>
    );
  }

  if (!config.data.printing_enabled) {
    return <LandingPage title={config.data.landing_title} body={config.data.landing_body} />;
  }

  return <PrintForm config={config.data} />;
}
