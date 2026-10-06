import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, postAsk } from "./client";

function stubFetch(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } })),
  );
}

describe("apiFetch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("turns a 429 into an ApiError carrying the server's message", async () => {
    stubFetch(429, { detail: "That's a lot of requests in a short time. Please wait a moment and try again." });
    const err = await postAsk({ question: "what bait for crappie" }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({
      status: 429,
      code: "rate_limited",
      message: "That's a lot of requests in a short time. Please wait a moment and try again.",
    });
  });

  it("falls back to a generic message when a 429 has no usable body", async () => {
    stubFetch(429, null);
    const err = await postAsk({ question: "what bait for crappie" }).catch((e: unknown) => e);
    expect(err).toMatchObject({ status: 429, code: "rate_limited", message: expect.stringMatching(/wait a moment/) });
  });

  it("keeps other errors as they were", async () => {
    stubFetch(500, { detail: "boom" });
    const err = await postAsk({ question: "what bait for crappie" }).catch((e: unknown) => e);
    expect(err).toMatchObject({ status: 500, code: undefined });
  });
});
