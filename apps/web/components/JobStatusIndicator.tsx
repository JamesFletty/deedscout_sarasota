export function JobStatusIndicator({ status }: { status: string }) {
  const color = status === "completed" ? "bg-emerald-500" : status === "failed" ? "bg-red-500" : "bg-amber-500";
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-sm font-medium text-slate-700 ring-1 ring-slate-200">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      {status}
    </span>
  );
}
