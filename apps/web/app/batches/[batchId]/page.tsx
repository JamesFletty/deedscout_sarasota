export const dynamic = "force-dynamic";

import Link from "next/link";
import { classifyAmbiguousAction, runTriageAction } from "@/app/actions";
import { BatchSummaryCard } from "@/components/BatchSummaryCard";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { ParcelTable } from "@/components/ParcelTable";
import { getBatch, getBatchRecords, getRecordEvidence } from "@/lib/api";

export default async function BatchDetailPage({ params }: { params: { batchId: string } }) {
  try {
    const [batch, records] = await Promise.all([getBatch(params.batchId), getBatchRecords(params.batchId)]);
    const evidenceEntries = await Promise.all(
      records.items.map(async (record) => [record.id, await getRecordEvidence(record.id)] as const),
    );
    const evidenceByRecordId = Object.fromEntries(evidenceEntries);

    return (
      <main className="min-h-screen px-6 py-8 lg:px-10">
        <section className="mx-auto max-w-7xl space-y-6">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
            <div>
              <Link className="text-sm font-medium text-blue-700 hover:text-blue-900" href="/dashboard">← Back to dashboard</Link>
              <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">Batch {batch.id.slice(0, 8)}</h1>
            </div>
            <div className="flex flex-wrap gap-2">
              <form action={runTriageAction}>
                <input name="batchId" type="hidden" value={batch.id} />
                <button className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" type="submit">Run Tier 1 Triage</button>
              </form>
              <form action={classifyAmbiguousAction}>
                <input name="batchId" type="hidden" value={batch.id} />
                <button className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-900 hover:bg-amber-100" type="submit">Classify Ambiguous Records</button>
              </form>
              <Link className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50" href={`/batches/${batch.id}`}>Refresh</Link>
            </div>
          </div>

          <BatchSummaryCard batch={batch} link={false} />

          {records.items.length ? (
            <ParcelTable records={records.items} evidenceByRecordId={evidenceByRecordId} />
          ) : (
            <EmptyState title="No records in this batch" description="Import snapshots and parse records before reviewing parcel-level triage." />
          )}
        </section>
      </main>
    );
  } catch (error) {
    return (
      <main className="min-h-screen px-6 py-8 lg:px-10">
        <section className="mx-auto max-w-4xl">
          <ErrorState message={error instanceof Error ? error.message : "The batch could not be loaded."} />
        </section>
      </main>
    );
  }
}
