"use client";

import { useMemo, useState } from "react";
import type { AuctionRecord, RecordEvidence } from "@/lib/api";
import { formatCents, formatDate, formatRatio } from "@/lib/format";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { EmptyState } from "./EmptyState";
import { ParcelGradeBadge } from "./ParcelGradeBadge";
import { RiskFlagList } from "./RiskFlagList";
import { TriageStatusChip } from "./TriageStatusChip";

export function ParcelTable({ records, evidenceByRecordId }: { records: AuctionRecord[]; evidenceByRecordId: Record<string, RecordEvidence | undefined> }) {
  const [statusFilter, setStatusFilter] = useState("");
  const [gradeFilter, setGradeFilter] = useState("");
  const [auctionStatusFilter, setAuctionStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [openRecordId, setOpenRecordId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return records.filter((record) => {
      const triage = record.latest_triage;
      if (statusFilter && triage?.tier_1_status !== statusFilter) return false;
      if (gradeFilter && triage?.grade !== gradeFilter) return false;
      if (auctionStatusFilter && record.auction_status !== auctionStatusFilter) return false;
      if (!normalizedSearch) return true;
      return [record.parcel_id_normalized, record.parcel_id_raw, record.case_number]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(normalizedSearch));
    });
  }, [auctionStatusFilter, gradeFilter, records, search, statusFilter]);

  const openRecord = records.find((record) => record.id === openRecordId);
  const tierStatuses = Array.from(
    new Set(records.map((record) => record.latest_triage?.tier_1_status).filter(isString)),
  );
  const grades = Array.from(new Set(records.map((record) => record.latest_triage?.grade).filter(isString)));
  const auctionStatuses = Array.from(new Set(records.map((record) => record.auction_status).filter(isString)));

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 border-b border-slate-200 pb-4 lg:flex-row lg:items-center">
        <input
          className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500"
          placeholder="Search parcel or case number"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <FilterSelect label="Tier status" value={statusFilter} onChange={setStatusFilter} options={tierStatuses} />
        <FilterSelect label="Grade" value={gradeFilter} onChange={setGradeFilter} options={grades} />
        <FilterSelect label="Auction status" value={auctionStatusFilter} onChange={setAuctionStatusFilter} options={auctionStatuses} />
      </div>

      {filtered.length ? (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-3">Parcel</th>
                <th className="px-3 py-3">Case</th>
                <th className="px-3 py-3">Auction</th>
                <th className="px-3 py-3">Opening bid</th>
                <th className="px-3 py-3">Assessment</th>
                <th className="px-3 py-3">Spread</th>
                <th className="px-3 py-3">Ratio</th>
                <th className="px-3 py-3">Grade</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Risk flags</th>
                <th className="px-3 py-3">Evidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {filtered.map((record) => (
                <tr key={record.id} className="align-top hover:bg-slate-50">
                  <td className="px-3 py-3 font-medium text-slate-900">{record.parcel_id_normalized ?? record.parcel_id_raw ?? "—"}</td>
                  <td className="px-3 py-3 text-slate-600">{record.case_number ?? "—"}</td>
                  <td className="px-3 py-3 text-slate-600">{formatDate(record.auction_date)}<br /><span className="text-xs">{record.auction_status ?? "unknown"}</span></td>
                  <td className="px-3 py-3 text-slate-600">{formatCents(record.opening_bid_cents)}</td>
                  <td className="px-3 py-3 text-slate-600">{formatCents(record.appraiser_assessment_cents)}</td>
                  <td className="px-3 py-3 text-slate-600">{formatCents(record.latest_triage?.estimated_spread_cents ?? null)}</td>
                  <td className="px-3 py-3 text-slate-600">{formatRatio(record.latest_triage?.opening_bid_ratio ?? null)}</td>
                  <td className="px-3 py-3"><ParcelGradeBadge grade={record.latest_triage?.grade} /></td>
                  <td className="px-3 py-3"><TriageStatusChip status={record.latest_triage?.tier_1_status} /></td>
                  <td className="px-3 py-3"><RiskFlagList flags={record.latest_triage?.risk_flags ?? []} /></td>
                  <td className="px-3 py-3">
                    <button className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-white" onClick={() => setOpenRecordId(record.id)} type="button">
                      View evidence
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="pt-4">
          <EmptyState title="No parcels match these filters" description="Clear filters or refresh the batch after importing and triaging records." />
        </div>
      )}

      {openRecord ? (
        <EvidenceDrawer
          record={openRecord}
          evidence={evidenceByRecordId[openRecord.id]}
          open={Boolean(openRecord)}
          onClose={() => setOpenRecordId(null)}
        />
      ) : null}
    </section>
  );
}

function FilterSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[] }) {
  return (
    <label className="text-xs font-medium uppercase tracking-wide text-slate-500">
      {label}
      <select className="mt-1 block min-w-36 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm normal-case text-slate-700" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>{option.replaceAll("_", " ")}</option>
        ))}
      </select>
    </label>
  );
}

function isString(value: string | null | undefined): value is string {
  return Boolean(value);
}
