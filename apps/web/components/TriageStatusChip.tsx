const statusClasses: Record<string, string> = {
  RESEARCH_CANDIDATE: "bg-emerald-100 text-emerald-800",
  WATCHLIST: "bg-amber-100 text-amber-800",
  MANUAL_REVIEW: "bg-amber-50 text-amber-800",
  REJECTED: "bg-red-100 text-red-800",
  QUARANTINED: "bg-slate-100 text-slate-700",
  CANCELED_OR_INACTIVE: "bg-slate-200 text-slate-700",
};

export function TriageStatusChip({ status }: { status: string | null | undefined }) {
  const label = status || "UNKNOWN";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${statusClasses[label] ?? "bg-slate-100 text-slate-700"}`}>{label.replaceAll("_", " ")}</span>;
}
