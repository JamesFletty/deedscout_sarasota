import { stringifyFlag } from "@/lib/format";

export function RiskFlagList({ flags, limit = 3 }: { flags: unknown[]; limit?: number }) {
  if (!flags.length) return <span className="text-xs text-slate-400">No flags</span>;
  const visible = flags.slice(0, limit);
  return (
    <div className="flex flex-wrap gap-1.5">
      {visible.map((flag) => (
        <span key={stringifyFlag(flag)} className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">
          {stringifyFlag(flag)}
        </span>
      ))}
      {flags.length > visible.length ? <span className="text-xs text-slate-500">+{flags.length - visible.length}</span> : null}
    </div>
  );
}
