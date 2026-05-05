import { apiFetch } from "./client";
import type { AdminConfig, AdminPrinter, PrintJob } from "../types/api";

export function getAdminConfig() {
  return apiFetch<AdminConfig>("/api/admin/config");
}

export function updateAdminConfig(payload: AdminConfig) {
  return apiFetch<AdminConfig>("/api/admin/config", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getPrinters() {
  return apiFetch<AdminPrinter[]>("/api/admin/printers");
}

export function savePrinter(printer: Omit<AdminPrinter, "id"> & { id?: number }) {
  const isUpdate = typeof printer.id === "number";
  return apiFetch<AdminPrinter>(isUpdate ? `/api/admin/printers/${printer.id}` : "/api/admin/printers", {
    method: isUpdate ? "PUT" : "POST",
    body: JSON.stringify(printer)
  });
}

export function getJobs() {
  return apiFetch<PrintJob[]>("/api/admin/jobs");
}
