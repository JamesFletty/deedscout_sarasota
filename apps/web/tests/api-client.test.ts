import { afterEach, describe, expect, it, vi } from "vitest";
import { importSarasotaBatch } from "@/lib/api";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requests parsed Sarasota imports for supplied sources", async () => {
    const fetchMock = vi.fn(async (_input: string | URL, _init?: RequestInit) => {
      return new Response(
        JSON.stringify({
          batch_id: "12345678-1234-1234-1234-123456789abc",
          job_id: "87654321-4321-4321-4321-cba987654321",
          job_status: "completed",
        }),
        {
          status: 201,
          headers: { "content-type": "application/json" },
        },
      );
    });
    vi.stubGlobal("fetch", fetchMock);

    await importSarasotaBatch("file:///workspace/fixtures/sarasota/html/sample_auction_detail.html");

    expect(fetchMock).toHaveBeenCalledOnce();
    const init = fetchMock.mock.calls[0]?.[1];
    expect(JSON.parse(String(init?.body))).toEqual({
      source_url: "file:///workspace/fixtures/sarasota/html/sample_auction_detail.html",
      snapshot_only: false,
    });
  });
});
