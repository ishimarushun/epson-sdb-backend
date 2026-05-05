export function PrintSuccess({ jobs }: { jobs: number }) {
  return (
    <div className="rounded border border-moss/25 bg-mint px-4 py-3 text-sm text-ink">
      Queued for {jobs === 1 ? "1 printer" : `${jobs} printers`}.
    </div>
  );
}
