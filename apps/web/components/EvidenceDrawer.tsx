"use client";

import type { AuctionRecord, RecordEvidence } from "@/lib/api";
import { formatCents, formatDate } from "@/lib/format";
import { AgentDecisionTimeline } from "./AgentDecisionTimeline";
import { CostLedgerPanel } from "./CostLedgerPanel";
import { RiskFlagList } from "./RiskFlagList";

export function EvidenceDrawer({ record, evidence, open, onClose }: { record: AuctionRecord; evidence?: RecordEvidence; open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/30" role="dialog" aria-modal="true">
      <button aria-label="Close evidence drawer" className="absolute inset-0 cursor-default" onClick={onClose} type="button" />
      <aside className="relative h-full w-full max-w-3xl overflow-y-auto bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Evidence drawer</p>
            <h2 className="mt-1 text-2xl font-semibold text-slate-950">{record.parcel_id_normalized ?? "Unknown parcel"}</h2>
            <p className="mt-1 text-sm text-slate-500">Case {record.case_number ?? "—"}</p>
          </div>
          <button className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium hover:bg-slate-50" onClick={onClose} type="button">Close</button>
        </div>

        <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Grades indicate research priority only. This is not legal, investment, title, appraisal, zoning, environmental, tax, or bidding advice.
        </p>

        <section className="mt-6 grid gap-3 sm:grid-cols-2">
          <Info label="Auction status" value={record.auction_status ?? "—"} />
          <Info label="Auction date" value={formatDate(record.auction_date)} />
          <Info label="Opening bid" value={formatCents(record.opening_bid_cents)} />
          <Info label="Appraiser assessment" value={formatCents(record.appraiser_assessment_cents)} />
          <Info label="Parse confidence" value={String(record.parse_confidence)} />
          <Info label="Detail URL" value={record.detail_url ?? "—"} />
        </section>

        <Section title="Parser warnings and missing fields">
          <RiskFlagList flags={[...record.missing_fields, ...record.parse_warnings]} limit={10} />
        </Section>

        <Section title="Source snapshots">
          {evidence?.snapshots.length ? (
            <div className="space-y-3">
              {evidence.snapshots.map((snapshot) => (
                <div key={snapshot.id} className="rounded-xl border border-slate-200 p-3 text-sm">
                  <p className="break-all font-medium text-slate-900">{snapshot.source_url}</p>
                  <p className="mt-1 text-slate-500">Scraped {formatDate(snapshot.scraped_at)} · parser {snapshot.parser_version}</p>
                  <p className="mt-1 break-all text-xs text-slate-500">Content hash {snapshot.content_hash}</p>
                  {snapshot.html_path ? <p className="mt-1 break-all text-xs text-slate-500">HTML {snapshot.html_path}</p> : null}
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-slate-500">No source snapshots recorded.</p>}
        </Section>

        <Section title="Rule evidence">
          {evidence?.triage_evidence.length ? (
            <div className="space-y-2">
              {evidence.triage_evidence.map((item, index) => (
                <div key={`${String(item.rule_name)}-${index}`} className="rounded-xl bg-slate-50 p-3 text-sm">
                  <p className="font-medium text-slate-900">{String(item.rule_name ?? "Rule")}</p>
                  <p className="text-slate-600">{String(item.reason ?? "No reason supplied")}</p>
                  <p className="mt-1 text-xs text-slate-500">{String(item.field_inspected ?? "field")} · {String(item.decision_impact ?? "impact")}</p>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-slate-500">No triage evidence recorded.</p>}
        </Section>

        <Section title="LLM classifier output and agent timeline">
          <AgentDecisionTimeline agentRuns={evidence?.agent_runs ?? []} />
        </Section>

        <Section title="Cost ledger">
          <CostLedgerPanel costEvents={evidence?.cost_events ?? []} />
        </Section>
      </aside>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 break-all text-sm font-medium text-slate-900">{value}</p>
    </div>
  );
}
