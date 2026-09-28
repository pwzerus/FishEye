import type { GuideSource, SpeciesGuide, TackleSetup } from "@/lib/api/types";

/**
 * Renders one species guide. Used in two places:
 * - `compact` inside a lake's side panel: what to use and how, with a link
 *   to the full guide.
 * - full on the /fish page: everything, including identification, the
 *   legal notes and the complete source list.
 *
 * Every tackle setup shows where it came from. Sources that are a fishing
 * guide's or tackle site rather than an agency or established publication
 * say so, because a beginner can't tell otherwise.
 */

const DIFFICULTY_LABEL: Record<string, string> = {
  beginner: "Beginner-friendly",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

export function DifficultyTag({ guide }: { guide: SpeciesGuide }) {
  if (guide.role === "forage") return <span className="guide-tag guide-tag-forage">Bait fish</span>;
  if (!guide.difficulty) return null;
  return (
    <span className={`guide-tag guide-tag-${guide.difficulty}`}>
      {DIFFICULTY_LABEL[guide.difficulty]}
    </span>
  );
}

const DIET_TYPE_LABEL: Record<SpeciesGuide["diet_type"], string> = {
  carnivore: "Carnivore",
  omnivore: "Omnivore",
  filter_feeder: "Filter feeder",
};

/** What it eats, in one word: carnivore, omnivore, or (for shad) filter
 * feeder. Shown next to "What it eats" so it reads at a glance. */
export function DietTypeTag({ guide }: { guide: SpeciesGuide }) {
  return (
    <span className={`guide-tag guide-tag-diet guide-tag-diet-${guide.diet_type}`}>
      {DIET_TYPE_LABEL[guide.diet_type]}
    </span>
  );
}

function SourceLinks({ sources }: { sources: GuideSource[] }) {
  return (
    <p className="guide-setup-sources">
      Source:{" "}
      {sources.map((s, i) => (
        <span key={s.url}>
          {i > 0 && " · "}
          <a href={s.url} target="_blank" rel="noreferrer">
            {s.label}
          </a>
          {s.kind === "guide" && <span className="guide-source-kind"> (fishing guide site)</span>}
        </span>
      ))}
    </p>
  );
}

function SetupCard({ setup }: { setup: TackleSetup }) {
  return (
    <li className="guide-setup">
      <div className="guide-setup-name">{setup.name}</div>
      <div className="guide-setup-when">{setup.use_when}</div>
      <dl className="guide-setup-specs">
        <dt>Rod</dt>
        <dd>{setup.rod}</dd>
        <dt>Reel</dt>
        <dd>{setup.reel}</dd>
        <dt>Line</dt>
        <dd>{setup.line}</dd>
        <dt>Hook &amp; rig</dt>
        <dd>{setup.terminal}</dd>
      </dl>
      <SourceLinks sources={setup.sources} />
    </li>
  );
}

/** Lure setups and bait setups, grouped for the two sections below. A
 * setup naming both (method "either") appears in both groups, since the
 * text already says it works either way. */
export function groupSetups(setups: TackleSetup[]) {
  return {
    lure: setups.filter((s) => s.method === "lure" || s.method === "either"),
    bait: setups.filter((s) => s.method === "bait" || s.method === "either"),
  };
}

function SetupGroup({ title, setups }: { title: string; setups: TackleSetup[] }) {
  if (setups.length === 0) return null;
  return (
    <section className="guide-section guide-setup-group">
      <h4>{title}</h4>
      <ul className="guide-setups">
        {setups.map((setup) => (
          <SetupCard key={setup.name} setup={setup} />
        ))}
      </ul>
    </section>
  );
}

function Bullets({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <section className="guide-section">
      <h4>{title}</h4>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

export function SpeciesGuideBody({
  guide,
  compact = false,
}: {
  guide: SpeciesGuide;
  compact?: boolean;
}) {
  const isForage = guide.role === "forage";

  return (
    <div className={compact ? "guide-body guide-body-compact" : "guide-body"}>
      {!compact && <p className="guide-summary">{guide.summary}</p>}

      {!compact && (
        <section className="guide-section">
          <h4>
            What it eats <DietTypeTag guide={guide} />
          </h4>
          <p>{guide.diet}</p>
        </section>
      )}

      {!compact && <Bullets title="How to recognise it" items={guide.identification} />}
      {!compact && <Bullets title="Where and when" items={guide.where_and_when} />}

      {isForage ? (
        <>
          <Bullets title="How to get it" items={guide.how_to_get} />
          <Bullets title="Use it as bait for" items={guide.bait_for} />
        </>
      ) : (
        <>
          <Bullets title="Live and natural bait" items={guide.live_baits} />
          <Bullets title="Lures" items={guide.lures} />
          <p className="guide-setups-intro">
            Rod and reel setups, grouped by lure fishing (artificial baits) and bait
            fishing (live or natural bait):
          </p>
          <SetupGroup title="Lure fishing" setups={groupSetups(guide.setups).lure} />
          <SetupGroup title="Bait fishing" setups={groupSetups(guide.setups).bait} />
        </>
      )}

      <Bullets title="Tips" items={guide.tips} />

      {!compact && guide.legal_notes.length > 0 && (
        <section className="guide-section guide-legal">
          <h4>Bait rules</h4>
          <ul>
            {guide.legal_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      )}

      <p className="guide-limits">
        Size and bag limits vary by species and lake.{" "}
        <a href={guide.limits_url} target="_blank" rel="noreferrer">
          Check TPWD&apos;s current limits
        </a>{" "}
        before you keep a fish.
      </p>

      {!compact && (
        <section className="guide-section guide-sources">
          <h4>Sources</h4>
          <ul>
            {guide.sources.map((s) => (
              <li key={s.url}>
                <a href={s.url} target="_blank" rel="noreferrer">
                  {s.label}
                </a>
                {s.kind === "guide" && <span className="guide-source-kind"> (fishing guide site)</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
