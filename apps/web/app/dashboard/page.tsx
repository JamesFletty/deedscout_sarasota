export const dynamic = "force-dynamic";

import { BatchSummaryCard } from "@/components/BatchSummaryCard";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { ImportBatchButton } from "@/components/ImportBatchButton";
import { listBatches } from "@/lib/api";

export default async function DashboardPage() {
  try {
    const batches = await listBatches();
    const latest = batches.items[0];
    return (
      <main className="min-h-screen px-6 py-8 lg:px-10">
        <section className="mx-auto max-w-7xl space-y-8">
          <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">DeedScout Sarasota</p>
              <h1 className="mt-3 text-4xl font-bold tracking-tight text-slate-950">Batch dashboard</h1>
              <p className="mt-3 max-w-3xl text-slate-600">
                Scraper-first due-diligence triage for Sarasota tax deed research. Outputs organize public-record research and require qualified human review.
              </p>
            </div>
            <div className="w-full max-w-xl">
              <ImportBatchButton />
            </div>
          </div>

          {latest ? (
            <div className="grid gap-4 md:grid-cols-4">
              <Metric label="Records found" value={latest.records_found} />
              <Metric label="Research candidates" value={latest.records_research_candidates} tone="green" />
              <Metric label="Watchlist / manual" value={latest.records_watchlist + latest.records_manual_review} tone="amber" />
              <Metric label="LLM cost" value={`$${Number(latest.estimated_cost_usd).toFixed(4)}`} />
            </div>
          ) : null}

          <div>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-950">Recent batches</h2>
              <p className="text-sm text-slate-500">{batches.total} total</p>
            </div>
            {batches.items.length ? (
              <div className="grid gap-4">
                {batches.items.map((batch) => <BatchSummaryCard key={batch.id} batch={batch} />)}
              </div>
            ) : (
              <EmptyState title="No batches yet" description="Create a Sarasota import batch to begin snapshot capture and triage review." />
            )}
          </div>
        </section>
      </main>
    );
  } catch (error) {
    return (
      <main className="min-h-screen px-6 py-8 lg:px-10">
        <section className="mx-auto max-w-4xl">
          <ErrorState message={error instanceof Error ? error.message : "The API request failed."} />
        </section>
      </main>
    );
  }
}

function Metric({ label, value, tone = "slate" }: { label: string; value: number | string; tone?: "slate" | "green" | "amber" }) {
  const toneClass = tone === "green" ? "text-emerald-700" : tone === "amber" ? "text-amber-700" : "text-slate-950";
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-2 text-3xl font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}
