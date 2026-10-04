import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { PinSummary } from "@/lib/api/types";
import { makeUser, renderApp } from "@/test-utils";

// vi.mock is hoisted above imports, so the factory imports what it needs itself.
vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return { ...actual, getMe: vi.fn(), getPinOptions: vi.fn(), createPin: vi.fn(), listPins: vi.fn() };
});
const session = await import("@/lib/api/session");
const { PhotoPicker } = await import("./PhotoPicker");
const { PinForm } = await import("./PinForm");
const { PinCard, formatDay } = await import("./PinCard");
const { CommunityFeed } = await import("./CommunityFeed");

const OPTIONS = {
  species: [
    { slug: "bluegill", label: "Bluegill" },
    { slug: "largemouth-bass", label: "Largemouth Bass" },
  ],
  report_reasons: [{ id: "spam", label: "Spam or advertising" }],
  max_photos: 4,
  max_photo_mb: 10,
};

function pin(overrides: Partial<PinSummary> = {}): PinSummary {
  return {
    id: 7,
    latitude: 32.8,
    longitude: -95.6,
    title: "Riprap by the dam",
    species_slug: "largemouth-bass",
    species_label: "Largemouth Bass",
    caught_on: "2026-09-20",
    created_at: "2026-09-25T12:00:00Z",
    visibility: "public",
    status: "published",
    status_reason: null,
    author: { id: 2, display_name: "Bob" },
    lake: { id: 1, name: "Lake Fork" },
    photo_count: 0,
    thumb_url: null,
    is_mine: false,
    ...overrides,
  };
}

const file = (name: string, type = "image/jpeg", size = 1000) => new File([new Uint8Array(size)], name, { type });

beforeAll(() => {
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
});

beforeEach(() => {
  vi.mocked(session.getMe).mockResolvedValue(makeUser());
  vi.mocked(session.getPinOptions).mockResolvedValue(OPTIONS);
  vi.mocked(session.createPin).mockReset();
  vi.mocked(session.listPins).mockReset();
});

describe("PhotoPicker", () => {
  it("adds photos, refuses non-images and oversize files, and caps the count", () => {
    const onChange = vi.fn();
    const { container, rerender } = render(<PhotoPicker files={[]} onChange={onChange} max={2} maxMb={1} />);
    const input = container.querySelector("input[type=file]") as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file("a.jpg"), file("notes.pdf", "application/pdf")] } });
    expect(onChange).toHaveBeenLastCalledWith([expect.objectContaining({ name: "a.jpg" })]);
    expect(screen.getByText(/isn't a JPEG, PNG or WebP/)).toBeInTheDocument();

    fireEvent.change(input, { target: { files: [file("huge.jpg", "image/jpeg", 2 * 1024 * 1024)] } });
    expect(screen.getByText(/is over 1 MB/)).toBeInTheDocument();

    rerender(<PhotoPicker files={[file("a.jpg")]} onChange={onChange} max={2} maxMb={1} />);
    fireEvent.change(input, { target: { files: [file("b.jpg"), file("c.jpg")] } });
    expect(onChange.mock.lastCall?.[0]).toHaveLength(2);
    expect(screen.getByText("Up to 2 photos per pin.")).toBeInTheDocument();
  });

  it("removes a selected photo", () => {
    const onChange = vi.fn();
    render(<PhotoPicker files={[file("a.jpg"), file("b.jpg")]} onChange={onChange} max={4} maxMb={10} />);
    fireEvent.click(screen.getByLabelText("Remove photo 1"));
    expect(onChange).toHaveBeenCalledWith([expect.objectContaining({ name: "b.jpg" })]);
  });
});

describe("PinForm", () => {
  it("sends the pin, with free-text species and privacy, and reports success", async () => {
    const created = { ...pin({ is_mine: true, visibility: "private" }), note: null, photos: [], can_edit: true, can_report: false, reported_by_me: false };
    vi.mocked(session.createPin).mockImplementation(async (_p, onProgress) => {
      onProgress?.(0.5);
      return created;
    });
    const onCreated = vi.fn();
    render(<PinForm point={{ latitude: 32.8, longitude: -95.6 }} onCreated={onCreated} onCancel={vi.fn()} />);
    await screen.findByRole("option", { name: "Bluegill" });

    fireEvent.change(screen.getByPlaceholderText("e.g. Rocks by the boat ramp"), { target: { value: "Creek mouth" } });
    fireEvent.change(screen.getByLabelText("Fish"), { target: { value: "__other" } });
    fireEvent.change(screen.getByLabelText("Which fish?"), { target: { value: "Freshwater drum" } });
    fireEvent.click(screen.getByRole("radio", { name: /Only me/ }));
    fireEvent.click(screen.getByRole("button", { name: "Save pin" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(created));
    const sent = vi.mocked(session.createPin).mock.calls[0][0];
    expect(sent).toMatchObject({
      latitude: 32.8,
      longitude: -95.6,
      title: "Creek mouth",
      species_other: "Freshwater drum",
      species_slug: undefined,
      visibility: "private",
      photos: [],
    });
  });

  it("keeps the form and shows the error when saving fails", async () => {
    const { ApiError } = await import("@/lib/api/client");
    vi.mocked(session.createPin).mockRejectedValue(new ApiError("Photo 1: That file isn't a photo we can read.", 422));
    render(<PinForm point={{ latitude: 1, longitude: 2 }} onCreated={vi.fn()} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByPlaceholderText("e.g. Rocks by the boat ramp"), { target: { value: "Pier" } });
    fireEvent.click(screen.getByRole("button", { name: "Save pin" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Photo 1");
    expect(screen.getByRole("button", { name: "Save pin" })).not.toBeDisabled();
  });

  it("needs a title of at least 3 characters", () => {
    render(<PinForm point={{ latitude: 1, longitude: 2 }} onCreated={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Save pin" })).toBeDisabled();
  });
});

describe("PinCard", () => {
  it("links to the pin and labels privacy and moderation states", () => {
    render(<PinCard pin={pin({ visibility: "private", status: "hidden", is_mine: true })} />);
    expect(screen.getByText("Riprap by the dam").closest("a")).toHaveAttribute("href", "/community/7");
    expect(screen.getByText("Only you")).toBeInTheDocument();
    expect(screen.getByText("Hidden")).toBeInTheDocument();
    expect(screen.getByText(/^You ·/)).toBeInTheDocument();
    expect(screen.getByText("near Lake Fork")).toBeInTheDocument();
  });

  it("formats calendar dates without shifting them a day", () => {
    expect(formatDay("2026-09-20")).toContain("20");
  });
});

describe("CommunityFeed", () => {
  it("lists pins", async () => {
    vi.mocked(session.listPins).mockResolvedValue([pin(), pin({ id: 8, title: "Pier" })]);
    renderApp(<CommunityFeed />);
    expect(await screen.findByText("Pier")).toBeInTheDocument();
    expect(screen.getByText("Riprap by the dam")).toBeInTheDocument();
  });

  it("shows an empty state that invites the first pin", async () => {
    vi.mocked(session.listPins).mockResolvedValue([]);
    renderApp(<CommunityFeed />);
    expect(await screen.findByText("No pins here yet")).toBeInTheDocument();
  });

  it("filters to my pins and by species", async () => {
    vi.mocked(session.listPins).mockResolvedValue([]);
    renderApp(<CommunityFeed />);
    await waitFor(() => expect(session.listPins).toHaveBeenCalled());
    fireEvent.click(await screen.findByRole("tab", { name: "My pins" }));
    await waitFor(() => expect(session.listPins).toHaveBeenLastCalledWith(expect.objectContaining({ mine: true })));
    await screen.findByRole("option", { name: "Bluegill" });
    fireEvent.change(screen.getByLabelText("Fish"), { target: { value: "bluegill" } });
    await waitFor(() => expect(session.listPins).toHaveBeenLastCalledWith(expect.objectContaining({ species: "bluegill" })));
  });

  it("sends signed-out visitors through sign-in to add a pin", async () => {
    vi.mocked(session.getMe).mockResolvedValue(null);
    vi.mocked(session.listPins).mockResolvedValue([]);
    renderApp(<CommunityFeed />);
    await screen.findByText("No pins here yet");
    const links = screen.getAllByText("Pin a catch").map((el) => el.closest("a")?.getAttribute("href"));
    expect(links.every((h) => h === "/login?next=%2Fmap%3FaddPin%3D1")).toBe(true);
    expect(screen.getByRole("tab", { name: "My pins" })).toBeDisabled();
  });
});
