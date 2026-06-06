import { importBatchAction } from "@/app/actions";

export function ImportBatchButton() {
  return (
    <form action={importBatchAction} className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row">
      <input
        name="sourceUrl"
        type="url"
        placeholder="Optional Sarasota source or fixture URL"
        className="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-blue-500"
      />
      <button className="rounded-xl bg-blue-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-800" type="submit">
        Import batch
      </button>
    </form>
  );
}
