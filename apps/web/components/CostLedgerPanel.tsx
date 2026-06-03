import type { CostEvent } from "@/lib/api";

export function CostLedgerPanel({ costEvents }: { costEvents: CostEvent[] }) {
  if (!costEvents.length) return <p className="text-sm text-slate-500">No cost events recorded.</p>;
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-2">Service</th>
            <th className="px-3 py-2">Event</th>
            <th className="px-3 py-2">Units</th>
            <th className="px-3 py-2">Cost</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {costEvents.map((event) => (
            <tr key={event.id}>
              <td className="px-3 py-2">{event.service}</td>
              <td className="px-3 py-2">{event.event_type}</td>
              <td className="px-3 py-2">{event.unit_count}</td>
              <td className="px-3 py-2">${Number(event.estimated_cost_usd).toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
