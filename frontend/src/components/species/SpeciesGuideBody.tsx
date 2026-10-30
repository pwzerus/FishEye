"use client";

import type { GuideSource, SpeciesGuide, TackleSetup } from "@/lib/api/types";
import { GuideSummary } from "@/components/fish/GuideSummary";
import { LimitsNote } from "@/components/rules/RegionGate";
import { useT } from "@/i18n/client";
import { groupSetups } from "./setups";

export { groupSetups };

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

export function DifficultyTag({ guide }: { guide: SpeciesGuide }) {
  const t = useT().fish;
  if (guide.role === "forage") return <span className="guide-tag guide-tag-forage">{t.baitFish}</span>;
  if (!guide.difficulty) return null;
  const label = { beginner: t.beginner, intermediate: t.intermediate, advanced: t.advanced }[guide.difficulty];
  return <span className={`guide-tag guide-tag-${guide.difficulty}`}>{label}</span>;
}

/** What it eats, in one word: carnivore, omnivore, or (for shad) filter
 * feeder. Shown next to "What it eats" so it reads at a glance. */
export function DietTypeTag({ guide }: { guide: SpeciesGuide }) {
  const t = useT().fish;
  const label = { carnivore: t.carnivore, omnivore: t.omnivore, filter_feeder: t.filterFeeder }[guide.diet_type];
  return <span className={`guide-tag guide-tag-diet guide-tag-diet-${guide.diet_type}`}>{label}</span>;
}

function SourceLinks({ sources }: { sources: GuideSource[] }) {
  const t = useT().fish;
  return (
    <p className="guide-setup-sources">
      {t.source}{" "}
      {sources.map((s, i) => (
        <span key={s.url}>
          {i > 0 && " · "}
          <a href={s.url} target="_blank" rel="noreferrer">
            {s.label}
          </a>
          {s.kind === "guide" && <span className="guide-source-kind">{t.guideSite}</span>}
        </span>
      ))}
    </p>
  );
}

function SetupCard({ setup }: { setup: TackleSetup }) {
  const t = useT().fish;
  return (
    <li className="guide-setup">
      <div className="guide-setup-name" lang="en">{setup.name}</div>
      <div className="guide-setup-when" lang="en">{setup.use_when}</div>
      <dl className="guide-setup-specs">
        <dt>{t.rod}</dt>
        <dd lang="en">{setup.rod}</dd>
        <dt>{t.reel}</dt>
        <dd lang="en">{setup.reel}</dd>
        <dt>{t.line}</dt>
        <dd lang="en">{setup.line}</dd>
        <dt>{t.hookRig}</dt>
        <dd lang="en">{setup.terminal}</dd>
      </dl>
      <SourceLinks sources={setup.sources} />
    </li>
  );
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
      <ul lang="en">
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
  const t = useT().fish;

  return (
    <div className={compact ? "guide-body guide-body-compact" : "guide-body"}>
      {!compact && <p className="guide-summary" lang="en"><GuideSummary guide={guide} /></p>}

      {!compact && (
        <section className="guide-section">
          <h4>
            {t.whatItEats} <DietTypeTag guide={guide} />
          </h4>
          <p lang="en">{guide.diet}</p>
        </section>
      )}

      {!compact && <Bullets title={t.recognise} items={guide.identification} />}
      {!compact && <Bullets title={t.whereWhen} items={guide.where_and_when} />}

      {isForage ? (
        <>
          <Bullets title={t.howToGetShort} items={guide.how_to_get} />
          <Bullets title={t.baitFor} items={guide.bait_for} />
        </>
      ) : (
        <>
          <Bullets title={t.liveBait} items={guide.live_baits} />
          <Bullets title={t.lures} items={guide.lures} />
          <p className="guide-setups-intro">{t.setupsNote}</p>
          <SetupGroup title={t.lureFishing} setups={groupSetups(guide.setups).lure} />
          <SetupGroup title={t.baitFishing} setups={groupSetups(guide.setups).bait} />
        </>
      )}

      <Bullets title={t.tips} items={guide.tips} />

      {!compact && guide.legal_notes.length > 0 && (
        <section className="guide-section guide-legal">
          <h4>{t.baitRules}</h4>
          <ul lang="en">
            {guide.legal_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      )}

      {/* The chosen state's agency, not Texas's for everyone. */}
      <LimitsNote className="guide-limits" texasUrl={guide.limits_url} />

      {!compact && (
        <section className="guide-section guide-sources">
          <h4>{t.sources}</h4>
          <ul>
            {guide.sources.map((s) => (
              <li key={s.url}>
                <a href={s.url} target="_blank" rel="noreferrer">
                  {s.label}
                </a>
                {s.kind === "guide" && <span className="guide-source-kind">{t.guideSite}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
