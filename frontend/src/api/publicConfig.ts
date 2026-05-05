import { apiFetch } from "./client";
import type { PublicConfig } from "../types/api";

export function getPublicConfig() {
  return apiFetch<PublicConfig>("/api/public/config");
}
