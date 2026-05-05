import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

import { login } from "../api/auth";
import { ErrorBanner } from "../components/ErrorBanner";

export function AdminLoginPage() {
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const mutation = useMutation({
    mutationFn: () => login(username, password),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["me"] })
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-5">
      <h1 className="text-3xl font-semibold text-ink">Admin login</h1>
      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-ink">
          Username
          <input className="mt-2 w-full rounded border border-ink/15 px-3 py-2" value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="block text-sm font-medium text-ink">
          Password
          <input className="mt-2 w-full rounded border border-ink/15 px-3 py-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <ErrorBanner message={mutation.error?.message} />
        <button className="w-full rounded bg-moss px-4 py-3 font-semibold text-white" disabled={mutation.isPending}>
          {mutation.isPending ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </main>
  );
}
