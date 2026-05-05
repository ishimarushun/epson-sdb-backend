import { apiFetch } from "./client";

export function login(username: string, password: string) {
  return apiFetch<{ username: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
}

export function logout() {
  return apiFetch<{ status: string }>("/api/auth/logout", { method: "POST" });
}

export function me() {
  return apiFetch<{ username: string }>("/api/auth/me");
}
