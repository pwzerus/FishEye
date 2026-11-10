import { getSpeciesGuide } from "@/lib/api/client";
import { OG_SIZE, ogCard } from "@/lib/ogCard";

// A shared fish guide shows what it teaches: the fish, how hard it is for a
// beginner, and what to start with.
export const alt = "A FishEye guide to catching this fish";
export const size = OG_SIZE;
export const contentType = "image/png";

const LEVEL = { beginner: "Good for beginners", intermediate: "A step up from beginner", advanced: "For experienced anglers" };

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  try {
    const guide = await getSpeciesGuide(slug);
    // The guide's first bait is a sentence of its own ("Large live shiners
    // (8-9 in) under a bobber."): lower-cased into "Start with …".
    const first = (guide.live_baits[0] ?? "").trim().replace(/[.\s]+$/, "");
    const start = first ? `Start with ${first.charAt(0).toLowerCase()}${first.slice(1)}. ` : "";
    return ogCard({
      eyebrow: guide.difficulty ? `How to catch it · ${LEVEL[guide.difficulty]}` : "How to catch it",
      title: guide.common_name,
      subtitle: `${start}Where to look, why the bait works, and the rules on keeping one.`,
    });
  } catch {
    return ogCard({
      eyebrow: "Learn to fish",
      title: "Fish guides",
      subtitle: "Where each fish lives, what it bites and why, and how to catch it.",
    });
  }
}
