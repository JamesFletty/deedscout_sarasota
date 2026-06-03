export function formatCents(cents: number | null): string {
  if (cents === null) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(
    cents / 100,
  );
}

export function formatRatio(value: string | null): string {
  if (value === null) return "—";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(value));
}

export function stringifyFlag(flag: unknown): string {
  if (typeof flag === "string") return flag;
  return JSON.stringify(flag);
}
