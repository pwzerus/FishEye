import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { makeUser, nav, renderApp, router } from "@/test-utils";

vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return {
    ...actual,
    getMe: vi.fn(),
    getProviders: vi.fn(),
    listPins: vi.fn(),
    reauth: vi.fn(),
    disconnectGoogle: vi.fn(),
    changePassword: vi.fn(),
    deleteAccount: vi.fn(),
  };
});
const session = await import("@/lib/api/session");
const actualSession = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
const { ApiError } = await import("@/lib/api/client");
const { AccountView } = await import("./AccountView");

const stale = () => new ApiError("For your security, confirm it's you first.", 403, "reauth_required");

beforeEach(() => {
  vi.mocked(session.getProviders).mockResolvedValue({ password: true, google: true });
  vi.mocked(session.listPins).mockResolvedValue([]);
  router.replace.mockReset();
  nav.pathname = "/account";
  nav.search = new URLSearchParams();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("re-authentication on the account page", () => {
  it("asks a password user to confirm, then finishes the change", async () => {
    const user = makeUser({ google_connected: true });
    vi.mocked(session.getMe).mockResolvedValue(user);
    vi.mocked(session.reauth).mockResolvedValue(user);
    vi.mocked(session.disconnectGoogle)
      .mockRejectedValueOnce(stale())
      .mockResolvedValueOnce({ ...user, google_connected: false });

    renderApp(<AccountView />);
    fireEvent.click(await screen.findByRole("button", { name: "Disconnect" }));

    expect(await screen.findByText(/confirm it's you with your password/i)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "tight-lines-42" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => expect(session.disconnectGoogle).toHaveBeenCalledTimes(2));
    expect(session.reauth).toHaveBeenCalledWith("tight-lines-42");
    expect(await screen.findByText("Google disconnected")).toBeTruthy();
    expect(await screen.findByText("Not connected")).toBeTruthy();
  });

  it("keeps the dialog open with the server's message on a wrong password", async () => {
    const user = makeUser({ google_connected: true });
    vi.mocked(session.getMe).mockResolvedValue(user);
    vi.mocked(session.reauth).mockRejectedValue(new ApiError("That password is incorrect.", 403));
    vi.mocked(session.disconnectGoogle).mockRejectedValue(stale());

    renderApp(<AccountView />);
    fireEvent.click(await screen.findByRole("button", { name: "Disconnect" }));
    fireEvent.change(await screen.findByLabelText("Password"), { target: { value: "nope" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    expect((await screen.findByRole("alert")).textContent).toBe("That password is incorrect.");
    expect(session.disconnectGoogle).toHaveBeenCalledTimes(1);
  });

  it("sends a Google-only user back through Google", async () => {
    vi.mocked(session.getMe).mockResolvedValue(makeUser({ has_password: false, google_connected: true }));
    vi.mocked(session.changePassword).mockRejectedValue(stale());

    renderApp(<AccountView />);
    fireEvent.click(await screen.findByRole("button", { name: "Set a password" }));
    const field = screen.getByLabelText("New password");
    fireEvent.change(field, { target: { value: "first-pass-77" } });
    fireEvent.click(within(field.closest("dialog")!).getByRole("button", { name: "Save" }));

    const link = await screen.findByRole("link", { name: /continue with google/i });
    expect(link.getAttribute("href")).toContain("/api/auth/google/start?next=%2Faccount");
    expect(screen.getByText(/to set a password, confirm it's you by signing in with google again/i)).toBeTruthy();
  });

  it("opens the confirmation when Google connect bounced for a stale session", async () => {
    nav.search = new URLSearchParams("error=reauth_required");
    vi.mocked(session.getMe).mockResolvedValue(makeUser());
    renderApp(<AccountView />);
    expect(await screen.findByText(/to connect google, confirm it's you with your password/i)).toBeTruthy();
  });
});

describe("the API client", () => {
  it("recognises the server's re-auth signal and nothing else", async () => {
    const respond = (status: number, headers: Record<string, string> = {}) =>
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "nope" }), { status, headers }));

    vi.stubGlobal("fetch", respond(403, { "X-Reauth-Required": "1" }));
    const err = await actualSession.disconnectGoogle().catch((e: unknown) => e);
    expect(actualSession.isReauthRequired(err)).toBe(true);

    vi.stubGlobal("fetch", respond(403));
    const plain = await actualSession.disconnectGoogle().catch((e: unknown) => e);
    expect(actualSession.isReauthRequired(plain)).toBe(false);
    expect((plain as Error).message).toBe("nope");
  });
});
