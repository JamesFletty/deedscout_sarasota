import Link from "next/link";
import type { BatchSummary } from "@/lib/api";
import { formatCents, formatDate } from "@/lib/format";
import { JobStatusIndicator } from "./JobStatusIndicator";

const countLabels: Array<[keyof BatchSummary, string]> = [
  ["records_found", "Found"],
  ["records_valid", "Valid"],
  ["records_quarantined", "Quarantined"],
  ["records_rejected", "Rejected"],
  ["records_watchlist", "Watchlist"],
  ["records_research_candidates", "Research"],
  ["records_manual_review", "Manual"],
  ["llm_calls_used", "LLM calls"],
];

export function BatchSummaryCard({ batch, link = true }: { batch: BatchSummary; link?: boolean }) {
  const content = (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-200 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{batch.county}</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">Batch {batch.id.slice(0, 8)}</h2>
          <p className="mt-1 break-all text-sm text-slate-500">{batch.source}</p>
        </div>
        <JobStatusIndicator status={batch.status} />
      </div>
      <dl className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        {countLabels.map(([key, label]) => (
          <div key={key} className="rounded-xl bg-slate-50 p-3">
            <dt className="text-xs text-slate-500">{label}</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-900">{String(batch[key] ?? 0)}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm text-slate-500">
        <span>Last run: {formatDate(batch.completed_at ?? batch.started_at)}</span>
        <span>Estimated cost: {formatCents(Math.round(Number(batch.estimated_cost_usd) * 100))}</span>
      </div>
    </article>
  );
  return link ? <Link href={`/batches/${batch.id}`}>{content}</Link> : content;
}
