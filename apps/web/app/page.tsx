const metrics = [
  { label: "Batches", value: "0" },
  { label: "Records", value: "0" },
  { label: "Manual review", value: "0" },
];

export default function DashboardPage() {
  return (
    <main className="min-h-screen px-8 py-10">
      <section className="mx-auto max-w-5xl">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">DeedScout Sarasota</p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight">Tax deed triage dashboard</h1>
        <p className="mt-4 max-w-2xl text-slate-600">
          MVP shell for scraper-first evidence capture, normalized auction records, deterministic triage,
          and human review workflows.
        </p>
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {metrics.map((metric) => (
            <div key={metric.label} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm text-slate-500">{metric.label}</p>
              <p className="mt-2 text-3xl font-semibold">{metric.value}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
