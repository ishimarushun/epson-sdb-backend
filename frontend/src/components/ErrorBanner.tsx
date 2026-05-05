export function ErrorBanner({ message }: { message?: string }) {
  if (!message) return null;
  return <div className="rounded border border-coral/40 bg-coral/10 px-3 py-2 text-sm text-ink">{message}</div>;
}
