import { importFixtureBatchAction } from "@/app/actions";

export function ImportFixtureBatchButton() {
  return (
    <form action={importFixtureBatchAction}>
      <button
        className="w-full rounded-xl bg-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-800"
        type="submit"
      >
        Import Sarasota fixture batch
      </button>
      <p className="mt-2 text-xs text-slate-500">
        Loads committed HTML fixtures, stores evidence snapshots, parses records, and runs Tier 1 triage.
      </p>
    </form>
  );
}
