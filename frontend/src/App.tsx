import { useQuery } from "@tanstack/react-query";

import { me } from "./api/auth";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { AdminLoginPage } from "./pages/AdminLoginPage";
import { EventPage } from "./pages/EventPage";

export function App() {
  const isAdminRoute = window.location.pathname.startsWith("/admin");
  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: me,
    retry: false,
    enabled: isAdminRoute
  });

  if (!isAdminRoute) return <EventPage />;
  if (meQuery.isLoading) return <main className="mx-auto min-h-screen max-w-5xl px-5 py-8 text-ink">Loading...</main>;
  if (!meQuery.data) return <AdminLoginPage />;
  return <AdminDashboardPage />;
}
