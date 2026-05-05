import { apiFetch } from "./client";

export type PublicPrintPayload = {
  text?: string;
  image_base64?: string;
  printer_ids?: number[];
  copies: 1;
};

export function submitPrint(payload: PublicPrintPayload) {
  return apiFetch<{ created_jobs: number; status: "queued" }>("/api/public/print", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
