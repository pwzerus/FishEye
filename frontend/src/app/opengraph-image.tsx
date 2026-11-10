import { OG_SIZE, ogCard } from "@/lib/ogCard";

// The site's own preview, for every page that doesn't draw its own.
export const alt = "FishEye: learn to fish. Where to go, what to use and why it works, and the rules.";
export const size = OG_SIZE;
export const contentType = "image/png";

export default function Image() {
  return ogCard({
    eyebrow: "Learn to fish",
    title: "Where to go. What to use. Why it works.",
    subtitle: "Beginner guides to each fish, the lakes near you, and your state's rules, in plain words.",
  });
}
