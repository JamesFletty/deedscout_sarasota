import type { AgentRun } from "@/lib/api";
import { formatDate } from "@/lib/format";

export function AgentDecisionTimeline({ agentRuns }: { agentRuns: AgentRun[] }) {
  if (!agentRuns.length) return <p className="text-sm text-slate-500">No agent runs recorded.</p>;
  return (
    <ol className="space-y-3">
      {agentRuns.map((run) => (
        <li key={run.id} className="rounded-xl border border-slate-200 p-3">
          <div className="flex items-center justify-between gap-3">
            <p className="font-medium text-slate-900">{run.agent_name}</p>
            <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{run.status}</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">{formatDate(run.completed_at ?? run.started_at)} · {run.model_name ?? "deterministic"}</p>
          {run.output_json ? <pre className="mt-2 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(run.output_json, null, 2)}</pre> : null}
        </li>
      ))}
    </ol>
  );
}
