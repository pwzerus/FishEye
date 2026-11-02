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
    adminAskMisses: vi.fn(),
    adminReports: vi.fn(),
    adminResolve: vi.fn(),
    adminUsers: vi.fn(),
    adminUpdateUser: vi.fn(),
    adminUser: vi.fn(),
    adminResetLink: vi.fn(),
    adminConfirmEmail: vi.fn(),
    adminFeedback: vi.fn(),
    adminFeedbackExport: vi.fn(),
    adminUpdateFeedback: vi.fn(),
    getProviders: vi.fn(async () => ({ password: true, google: false, email_ready: false })),
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
        id: 9, latitude: 1, longitude: 2, location_shown: "exact" as const, share_exact: false, public_place: "area" as const,
        title: "Spammy pin", species_slug: null, species_label: null, species_check: null, species_check_label: null, caught_on: null,
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

  const USER = {
    has_password: true,
    google_connected: false,
    created_at: "2026-09-25T12:00:00Z",
    last_login_at: null,
    email_verified: true,
    pins: 0,
    reports_against: 0,
    role: "user" as const,
    status: "active" as const,
  };
  const DETAIL = {
    last_seen_at: null,
    sessions: 1,
    pins_public: 0,
    pins_private: 0,
    pins_hidden: 0,
    reports_filed: 0,
    feedback: 0,
    recent_pins: [],
    history: [],
  };
  const page = (items: unknown[]) =>
    ({ total: items.length, page: 1, page_size: 25, items, counts: { all: 2, admins: 1, suspended: 0, unconfirmed: 1, new_7d: 0 } }) as never;
  const BOB = { ...USER, id: 2, email: "bob@example.com", display_name: "Bob" };
  const AMY = { ...USER, id: 1, email: "amy@example.com", display_name: "Angler Amy", role: "admin" as const };

  it("lists accounts with counts, and filters and sorts them", async () => {
    nav.search = new URLSearchParams("tab=users");
    vi.mocked(session.adminUsers).mockResolvedValue(page([AMY, BOB]));
    renderApp(<AdminConsole />);
    expect(await screen.findByText(/bob@example.com/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Email not confirmed/ }));
    await waitFor(() => expect(session.adminUsers).toHaveBeenLastCalledWith(expect.objectContaining({ unconfirmed: true })));
    fireEvent.change(screen.getByLabelText("Sort"), { target: { value: "catches" } });
    await waitFor(() => expect(session.adminUsers).toHaveBeenLastCalledWith(expect.objectContaining({ sort: "catches" })));
  });

  it("opens an account from its row", async () => {
    nav.search = new URLSearchParams("tab=users");
    vi.mocked(session.adminUsers).mockResolvedValue(page([BOB]));
    renderApp(<AdminConsole />);
    fireEvent.click(await screen.findByRole("button", { name: "Bob" }));
    expect(router.replace).toHaveBeenCalledWith("/admin?tab=users&user=2", { scroll: false });
  });

  it("never offers role or status changes on the admin's own account", async () => {
    nav.search = new URLSearchParams("tab=users&user=1");
    vi.mocked(session.adminUsers).mockResolvedValue(page([AMY]));
    vi.mocked(session.adminUser).mockResolvedValue({ ...AMY, ...DETAIL });
    renderApp(<AdminConsole />);
    expect(await screen.findByRole("button", { name: "Save name", hidden: true })).toBeInTheDocument();
    for (const name of ["Suspend", "Remove admin", "Delete account", "Make a password reset link", "Sign out everywhere"]) {
      expect(screen.queryByRole("button", { name, hidden: true })).not.toBeInTheDocument();
    }
  });

  it("suspends someone after asking", async () => {
    nav.search = new URLSearchParams("tab=users&user=2");
    vi.mocked(session.adminUsers).mockResolvedValue(page([BOB]));
    vi.mocked(session.adminUser).mockResolvedValue({ ...BOB, ...DETAIL });
    vi.mocked(session.adminUpdateUser).mockResolvedValue({ ...BOB, status: "suspended" });
    renderApp(<AdminConsole />);
    fireEvent.click(await screen.findByRole("button", { name: "Suspend", hidden: true }));
    expect(session.adminUpdateUser).not.toHaveBeenCalled();
    fireEvent.click((await screen.findAllByRole("button", { name: "Suspend", hidden: true })).at(-1) as HTMLElement);
    await waitFor(() => expect(session.adminUpdateUser).toHaveBeenCalledWith(2, { status: "suspended" }));
  });

  it("shows a reset link once, to pass on", async () => {
    nav.search = new URLSearchParams("tab=users&user=2");
    vi.mocked(session.adminUsers).mockResolvedValue(page([BOB]));
    vi.mocked(session.adminUser).mockResolvedValue({ ...BOB, ...DETAIL });
    vi.mocked(session.adminResetLink).mockResolvedValue({ link: "https://x/reset-password?token=abc", expires_at: "2026-11-03T12:00:00Z", emailed: false });
    renderApp(<AdminConsole />);
    fireEvent.click(await screen.findByRole("button", { name: "Make a password reset link", hidden: true }));
    expect(await screen.findByDisplayValue("https://x/reset-password?token=abc")).toBeInTheDocument();
    expect(session.adminResetLink).toHaveBeenCalledWith(2, false);
  });

  it("only offers to confirm an address that isn't", async () => {
    nav.search = new URLSearchParams("tab=users&user=2");
    vi.mocked(session.adminUsers).mockResolvedValue(page([BOB]));
    vi.mocked(session.adminUser).mockResolvedValue({ ...BOB, ...DETAIL, email_verified: false });
    vi.mocked(session.adminConfirmEmail).mockResolvedValue({ ...BOB, ...DETAIL });
    renderApp(<AdminConsole />);
    fireEvent.click(await screen.findByRole("button", { name: "Confirm their email", hidden: true }));
    await waitFor(() => expect(session.adminConfirmEmail).toHaveBeenCalledWith(2));
  });

  it("shows feedback and marks it handled", async () => {
    nav.search = new URLSearchParams("tab=feedback");
    const row = {
      id: 7, message: "Add a dark mode", page: "/fish", lang: "ko", status: "new" as const, created_at: "2026-11-01T12:00:00Z",
      handled_at: null, user_id: 2, author_name: "Bob", author_email: "bob@example.com",
    };
    vi.mocked(session.adminFeedback).mockResolvedValue({ total: 1, page: 1, page_size: 25, items: [row] });
    vi.mocked(session.adminUpdateFeedback).mockResolvedValue({ ...row, status: "done" });
    renderApp(<AdminConsole />);
    expect(await screen.findByText("Add a dark mode")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Bob" })).toHaveAttribute("href", "/admin?tab=users&user=2");
    expect(screen.getByRole("link", { name: "Reply by email" }).getAttribute("href")).toContain("mailto:bob@example.com");
    fireEvent.click(screen.getByRole("button", { name: "Mark handled" }));
    await waitFor(() => expect(session.adminUpdateFeedback).toHaveBeenCalledWith(7, "done"));
  });

  it("copies feedback for Claude, without names", async () => {
    nav.search = new URLSearchParams("tab=feedback");
    vi.mocked(session.adminFeedback).mockResolvedValue({ total: 0, page: 1, page_size: 25, items: [] });
    vi.mocked(session.adminFeedbackExport).mockResolvedValue({ count: 3, text: "the text" });
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    renderApp(<AdminConsole />);
    fireEvent.click(await screen.findByRole("button", { name: "Copy for Claude" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("the text"));
    expect(session.adminFeedbackExport).toHaveBeenCalledWith("new");
    expect(await screen.findByText("Copied 3 messages")).toBeInTheDocument();
  });

  it("lists the questions Ask couldn't answer, most asked first", async () => {
    nav.search = new URLSearchParams("tab=ask");
    vi.mocked(session.getMe).mockResolvedValue(makeUser({ role: "admin" }));
    vi.mocked(session.adminAskMisses).mockResolvedValue([
      { question: "How do I catch walleye at night?", outcome: "unguided_fish", lang: "en", state: "MN", species_slug: null, count: 7, days: 3, last_day: "2026-11-01" },
    ]);
    renderApp(<AdminConsole />);
    const row = (await screen.findByText("How do I catch walleye at night?")).closest("tr") as HTMLElement;
    expect(row).toHaveTextContent("Fish without a guide");
    expect(row).toHaveTextContent("3 days");
    fireEvent.change(screen.getByLabelText("Why it missed"), { target: { value: "no_match" } });
    await waitFor(() => expect(session.adminAskMisses).toHaveBeenLastCalledWith(30, "no_match"));
  });
});
