export function ErrorState({ title = "Unable to load data", message }: { title?: string; message: string }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-900">
      <h2 className="font-semibold">{title}</h2>
      <p className="mt-2 text-sm">{message}</p>
    </div>
  );
}
