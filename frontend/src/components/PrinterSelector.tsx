import type { PublicPrinter } from "../types/api";

export function PrinterSelector({
  printers,
  selectedIds,
  onChange
}: {
  printers: PublicPrinter[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
}) {
  return (
    <fieldset>
      <legend className="text-sm font-medium text-ink">Printer</legend>
      <div className="mt-2 grid gap-2">
        {printers.map((printer) => (
          <label key={printer.id} className="flex cursor-pointer items-center gap-3 rounded border border-ink/15 bg-white p-3">
            <input
              type="checkbox"
              checked={selectedIds.includes(printer.id)}
              onChange={(event) => {
                onChange(
                  event.target.checked
                    ? [...selectedIds, printer.id]
                    : selectedIds.filter((id) => id !== printer.id)
                );
              }}
            />
            <span>
              <span className="block text-sm font-semibold text-ink">{printer.name}</span>
              {printer.location && <span className="block text-xs text-ink/60">{printer.location}</span>}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
