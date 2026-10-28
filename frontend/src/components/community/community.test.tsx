import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { FishIdResult, FishVerdict, PinSummary } from "@/lib/api/types";
import { JPEG_WITH_EXIF, fixtureBytes } from "@/lib/exif.fixture";
import { makeUser, renderApp } from "@/test-utils";

// vi.mock is hoisted above imports, so the factory imports what it needs itself.
vi.mock("next/navigation", async () => (await import("@/test-utils")).navigationMock());
vi.mock("@/lib/api/session", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/session")>("@/lib/api/session");
  return { ...actual, getMe: vi.fn(), getPinOptions: vi.fn(), createPin: vi.fn(), listPins: vi.fn(), listPinPlaces: vi.fn(), pinWhere: vi.fn(), adminSetPinStatus: vi.fn(), adminPurgePin: vi.fn(), identifyFish: vi.fn(), getPin: vi.fn() };
});
const session = await import("@/lib/api/session");
const { PhotoPicker } = await import("./PhotoPicker");
const { PinForm } = await import("./PinForm");
const { PinCard, formatDay } = await import("./PinCard");
const { CommunityFeed } = await import("./CommunityFeed");
const { PinDetailView } = await import("./PinDetailView");

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
    species_check: null,
    species_check_label: null,
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
  vi.mocked(session.identifyFish).mockReset();
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

const LARGEMOUTH = { slug: "largemouth-bass", label: "Largemouth Bass", probability: 0.86, in_guides: true };
const CATFISH = { slug: "channel-catfish", label: "Channel Catfish", probability: 0.9, in_guides: true };

function idResult(candidates: (typeof LARGEMOUTH)[], verdict: Partial<FishVerdict> | null = null): FishIdResult {
  return {
    available: true,
    model: "bioclip",
    fish_probability: 0.99,
    candidates,
    verdict: verdict && {
      status: "confirmed", accepted: true, detected: null, detected_label: null, detected_in_guides: false, message: "", ...verdict,
    },
  };
}

function choosePhoto(container: HTMLElement, name = "catch.jpg") {
  const input = container.querySelector("input[type=file][multiple]") as HTMLInputElement;
  fireEvent.change(input, { target: { files: [file(name)] } });
}

describe("PinForm", () => {
  it("fills in the fish the photo shows, checks it, and shares the catch", async () => {
    const created = { ...pin({ is_mine: true }), note: null, photos: [], can_edit: true, can_report: false, reported_by_me: false };
    vi.mocked(session.createPin).mockImplementation(async (_p, onProgress) => {
      onProgress?.(0.5);
      return created;
    });
    vi.mocked(session.identifyFish).mockImplementation(async (_photo, claim) =>
      claim?.species_slug
        ? idResult([LARGEMOUTH], { status: "confirmed", accepted: true, message: "Photo check: this looks like a Largemouth Bass." })
        : idResult([LARGEMOUTH]),
    );
    const onCreated = vi.fn();
    const { container } = render(<PinForm point={{ latitude: 32.8, longitude: -95.6 }} onCreated={onCreated} onCancel={vi.fn()} />);
    await screen.findByRole("option", { name: "Bluegill" });

    choosePhoto(container);
    expect(await screen.findByText("Photo check: this looks like a Largemouth Bass.")).toBeInTheDocument();
    expect(screen.getByLabelText("Fish")).toHaveValue("largemouth-bass");
    fireEvent.click(screen.getByRole("button", { name: "Share catch" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(created));
    expect(vi.mocked(session.createPin).mock.calls[0][0]).toMatchObject({
      title: "Largemouth Bass", // no title typed: the fish's name
      species_slug: "largemouth-bass",
      photos: [expect.objectContaining({ name: "catch.jpg" })],
    });
  });

  it("won't share a fish the photo contradicts, and offers the fish it shows", async () => {
    vi.mocked(session.identifyFish).mockImplementation(async (_photo, claim) =>
      claim?.species_slug === "largemouth-bass"
        ? idResult([CATFISH], {
            status: "mismatch", accepted: false, detected: "channel-catfish", detected_label: "Channel Catfish", detected_in_guides: true,
            message: "This looks like a Channel Catfish, not a Largemouth Bass.",
          })
        : idResult([CATFISH], { status: "confirmed", accepted: true, message: "Photo check: this looks like a Channel Catfish." }),
    );
    const { container } = render(<PinForm point={{ latitude: 1, longitude: 2 }} onCreated={vi.fn()} onCancel={vi.fn()} />);
    await screen.findByRole("option", { name: "Bluegill" });
    fireEvent.change(screen.getByLabelText("Fish"), { target: { value: "largemouth-bass" } });
    choosePhoto(container);

    expect(await screen.findByText("This looks like a Channel Catfish, not a Largemouth Bass.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Share catch" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Share without naming the fish" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Change to Channel Catfish" }));
    expect(await screen.findByText("Photo check: this looks like a Channel Catfish.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Share catch" })).not.toBeDisabled();
  });

  it("accepts a look-alike as its group, and names a fish with no guide as Other", async () => {
    vi.mocked(session.identifyFish).mockImplementation(async (_photo, claim) =>
      claim?.species_slug === "largemouth-bass"
        ? idResult([LARGEMOUTH], {
            status: "other_fish", accepted: false, detected: "walleye", detected_label: "Walleye", detected_in_guides: false,
            message: "This looks like a Walleye, not a Largemouth Bass.",
          })
        : idResult([LARGEMOUTH], { status: "group", accepted: true, message: "Photo check: this looks like a black bass." }),
    );
    const { container } = render(<PinForm point={{ latitude: 1, longitude: 2 }} onCreated={vi.fn()} onCancel={vi.fn()} />);
    await screen.findByRole("option", { name: "Bluegill" });
    fireEvent.change(screen.getByLabelText("Fish"), { target: { value: "largemouth-bass" } });
    choosePhoto(container);

    fireEvent.click(await screen.findByRole("button", { name: "Choose Other: Walleye" }));
    expect(screen.getByLabelText("Fish")).toHaveValue("__other");
    expect(screen.getByLabelText("Which fish?")).toHaveValue("Walleye");
    expect(await screen.findByText("Photo check: this looks like a black bass.")).toBeInTheDocument();
  });

  it("offers what the photo looks like when the angler isn't sure", async () => {
    vi.mocked(session.identifyFish).mockResolvedValue(idResult([{ ...LARGEMOUTH, probability: 0.42 }, { ...CATFISH, probability: 0.3 }]));
    const { container } = render(<PinForm point={{ latitude: 1, longitude: 2 }} onCreated={vi.fn()} onCancel={vi.fn()} />);
    await screen.findByRole("option", { name: "Bluegill" });
    choosePhoto(container);
    // Under the bar for filling it in: offered, not chosen.
    const chip = await screen.findByRole("button", { name: /Largemouth Bass 42%/ });
    expect(screen.getByLabelText("Fish")).toHaveValue("");
    fireEvent.click(chip);
    expect(screen.getByLabelText("Fish")).toHaveValue("largemouth-bass");
  });

  it("asks for a photo before sharing a named fish", async () => {
    render(<PinForm point={{ latitude: 1, longitude: 2 }} onCreated={vi.fn()} onCancel={vi.fn()} />);
    await screen.findByRole("option", { name: "Bluegill" });
    fireEvent.change(screen.getByLabelText("Fish"), { target: { value: "bluegill" } });
    expect(screen.getByText(/Add a photo of the fish/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Share catch" })).toBeDisabled();
  });

  it("shares a spot with no fish named, with its privacy", async () => {
    const created = { ...pin({ is_mine: true, visibility: "private" }), note: null, photos: [], can_edit: true, can_report: false, reported_by_me: false };
    vi.mocked(session.createPin).mockResolvedValue(created);
    render(<PinForm point={{ latitude: 32.8, longitude: -95.6 }} onCreated={vi.fn()} onCancel={vi.fn()} />);
    await screen.findByRole("option", { name: "Bluegill" });
    fireEvent.change(screen.getByPlaceholderText("e.g. Rocks by the boat ramp"), { target: { value: "Creek mouth" } });
    fireEvent.click(screen.getByRole("radio", { name: /Only me/ }));
    fireEvent.click(screen.getByRole("button", { name: "Share catch" }));
    await waitFor(() =>
      expect(vi.mocked(session.createPin).mock.calls[0][0]).toMatchObject({
        title: "Creek mouth", species_slug: undefined, species_other: undefined, visibility: "private", photos: [],
      }),
    );
  });

  it("keeps the form and shows the error when saving fails", async () => {
    const { ApiError } = await import("@/lib/api/client");
    vi.mocked(session.createPin).mockRejectedValue(new ApiError("Photo 1: That file isn't a photo we can read.", 422));
    render(<PinForm point={{ latitude: 1, longitude: 2 }} onCreated={vi.fn()} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByPlaceholderText("e.g. Rocks by the boat ramp"), { target: { value: "Pier" } });
    fireEvent.click(screen.getByRole("button", { name: "Share catch" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Photo 1");
    expect(screen.getByRole("button", { name: "Share catch" })).not.toBeDisabled();
  });

  it("takes the date from the photo, and offers to move the pin to where it was taken", async () => {
    vi.mocked(session.identifyFish).mockResolvedValue(idResult([LARGEMOUTH]));
    const onMove = vi.fn();
    const { container } = render(
      <PinForm point={{ latitude: 33.9, longitude: -84.2 }} onCreated={vi.fn()} onCancel={vi.fn()} onMove={onMove} />,
    );
    const photo = new File([fixtureBytes(JPEG_WITH_EXIF)], "phone.jpg", { type: "image/jpeg" });
    fireEvent.change(container.querySelector("input[type=file][multiple]") as HTMLInputElement, { target: { files: [photo] } });

    await waitFor(() => expect(screen.getByLabelText("Date")).toHaveValue("2026-09-20"));
    fireEvent.click(await screen.findByRole("button", { name: "Move the pin there" }));
    expect(onMove).toHaveBeenCalledWith(expect.closeTo(32.80639, 4), expect.closeTo(-95.58639, 4));
  });

  it("has nothing to share before a title, a photo or a fish", () => {
    render(<PinForm point={{ latitude: 1, longitude: 2 }} onCreated={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Share catch" })).toBeDisabled();
  });
});

describe("PinDetailView", () => {
  it("says what the photo check found and shares a public catch's link", async () => {
    const detail = {
      ...pin({ species_check: "confirmed", title: "Riprap by the dam" }),
      note: null, photos: [], can_edit: false, can_report: true, reported_by_me: false,
    };
    vi.mocked(session.getPin).mockResolvedValue(detail);
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    renderApp(<PinDetailView pinId={7} />);

    expect(await screen.findByText("The catch photo shows a Largemouth Bass.")).toBeInTheDocument();
    expect(screen.getByText("✓ Photo-checked")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Share" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(window.location.href));
    expect(await screen.findByText("Link copied")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Moderation" })).not.toBeInTheDocument();
  });

  it("lets the owner delete, but not edit, a catch a moderator hid", async () => {
    const detail = {
      ...pin({ status: "hidden", status_reason: "moderator", is_mine: true }),
      note: null, photos: [], can_edit: false, can_report: false, reported_by_me: false,
    };
    vi.mocked(session.getPin).mockResolvedValue(detail);
    renderApp(<PinDetailView pinId={7} />);
    expect(await screen.findByText(/can't be edited until the review, but you can delete it/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });

  it("lets an admin hide anyone's catch from its page", async () => {
    vi.mocked(session.getMe).mockResolvedValue(makeUser({ role: "admin" }));
    const detail = { ...pin(), note: null, photos: [], can_edit: false, can_report: true, reported_by_me: false };
    vi.mocked(session.getPin).mockResolvedValue(detail);
    vi.mocked(session.adminSetPinStatus).mockResolvedValue({ ...pin({ status: "hidden" }), open_reports: 0, author_email: "bob@example.com" });
    renderApp(<PinDetailView pinId={7} />);
    const bar = await screen.findByRole("region", { name: "Moderation" });
    expect(within(bar).getByText(/by Bob/)).toBeInTheDocument();
    expect(within(bar).queryByRole("button", { name: "Restore" })).not.toBeInTheDocument();
    fireEvent.click(within(bar).getByRole("button", { name: "Hide" }));
    fireEvent.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Hide" }));
    await waitFor(() => expect(session.adminSetPinStatus).toHaveBeenCalledWith(7, "hidden"));
    await waitFor(() => expect(session.getPin).toHaveBeenCalledTimes(2));
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
  const STATES = { level: "state" as const, places: [{ id: "TX", name: "Texas", count: 3 }, { id: "GA", name: "Georgia", count: 1 }] };
  const TX = { level: "county" as const, state_name: "Texas", places: [{ id: "48499", name: "Wood County", count: 2 }] };
  const WOOD = {
    level: "lake" as const,
    state_name: "Texas",
    county_name: "Wood County",
    places: [
      { id: "1", name: "Lake Fork", count: 1 },
      { id: "0", name: "Not at a mapped lake", count: 1 },
    ],
  };

  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState(null, "", "/community");
    vi.mocked(session.listPinPlaces).mockImplementation(async (p = {}) => (p.county ? WOOD : p.state ? TX : STATES));
  });

  it("starts by picking a state, never one nationwide pile", async () => {
    vi.mocked(session.listPins).mockResolvedValue([pin(), pin({ id: 8, title: "Pier" })]);
    renderApp(<CommunityFeed />);
    fireEvent.click(await screen.findByRole("button", { name: /Texas/ }));
    expect(await screen.findByText("Pier")).toBeInTheDocument();
    expect(session.listPins).toHaveBeenCalledTimes(1);
    expect(session.listPins).toHaveBeenLastCalledWith(expect.objectContaining({ state: "TX" }));
    expect(screen.getByRole("heading", { name: "Catches in Texas" })).toBeInTheDocument();
    expect(window.location.search).toBe("?state=TX");
  });

  it("goes down to a county and a lake, and back up", async () => {
    vi.mocked(session.listPins).mockResolvedValue([pin()]);
    window.history.replaceState(null, "", "/community?state=TX");
    renderApp(<CommunityFeed />);
    fireEvent.click(await screen.findByRole("button", { name: /Wood County/ }));
    await waitFor(() => expect(session.listPins).toHaveBeenLastCalledWith(expect.objectContaining({ county: "48499" })));
    fireEvent.click(await screen.findByRole("button", { name: /Lake Fork/ }));
    await waitFor(() => expect(session.listPins).toHaveBeenLastCalledWith(expect.objectContaining({ county: "48499", lake: "1" })));
    expect(await screen.findByRole("heading", { name: "Catches in Lake Fork" })).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("navigation", { name: "Place" })).getByRole("button", { name: "Texas" }));
    await waitFor(() => expect(window.location.search).toBe("?state=TX"));
  });

  it("shows an empty county with a way up to its state", async () => {
    vi.mocked(session.listPins).mockResolvedValue([]);
    vi.mocked(session.listPinPlaces).mockResolvedValue({ ...WOOD, places: [] });
    window.history.replaceState(null, "", "/community?state=TX&county=48499");
    renderApp(<CommunityFeed />);
    expect(await screen.findByText("No catches in Wood County, Texas yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "See all of Texas" })).toBeInTheDocument();
  });

  it("opens the county you are in from Near me", async () => {
    vi.mocked(session.listPins).mockResolvedValue([]);
    vi.mocked(session.pinWhere).mockResolvedValue({ state_code: "TX", state_name: "Texas", county_geoid: "48201", county_name: "Harris County" });
    const geo = { getCurrentPosition: vi.fn((ok: PositionCallback) => ok({ coords: { latitude: 29.76, longitude: -95.37 } } as GeolocationPosition)) };
    Object.defineProperty(navigator, "geolocation", { value: geo, configurable: true });
    renderApp(<CommunityFeed />);
    fireEvent.click(await screen.findByRole("button", { name: "Near me" }));
    await waitFor(() => expect(session.listPins).toHaveBeenLastCalledWith(expect.objectContaining({ state: "TX", county: "48201" })));
    expect(session.pinWhere).toHaveBeenCalledWith(29.76, -95.37);
  });

  it("filters to my pins and by species", async () => {
    vi.mocked(session.listPins).mockResolvedValue([]);
    window.history.replaceState(null, "", "/community?state=TX");
    renderApp(<CommunityFeed />);
    await waitFor(() => expect(session.listPins).toHaveBeenCalled());
    fireEvent.click(await screen.findByRole("tab", { name: "My catches" }));
    await waitFor(() => expect(session.listPins).toHaveBeenLastCalledWith(expect.objectContaining({ mine: true })));
    await screen.findByRole("option", { name: "Bluegill" });
    fireEvent.change(screen.getByLabelText("Fish"), { target: { value: "bluegill" } });
    await waitFor(() => expect(session.listPins).toHaveBeenLastCalledWith(expect.objectContaining({ species: "bluegill" })));
  });

  it("sends signed-out visitors through sign-in to add a pin", async () => {
    vi.mocked(session.getMe).mockResolvedValue(null);
    vi.mocked(session.listPins).mockResolvedValue([]);
    window.history.replaceState(null, "", "/community?state=TX");
    renderApp(<CommunityFeed />);
    await screen.findByText("No catches in Texas yet");
    const links = screen.getAllByText("Pin a catch").map((el) => el.closest("a")?.getAttribute("href"));
    expect(links.every((h) => h === "/login?next=%2Fmap%3FaddPin%3D1")).toBe(true);
    expect(screen.getByRole("tab", { name: "My catches" })).toBeDisabled();
  });
});
