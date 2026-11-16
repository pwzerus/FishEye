import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeUser, nav, renderApp, router } from "@/test-utils";

vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return { ...actual, getMe: vi.fn(), getProviders: vi.fn(), listPins: vi.fn(), setGearStats: vi.fn() };
});
const session = await import("@/lib/api/session");
const { AccountView } = await import("./AccountView");

beforeEach(() => {
  vi.mocked(session.getProviders).mockResolvedValue({ password: true, google: false });
  vi.mocked(session.listPins).mockResolvedValue([]);
  router.replace.mockReset();
  nav.pathname = "/account";
  nav.search = new URLSearchParams();
});

describe("gear counts on the account page (backend ADR 0056)", () => {
  it("are on until the angler turns them off, and can be turned back on", async () => {
    // An account that never chose: the website counts its gear, as the
    // privacy policy says.
    const user = makeUser();
    vi.mocked(session.getMe).mockResolvedValue(user);
    vi.mocked(session.setGearStats).mockImplementation(async (on) => ({ ...user, gear_stats: on }));
    renderApp(<AccountView />);

    const box = await screen.findByRole("checkbox", { name: /Count my gear in FishEye's totals/ });
    expect(box).toBeChecked();
    // Just the switch: what is counted is in the privacy policy.
    expect(screen.queryByText(/never the spot/)).not.toBeInTheDocument();
    fireEvent.click(box);
    await waitFor(() => expect(session.setGearStats).toHaveBeenCalledWith(false));
    await waitFor(() => expect(box).not.toBeChecked());
    fireEvent.click(box);
    await waitFor(() => expect(session.setGearStats).toHaveBeenLastCalledWith(true));
    await waitFor(() => expect(box).toBeChecked());
  });

  it("shows an account that turned them off as off", async () => {
    vi.mocked(session.getMe).mockResolvedValue(makeUser({ gear_stats: false }));
    renderApp(<AccountView />);
    expect(await screen.findByRole("checkbox", { name: /Count my gear in FishEye's totals/ })).not.toBeChecked();
  });
});
