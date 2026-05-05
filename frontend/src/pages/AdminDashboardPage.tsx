import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";

import { getAdminConfig, getJobs, getPrinters, savePrinter, updateAdminConfig } from "../api/admin";
import { logout } from "../api/auth";
import { ErrorBanner } from "../components/ErrorBanner";
import type { AdminConfig, AdminPrinter } from "../types/api";

const blankPrinter: Omit<AdminPrinter, "id"> = {
  name: "",
  printer_sdp_id: "",
  location: "",
  enabled: true,
  public_selectable: true,
  is_default: false
};

export function AdminDashboardPage() {
  const queryClient = useQueryClient();
  const configQuery = useQuery({ queryKey: ["admin-config"], queryFn: getAdminConfig });
  const printersQuery = useQuery({ queryKey: ["printers"], queryFn: getPrinters });
  const jobsQuery = useQuery({ queryKey: ["jobs"], queryFn: getJobs, refetchInterval: 5000 });
  const [config, setConfig] = useState<AdminConfig>();
  const [printer, setPrinter] = useState<Omit<AdminPrinter, "id"> & { id?: number }>(blankPrinter);

  useEffect(() => {
    if (configQuery.data) setConfig(configQuery.data);
  }, [configQuery.data]);

  const configMutation = useMutation({
    mutationFn: updateAdminConfig,
    onSuccess: (next) => {
      setConfig(next);
      void queryClient.invalidateQueries({ queryKey: ["public-config"] });
    }
  });
  const printerMutation = useMutation({
    mutationFn: savePrinter,
    onSuccess: () => {
      setPrinter(blankPrinter);
      void queryClient.invalidateQueries({ queryKey: ["printers"] });
    }
  });

  if (!config) {
    return <main className="mx-auto min-h-screen max-w-5xl px-5 py-8 text-ink">Loading admin...</main>;
  }

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-5 py-8">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Event print</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Admin</h1>
        </div>
        <button className="rounded border border-ink/15 px-4 py-2 text-sm" onClick={() => void logout().then(() => location.reload())}>
          Sign out
        </button>
      </header>

      <section className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
        <form
          className="space-y-4 rounded border border-ink/10 bg-white p-4"
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            configMutation.mutate(config);
          }}
        >
          <h2 className="text-lg font-semibold text-ink">Event settings</h2>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input type="checkbox" checked={config.printing_enabled} onChange={(e) => setConfig({ ...config, printing_enabled: e.target.checked })} />
            Printing enabled
          </label>
          <Input label="Landing title" value={config.landing_title} onChange={(value) => setConfig({ ...config, landing_title: value })} />
          <label className="block text-sm font-medium text-ink">
            Landing body
            <textarea className="mt-2 min-h-24 w-full rounded border border-ink/15 px-3 py-2" value={config.landing_body} onChange={(e) => setConfig({ ...config, landing_body: e.target.value })} />
          </label>
          <label className="block text-sm font-medium text-ink">
            Printer mode
            <select className="mt-2 w-full rounded border border-ink/15 px-3 py-2" value={config.printer_mode} onChange={(e) => setConfig({ ...config, printer_mode: e.target.value as AdminConfig["printer_mode"] })}>
              <option value="single">Single printer</option>
              <option value="select">Visitor selects</option>
              <option value="all">Send to all enabled</option>
            </select>
          </label>
          <label className="block text-sm font-medium text-ink">
            Default printer
            <select className="mt-2 w-full rounded border border-ink/15 px-3 py-2" value={config.default_printer_id ?? ""} onChange={(e) => setConfig({ ...config, default_printer_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">None</option>
              {printersQuery.data?.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input type="checkbox" checked={config.allow_image_uploads} onChange={(e) => setConfig({ ...config, allow_image_uploads: e.target.checked })} />
            Allow images
          </label>
          <ErrorBanner message={configMutation.error?.message} />
          <button className="rounded bg-moss px-4 py-2 font-semibold text-white" disabled={configMutation.isPending}>Save settings</button>
        </form>

        <form
          className="space-y-4 rounded border border-ink/10 bg-white p-4"
          onSubmit={(event) => {
            event.preventDefault();
            printerMutation.mutate(printer);
          }}
        >
          <h2 className="text-lg font-semibold text-ink">{printer.id ? "Edit printer" : "Add printer"}</h2>
          <Input label="Name" value={printer.name} onChange={(value) => setPrinter({ ...printer, name: value })} />
          <Input label="SDP printer ID" value={printer.printer_sdp_id} onChange={(value) => setPrinter({ ...printer, printer_sdp_id: value })} />
          <Input label="Location" value={printer.location} onChange={(value) => setPrinter({ ...printer, location: value })} />
          <label className="flex items-center gap-2 text-sm text-ink"><input type="checkbox" checked={printer.enabled} onChange={(e) => setPrinter({ ...printer, enabled: e.target.checked })} /> Enabled</label>
          <label className="flex items-center gap-2 text-sm text-ink"><input type="checkbox" checked={printer.public_selectable} onChange={(e) => setPrinter({ ...printer, public_selectable: e.target.checked })} /> Public selectable</label>
          <label className="flex items-center gap-2 text-sm text-ink"><input type="checkbox" checked={printer.is_default} onChange={(e) => setPrinter({ ...printer, is_default: e.target.checked })} /> Default</label>
          <ErrorBanner message={printerMutation.error?.message} />
          <div className="flex gap-2">
            <button className="rounded bg-moss px-4 py-2 font-semibold text-white" disabled={printerMutation.isPending}>Save printer</button>
            {printer.id && <button className="rounded border border-ink/15 px-4 py-2" type="button" onClick={() => setPrinter(blankPrinter)}>Cancel</button>}
          </div>
        </form>
      </section>

      <section className="mt-6 rounded border border-ink/10 bg-white p-4">
        <h2 className="text-lg font-semibold text-ink">Printers</h2>
        <div className="mt-3 grid gap-2">
          {printersQuery.data?.map((item) => (
            <button key={item.id} className="rounded border border-ink/10 px-3 py-2 text-left text-sm" onClick={() => setPrinter(item)}>
              <span className="font-semibold text-ink">{item.name}</span>
              <span className="ml-2 text-ink/60">{item.printer_sdp_id}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="mt-6 rounded border border-ink/10 bg-white p-4">
        <h2 className="text-lg font-semibold text-ink">Recent jobs</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-ink/60"><tr><th className="py-2">ID</th><th>Printer</th><th>Status</th><th>Text</th><th>Created</th></tr></thead>
            <tbody>
              {jobsQuery.data?.map((job) => (
                <tr key={job.id} className="border-t border-ink/10">
                  <td className="py-2">{job.id}</td>
                  <td>{job.printer_id}</td>
                  <td>{job.status}</td>
                  <td className="max-w-sm truncate">{job.text || (job.image_base64 ? "Image" : "")}</td>
                  <td>{new Date(job.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

function Input({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-ink">
      {label}
      <input className="mt-2 w-full rounded border border-ink/15 px-3 py-2" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}
