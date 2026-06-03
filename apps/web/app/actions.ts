"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { classifyAmbiguous, importSarasotaBatch, runTier1Triage } from "@/lib/api";

export async function importBatchAction(formData: FormData) {
  const sourceUrl = String(formData.get("sourceUrl") ?? "").trim();
  const result = await importSarasotaBatch(sourceUrl || undefined);
  revalidatePath("/dashboard");
  redirect(`/batches/${result.batch_id}`);
}

export async function runTriageAction(formData: FormData) {
  const batchId = String(formData.get("batchId"));
  await runTier1Triage(batchId);
  revalidatePath(`/batches/${batchId}`);
}

export async function classifyAmbiguousAction(formData: FormData) {
  const batchId = String(formData.get("batchId"));
  await classifyAmbiguous(batchId);
  revalidatePath(`/batches/${batchId}`);
}
