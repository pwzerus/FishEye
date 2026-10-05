import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeUser, nav, renderApp, router } from "@/test-utils";

// vi.mock is hoisted above imports, so the factory imports what it needs itself.
vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return {
    ...actual,
    getMe: vi.fn(),
    adminStats: vi.fn(),
    adminAudit: vi.fn(),
    adminReports: vi.fn(),
    adminResolve: vi.fn(),
    adminUsers: vi.fn(),
    adminUpdateUser: vi.fn(),
  };
});
const session = await import("@/lib/api/session");
const { AdminConsole } = await import("./AdminConsole");

const STATS = {
  users: 3,
  users_new_7d: 2,
  users_active_7d: 2,
  admins: 1,
  suspended: 0,
  pins: 5,
  pins_new_7d: 5,
  pins_public: 4,
  pins_private: 1,
  pins_hidden: 1,
  pins_removed: 0,
  photos: 6,
  open_reports: 3,
  pins_awaiting_review: 1,
};

beforeEach(() => {
  nav.pathname = "/admin";
  nav.search = new URLSearchParams();
  router.replace.mockReset();
  vi.mocked(session.adminStats).mockResolvedValue(STATS);
  vi.mocked(session.adminAudit).mockResolvedValue({ total: 0, page: 1, page_size: 25, items: [] });
});

describe("AdminConsole access", () => {
  it("asks signed-out visitors to sign in", async () => {
    vi.mocked(session.getMe).mockResolvedValue(null);
    renderApp(<AdminConsole />);
    expect((await screen.findByText("Sign in")).closest("a")).toHaveAttribute("href", "/login?next=/admin");
  });

  it("turns away non-admins without calling admin endpoints", async () => {
    vi.mocked(session.getMe).mockResolvedValue(makeUser());
    renderApp(<AdminConsole />);
    expect(await screen.findByText("Admins only")).toBeInTheDocument();
    expect(session.adminStats).not.toHaveBeenCalled();
  });
});

describe("AdminConsole for an admin", () => {
  beforeEach(() => {
    vi.mocked(session.getMe).mockResolvedValue(makeUser({ role: "admin" }));
  });

  it("shows the overview numbers and highlights what needs review", async () => {
    renderApp(<AdminConsole />);
    const review = (await screen.findByText("Needs review")).closest(".stat-card") as HTMLElement;
    expect(review).toHaveClass("stat-warn");
    expect(within(review).getByText("3 open reports")).toBeInTheDocument();
    fireEvent.click(review);
    expect(router.replace).toHaveBeenCalledWith("/admin?tab=reports", { scroll: false });
  });

  it("dismisses reports only after confirmation", async () => {
    nav.search = new URLSearchParams("tab=reports");
    const group = {
      pin: {
        id: 9, latitude: 1, longitude: 2, title: "Spammy pin", species_slug: null, species_label: null, caught_on: null,
        created_at: "2026-09-25T12:00:00Z", visibility: "public" as const, status: "hidden" as const, status_reason: "reports",
        author: { id: 3, display_name: "Spammer" }, lake: null, photo_count: 0, thumb_url: null, is_mine: false,
      },
      reports: [{ id: 1, reason: "spam", reason_label: "Spam or advertising", detail: "ad", reporter: "Bob", created_at: "2026-09-25T12:00:00Z" }],
    };
    vi.mocked(session.adminReports).mockResolvedValueOnce([group]).mockResolvedValueOnce([]);
    vi.mocked(session.adminResolve).mockResolvedValue({ ...group.pin, open_reports: 0, author_email: "s@x.co" });
    renderApp(<AdminConsole />);

    fireEvent.click(await screen.findByRole("button", { name: "Dismiss" }));
    expect(session.adminResolve).not.toHaveBeenCalled();
    expect(screen.getByText("Dismiss these reports?")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Dismiss" }).at(-1)!);
    await waitFor(() => expect(session.adminResolve).toHaveBeenCalledWith(9, "dismiss"));
    expect(await screen.findByText("All clear")).toBeInTheDocument();
  });

  it("never offers role or status changes on the admin's own row", async () => {
    nav.search = new URLSearchParams("tab=users");
    vi.mocked(session.adminUsers).mockResolvedValue({
      total: 2,
      page: 1,
      page_size: 25,
      items: [
        { id: 1, email: "amy@example.com", display_name: "Angler Amy", role: "admin", status: "active", has_password: true, google_connected: false, created_at: "2026-09-25T12:00:00Z", last_login_at: null, pins: 0, reports_against: 0 },
        { id: 2, email: "bob@example.com", display_name: "Bob", role: "user", status: "active", has_password: true, google_connected: false, created_at: "2026-09-25T12:00:00Z", last_login_at: null, pins: 2, reports_against: 1 },
      ],
    });
    renderApp(<AdminConsole />);
    const myRow = (await screen.findByText("amy@example.com")).closest("tr") as HTMLElement;
    expect(within(myRow).queryByRole("button")).toBeNull();
    const bobRow = screen.getByText("bob@example.com").closest("tr") as HTMLElement;
    fireEvent.click(within(bobRow).getByRole("button", { name: "Suspend" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(session.adminUpdateUser).toHaveBeenCalledWith(2, { status: "suspended" }));
  });
});
