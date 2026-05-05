import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { submitPrint } from "../api/print";
import type { PublicConfig } from "../types/api";
import { ErrorBanner } from "./ErrorBanner";
import { ImagePicker } from "./ImagePicker";
import { PrinterSelector } from "./PrinterSelector";
import { PrintSuccess } from "./PrintSuccess";

type FormValues = {
  text: string;
};

export function PrintForm({ config }: { config: PublicConfig }) {
  const [imageBase64, setImageBase64] = useState<string>();
  const [selectedPrinterIds, setSelectedPrinterIds] = useState<number[]>([]);
  const [queuedJobs, setQueuedJobs] = useState<number>();
  const schema = useMemo(
    () =>
      z.object({
        text: z.string().max(config.max_text_length)
      }),
    [config.max_text_length]
  );
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { text: "" }
  });
  const mutation = useMutation({
    mutationFn: submitPrint,
    onSuccess: (result) => {
      setQueuedJobs(result.created_jobs);
      form.reset();
      setImageBase64(undefined);
      setSelectedPrinterIds([]);
    }
  });

  const textValue = form.watch("text");
  const remaining = config.max_text_length - textValue.length;

  return (
    <main className="mx-auto min-h-screen max-w-2xl px-5 py-8">
      <div className="mb-8">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Event print</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Send something to print</h1>
      </div>

      <form
        className="space-y-5"
        onSubmit={form.handleSubmit((values) => {
          setQueuedJobs(undefined);
          mutation.mutate({
            text: values.text.trim() || undefined,
            image_base64: imageBase64,
            printer_ids: config.printer_mode === "select" ? selectedPrinterIds : undefined,
            copies: 1
          });
        })}
      >
        <div>
          <label className="block text-sm font-medium text-ink" htmlFor="text">
            Text
          </label>
          <textarea
            id="text"
            className="mt-2 min-h-36 w-full resize-y rounded border border-ink/15 bg-white px-3 py-2 text-base text-ink outline-none focus:border-moss"
            maxLength={config.max_text_length}
            {...form.register("text")}
          />
          <p className="mt-1 text-right text-xs text-ink/55">{remaining} characters left</p>
        </div>

        {config.allow_image_uploads && <ImagePicker maxBytes={config.max_image_bytes} onChange={setImageBase64} />}

        {config.printer_mode === "select" && (
          <PrinterSelector printers={config.printers} selectedIds={selectedPrinterIds} onChange={setSelectedPrinterIds} />
        )}

        <ErrorBanner message={mutation.error?.message} />
        {queuedJobs && <PrintSuccess jobs={queuedJobs} />}

        <button
          className="w-full rounded bg-coral px-4 py-3 font-semibold text-white shadow-sm transition hover:bg-coral/90 disabled:cursor-not-allowed disabled:bg-ink/30"
          type="submit"
          disabled={mutation.isPending || (!textValue.trim() && !imageBase64)}
        >
          {mutation.isPending ? "Sending..." : "Send to print"}
        </button>
      </form>
    </main>
  );
}
