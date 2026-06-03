const gradeClasses: Record<string, string> = {
  A: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  B: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  C: "bg-amber-100 text-amber-800 ring-amber-200",
  D: "bg-orange-100 text-orange-800 ring-orange-200",
  F: "bg-red-100 text-red-800 ring-red-200",
  U: "bg-slate-100 text-slate-700 ring-slate-200",
};

export function ParcelGradeBadge({ grade }: { grade: string | null | undefined }) {
  const label = grade || "U";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${gradeClasses[label] ?? gradeClasses.U}`}>{label}</span>;
}
