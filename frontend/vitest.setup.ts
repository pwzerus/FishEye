import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import "@testing-library/jest-dom/vitest";

// Tests never reach the network. A request a test didn't mock fails at once,
// as it would with no backend running, instead of a moment later: a failure
// that came back after the test environment had closed made React throw
// "window is not defined" in CI. It also keeps a backend running on this
// machine out of the results. vi.stubGlobal("fetch", ...) still replaces it.
globalThis.fetch = (() => Promise.reject(new TypeError("fetch failed: tests don't reach the network"))) as typeof fetch;

afterEach(() => {
  cleanup();
});
