import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FISH_SPECS } from "@/lib/fishArt";
import type { SpeciesGuide, SpeciesPhoto } from "@/lib/api/types";
import { FishArt } from "./FishArt";
import { FishGrid } from "./FishGrid";
import { HeroPhoto } from "./PhotoCard";

function guide(slug: string, name: string, extra: Partial<SpeciesGuide> = {}): SpeciesGuide {
  return {
    slug,
    common_name: name,
    scientific_name: "Genus species",
    role: "sport",
    difficulty: "beginner",
    summary: `${name} summary.`,
    diet: "",
    diet_type: "carnivore",
    where_and_when: [],
    live_baits: [],
    lures: [],
    setups: [],
    tips: [],
    identification: [],
    how_to_get: [],
    bait_for: [],
    legal_notes: [],
    limits_url: "https://tpwd.texas.gov/limits",
    sources: [],
    ...extra,
  };
}

const PHOTO: SpeciesPhoto = {
  url: "https://upload.wikimedia.org/x/960px.jpg",
  width: 960,
  height: 640,
  author: "Jane Doe",
  license: "CC BY-SA 4.0",
  license_url: "https://creativecommons.org/licenses/by-sa/4.0/",
  file_page: "https://commons.wikimedia.org/wiki/File:X.jpg",
  source: "wikimedia",
};

describe("FishArt", () => {
  it.each(Object.keys(FISH_SPECS))("draws %s", (slug) => {
    const { container } = render(<FishArt slug={slug} />);
    const svg = container.querySelector("svg.fish-art");
    expect(svg).not.toBeNull();
    // body gradient + clip, and nothing NaN'd its way into a path
    expect(container.querySelector(`#fa-${slug}-clip`)).not.toBeNull();
    expect(container.innerHTML).not.toContain("NaN");
  });

  it("gives each instance its own ids so two of the same fish can share a page", () => {
    const { container } = render(
      <>
        <FishArt slug="bluegill" uid="a" />
        <FishArt slug="bluegill" uid="b" />
      </>,
    );
    expect(container.querySelector("#fa-a-clip")).not.toBeNull();
    expect(container.querySelector("#fa-b-clip")).not.toBeNull();
  });

  it("is decorative unless given a title", () => {
    const { container, rerender } = render(<FishArt slug="bluegill" />);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    rerender(<FishArt slug="bluegill" title="Illustration of a Bluegill" />);
    expect(screen.getByRole("img", { name: "Illustration of a Bluegill" })).toBeInTheDocument();
  });

  it("draws the same speckles every render, so server and client markup match", () => {
    const a = render(<FishArt slug="black-crappie" uid="x" />).container.innerHTML;
    const b = render(<FishArt slug="black-crappie" uid="x" />).container.innerHTML;
    expect(a).toBe(b);
  });
});

describe("FishGrid", () => {
  const guides = [
    guide("bluegill", "Bluegill"),
    guide("blue-catfish", "Blue Catfish", { difficulty: "intermediate" }),
    guide("gizzard-shad", "Gizzard Shad", { role: "forage", difficulty: null }),
  ];

  it("links every card to its fish page", () => {
    render(<FishGrid guides={guides} photos={{}} />);
    expect(screen.getByText("Bluegill").closest("a")).toHaveAttribute("href", "/fish/bluegill");
  });

  it("filters by difficulty and by bait fish", () => {
    render(<FishGrid guides={guides} photos={{}} />);
    fireEvent.click(screen.getByRole("tab", { name: "Intermediate" }));
    expect(screen.getByText("Blue Catfish")).toBeInTheDocument();
    expect(screen.queryByText("Bluegill")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Bait fish" }));
    expect(screen.getByText("Gizzard Shad")).toBeInTheDocument();
    expect(screen.queryByText("Blue Catfish")).not.toBeInTheDocument();
  });

  it("searches by name and says so when nothing matches", () => {
    render(<FishGrid guides={guides} photos={{}} />);
    fireEvent.change(screen.getByLabelText("Search fish"), { target: { value: "cat" } });
    expect(screen.getByText("Blue Catfish")).toBeInTheDocument();
    expect(screen.queryByText("Bluegill")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search fish"), { target: { value: "shark" } });
    expect(screen.getByText(/No fish match/)).toBeInTheDocument();
  });

  it("shows a photo thumbnail only for fish that have one", () => {
    const { container } = render(<FishGrid guides={guides} photos={{ bluegill: PHOTO, "blue-catfish": null }} />);
    const thumbs = container.querySelectorAll(".fish-card-photo img");
    expect(thumbs).toHaveLength(1);
    expect(thumbs[0]).toHaveAttribute("src", PHOTO.url);
  });
});

describe("HeroPhoto", () => {
  it("renders nothing without a photo", () => {
    const { container } = render(<HeroPhoto photo={null} name="Bluegill" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the photo with the credit its licence requires", () => {
    render(<HeroPhoto photo={PHOTO} name="Bluegill" />);
    expect(screen.getByAltText("Photo of a Bluegill")).toHaveAttribute("src", PHOTO.url);
    const caption = screen.getByText(/Jane Doe/);
    expect(within(caption).getByText("CC BY-SA 4.0")).toHaveAttribute("href", PHOTO.license_url);
    expect(within(caption).getByText("Wikimedia")).toHaveAttribute("href", PHOTO.file_page);
  });
});
