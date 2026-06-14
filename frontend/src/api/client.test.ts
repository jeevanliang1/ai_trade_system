import { ApiError, api, apiRequest } from "./client";

beforeEach(() => {
  vi.restoreAllMocks();
});

test("apiRequest raises an ApiError with backend detail", async () => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: 400,
    json: async () => ({ detail: "path must stay under data" })
  }) as unknown as typeof fetch;

  await expect(apiRequest("/api/data/load")).rejects.toEqual(new ApiError(400, "path must stay under data"));
});

test("paperEvents fetches the encoded paper event log path", async () => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ events: [], orders: [], equity: [], summary: null })
  }) as unknown as typeof fetch;

  await api.paperEvents("logs/paper events.jsonl");

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/paper/events?path=logs%2Fpaper%20events.jsonl",
    expect.objectContaining({
      headers: expect.objectContaining({ "Content-Type": "application/json" })
    })
  );
});
