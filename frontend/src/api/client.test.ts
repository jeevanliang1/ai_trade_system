import { ApiError, apiRequest } from "./client";

test("apiRequest raises an ApiError with backend detail", async () => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: 400,
    json: async () => ({ detail: "path must stay under data" })
  }) as unknown as typeof fetch;

  await expect(apiRequest("/api/data/load")).rejects.toEqual(new ApiError(400, "path must stay under data"));
});
