import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { Leaderboard as Board, PinDetail } from "@/lib/api/types";
import { makeUser, renderApp } from "@/test-utils";

vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return {
    ...actual,
    getMe: vi.fn(),
    getPinOptions: vi.fn(),
    likePin: vi.fn(),
    unlikePin: vi.fn(),
    listComments: vi.fn(),
    addComment: vi.fn(),
    deleteComment: vi.fn(),
    getLeaderboard: vi.fn(),
    listAlerts: vi.fn(),
    deleteAlert: vi.fn(),
    unsubscribeAlert: vi.fn(),
  };
});
const session = await import("@/lib/api/session");
const { CommentsSection, LikeButton } = await import("./Social");
const { Leaderboard } = await import("./Leaderboard");
const { AlertsSection } = await import("@/components/auth/AlertsSection");

function pin(overrides: Partial<PinDetail> = {}): PinDetail {
  return {
    id: 7,
    latitude: 32.8,
    longitude: -95.6,
    location_shown: "lake",
    share_exact: false,
    public_place: "lake",
    title: "Dam bank",
    species_slug: "bluegill",
    species_label: "Bluegill",
    species_check: "confirmed",
    species_check_label: null,
    caught_on: "2026-11-01",
    created_at: "2026-11-01T12:00:00Z",
    visibility: "public",
    status: "published",
    status_reason: null,
    author: { id: 2, display_name: "Pat" },
    lake: null,
    photo_count: 0,
    thumb_url: null,
    is_mine: false,
    note: null,
    photos: [],
    can_edit: false,
    can_report: true,
    reported_by_me: false,
    like_count: 2,
    comment_count: 0,
    liked_by_me: false,
    ...overrides,
  } as PinDetail;
}

const comment = (id: number, body: string, overrides = {}) => ({
  id,
  body,
  created_at: "2026-11-02T12:00:00Z",
  author: { id: 3, display_name: "Sam" },
  status: "published" as const,
  is_mine: false,
  can_delete: false,
  can_report: true,
  ...overrides,
});

beforeEach(() => {
  vi.mocked(session.getMe).mockResolvedValue(makeUser());
  vi.mocked(session.likePin).mockReset();
  vi.mocked(session.unlikePin).mockReset();
  vi.mocked(session.addComment).mockReset();
  vi.mocked(session.deleteComment).mockReset();
  vi.mocked(session.listComments).mockResolvedValue([]);
});

describe("LikeButton", () => {
  it("likes a catch and shows the new count", async () => {
    vi.mocked(session.likePin).mockResolvedValue({ liked: true, like_count: 3 });
    renderApp(<LikeButton pin={pin()} />);
    fireEvent.click(await screen.findByRole("button", { name: /Like · 2/ }));
    expect(await screen.findByRole("button", { name: /Liked · 3/ })).toHaveAttribute("aria-pressed", "true");
    expect(session.likePin).toHaveBeenCalledWith(7);
  });

  it("goes back when the server refuses", async () => {
    vi.mocked(session.likePin).mockRejectedValue(new ApiError("You're doing that a lot.", 429));
    renderApp(<LikeButton pin={pin()} />);
    fireEvent.click(await screen.findByRole("button", { name: /Like · 2/ }));
    expect(await screen.findByText("You're doing that a lot.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Like · 2/ })).toBeInTheDocument();
  });

  it("is a count on your own catch, and a way to sign in when signed out", async () => {
    const { unmount } = renderApp(<LikeButton pin={pin({ is_mine: true })} />);
    expect(await screen.findByText(/2 likes/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    unmount();
    vi.mocked(session.getMe).mockResolvedValue(null);
    renderApp(<LikeButton pin={pin()} />);
    await waitFor(() => expect(screen.getByRole("link", { name: /2 likes/ })).toHaveAttribute("href", "/login?next=/community/7"));
  });

  it("isn't offered on a private catch", async () => {
    const { container } = renderApp(<LikeButton pin={pin({ visibility: "private" })} />);
    await waitFor(() => expect(session.getMe).toHaveBeenCalled());
    expect(container.querySelector(".like-button")).toBeNull();
  });
});

describe("CommentsSection", () => {
  it("lists the comments and adds a new one at the end", async () => {
    vi.mocked(session.listComments).mockResolvedValue([comment(1, "What bait?")]);
    vi.mocked(session.addComment).mockResolvedValue(comment(2, "A jig.", { is_mine: true, can_delete: true, can_report: false }));
    renderApp(<CommentsSection pin={pin()} />);
    expect(await screen.findByText("What bait?")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Add a comment"), { target: { value: "A jig." } });
    fireEvent.click(screen.getByRole("button", { name: "Post" }));
    expect(await screen.findByText("A jig.")).toBeInTheDocument();
    expect(session.addComment).toHaveBeenCalledWith(7, "A jig.");
    expect(screen.getByLabelText("Add a comment")).toHaveValue("");
  });

  it("asks you to sign in instead of showing the form", async () => {
    vi.mocked(session.getMe).mockResolvedValue(null);
    renderApp(<CommentsSection pin={pin()} />);
    expect(await screen.findByRole("link", { name: "Sign in to comment" })).toHaveAttribute("href", "/login?next=/community/7");
    expect(screen.queryByLabelText("Add a comment")).not.toBeInTheDocument();
  });

  it("takes away a deleted comment, and shows delete only to those who may", async () => {
    vi.mocked(session.listComments).mockResolvedValue([comment(1, "Mine", { can_delete: true, can_report: false }), comment(2, "Theirs")]);
    vi.mocked(session.deleteComment).mockResolvedValue(undefined);
    renderApp(<CommentsSection pin={pin()} />);
    await screen.findByText("Mine");
    expect(screen.getAllByRole("button", { name: "Delete" })).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(screen.queryByText("Mine")).not.toBeInTheDocument());
    expect(screen.getByText("Theirs")).toBeInTheDocument();
  });
});

describe("Leaderboard", () => {
  const board = (overrides: Partial<Board> = {}): Board => ({
    metric: "catches",
    period: "30d",
    entries: [
      { rank: 1, user_id: 2, display_name: "Pat", value: 5, is_me: false },
      { rank: 2, user_id: 3, display_name: "Sam", value: 2, is_me: true },
    ],
    me: null,
    ...overrides,
  });

  it("is for the place being browsed, and links to each angler", async () => {
    vi.mocked(session.getLeaderboard).mockResolvedValue(board());
    renderApp(<Leaderboard state="TX" county="48453" where="Travis County" />);
    expect(await screen.findByRole("link", { name: "Pat" })).toHaveAttribute("href", "/community/anglers/2");
    expect(screen.getByRole("link", { name: "Sam (you)" })).toBeInTheDocument();
    expect(screen.getByText("5 fish")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Top anglers in Travis County" })).toBeInTheDocument();
    expect(session.getLeaderboard).toHaveBeenCalledWith({ metric: "catches", period: "30d", state: "TX", county: "48453" });
  });

  it("asks again for another board and says when there's nobody on it", async () => {
    vi.mocked(session.getLeaderboard).mockResolvedValueOnce(board()).mockResolvedValue(board({ metric: "likes", entries: [] }));
    renderApp(<Leaderboard where={null} />);
    await screen.findByRole("link", { name: "Pat" });
    fireEvent.click(screen.getByRole("tab", { name: "Likes" }));
    expect(await screen.findByText("Nobody yet. Share a catch and you're first.")).toBeInTheDocument();
    expect(vi.mocked(session.getLeaderboard).mock.lastCall?.[0].metric).toBe("likes");
  });

  it("says where you stand when you're below the top", async () => {
    vi.mocked(session.getLeaderboard).mockResolvedValue(board({ me: { rank: 14, user_id: 9, display_name: "Me", value: 1, is_me: true }, entries: board().entries.map((e) => ({ ...e, is_me: false })) }));
    renderApp(<Leaderboard where={null} />);
    expect(await screen.findByText(/You're number 14/)).toBeInTheDocument();
  });
});

describe("AlertsSection", () => {
  const info = {
    alerts: [{ id: 1, species_slug: "bluegill", species_label: "Bluegill", place: "Austin, TX", radius_miles: 30, created_at: "2026-11-01T12:00:00Z", last_sent_at: null }],
    email: "me@example.com",
    email_confirmed: false,
    sending: false,
    max_alerts: 10,
    min_radius: 1,
    max_radius: 500,
  };

  beforeEach(() => {
    vi.mocked(session.getPinOptions).mockResolvedValue({ species: [{ slug: "bluegill", label: "Bluegill" }], report_reasons: [], max_photos: 4, max_photo_mb: 10 });
  });

  it("says plainly that emails aren't on yet", async () => {
    vi.mocked(session.listAlerts).mockResolvedValue(info);
    renderApp(<AlertsSection />);
    expect(await screen.findByText(/Emails aren't switched on yet/)).toBeInTheDocument();
    expect(screen.getByText("Bluegill within 30 miles of Austin, TX")).toBeInTheDocument();
  });

  it("asks for a confirmed address once mail is on", async () => {
    vi.mocked(session.listAlerts).mockResolvedValue({ ...info, sending: true });
    renderApp(<AlertsSection />);
    expect(await screen.findByText(/Confirm me@example.com to receive them/)).toBeInTheDocument();
  });

  it("deletes an alert", async () => {
    vi.mocked(session.listAlerts).mockResolvedValue(info);
    vi.mocked(session.deleteAlert).mockResolvedValue(undefined);
    renderApp(<AlertsSection />);
    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
    await waitFor(() => expect(screen.queryByText(/within 30 miles/)).not.toBeInTheDocument());
    expect(session.deleteAlert).toHaveBeenCalledWith(1);
  });
});
