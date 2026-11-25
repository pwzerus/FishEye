"use client";

import type { ReactNode } from "react";

import { LinkedText } from "@/components/terms/TermText";
import { useT } from "@/i18n/client";

import { Hook, Mark, Swivel, Wraps } from "./rigParts";
import { rigKeys, type RigKey } from "./rigTopics";
import { STEP_DRAWINGS, type StepKey } from "./StepDrawings";

/**
 * Drawings for the rig, knot and hook topics of the handbook (added
 * 2026-11-16: the owner asked for pictures of what a beginner can't follow
 * from words alone — threading an egg sinker, tying on a barrel swivel,
 * joining a leader, reading a hook size, telling a circle hook from a J hook,
 * rigging a wacky worm on an O-ring).
 *
 * A drawing carries numbers only. What each number points at is the list
 * under it, in the reader's language (messages `rigs`), so every word stays
 * text at a readable size on a phone and nothing has to be redrawn per
 * language. The parts follow the topic's own text (backend
 * angling_handbook.py): a size or a weight here is one the topic states.
 * Colours are the theme's, so the drawings work in dark mode.
 */

type Key = RigKey;

function SlidingSinkerRig() {
  return (
    <>
      <path className="rig-line rig-draw" pathLength={1} d="M8 62 H176" />
      <ellipse className="rig-lead" cx={96} cy={62} rx={25} ry={14} />
      <path className="rig-hole" d="M71 62 H121" />
      <path className="rig-arrow" d="M70 90 H122 M70 90 l6 -4 M70 90 l6 4 M122 90 l-6 -4 M122 90 l-6 4" />
      <Swivel x={176} y={62} />
      <circle className="rig-knot" cx={176} cy={62} r={2.6} />
      <path className="rig-leader rig-draw" pathLength={1} d="M220 62 H318" />
      <circle className="rig-knot" cx={220} cy={62} r={2.6} />
      <g transform="translate(321 62) matrix(0 1 1 0 0 0)">
        <Hook kind="circle" L={22} R={12} P={8} />
      </g>
      <Mark n={1} x={40} y={30} to={[40, 62]} />
      <Mark n={2} x={96} y={24} to={[96, 48]} />
      <Mark n={3} x={198} y={28} to={[198, 56]} />
      <Mark n={4} x={268} y={32} to={[268, 62]} />
      <Mark n={5} x={338} y={114} to={[338, 86]} />
    </>
  );
}

function SwivelAndLeader() {
  return (
    <>
      <path className="rig-line rig-draw" pathLength={1} d="M10 55 H131" />
      <Wraps x0={106} x1={124} y={55} />
      <path className="rig-line" d="M104 50 l-9 -7" />
      <Swivel x={131} y={55} big />
      <path className="rig-leader rig-draw" pathLength={1} d="M223 55 H350" />
      <Wraps x0={236} x1={254} y={55} lean={-1} />
      <path className="rig-leader" d="M256 50 l9 -7" />
      <Mark n={1} x={44} y={24} to={[44, 55]} />
      <Mark n={2} x={115} y={22} to={[115, 47]} />
      <Mark n={3} x={180} y={20} to={[180, 45]} />
      <Mark n={4} x={245} y={22} to={[245, 47]} />
      <Mark n={5} x={308} y={24} to={[308, 55]} />
    </>
  );
}

// Hook sizes, small to large, and roughly how big each draws (a 4/0 is 1).
const SIZES: [string, number][] = [
  ["#10", 0.3], ["#8", 0.36], ["#6", 0.43], ["#4", 0.52], ["#2", 0.62],
  ["#1", 0.68], ["1/0", 0.75], ["2/0", 0.83], ["4/0", 1], ["6/0", 1.18],
];
// The topic's ranges, as columns of SIZES: bluegill #4–8, crappie #2–6, bass #2–4/0, catfish #1–6/0.
const RANGES: [number, number][] = [[1, 3], [2, 4], [4, 8], [5, 9]];

function HookSizes() {
  const L = 46;
  const R = 11;
  const col = (i: number) => 26 + i * 38;
  const mid = (i: number) => col(i) + SIZES[i][1] * R;
  return (
    <>
      {SIZES.map(([label, s], i) => (
        <g key={label}>
          <g transform={`translate(${col(i)} ${118 - s * (L + R)}) scale(${s})`}>
            <Hook kind="j" L={L} R={R} P={20} />
          </g>
          <text className="rig-size" x={mid(i)} y={140}>
            {label}
          </text>
        </g>
      ))}
      {RANGES.map(([a, b], k) => {
        const y = 160 + k * 22;
        return (
          <g key={k}>
            <rect className="rig-bar" x={mid(a) - 9} y={y - 4} width={mid(b) - mid(a) + 18} height={8} rx={4} />
            <Mark n={k + 1} x={mid(a) - 22} y={y} />
          </g>
        );
      })}
    </>
  );
}

function CircleAndJ() {
  return (
    <>
      <g transform="translate(78 24) scale(1.8)">
        <Hook kind="circle" L={26} R={16} P={12} />
      </g>
      <g transform="translate(236 24) scale(1.8)">
        <Hook kind="j" L={40} R={13} P={16} />
      </g>
      <Mark n={1} x={160} y={52} to={[112, 40]} />
      <Mark n={2} x={330} y={50} to={[286, 66]} />
    </>
  );
}

function WackyRig() {
  return (
    <>
      <path className="rig-line rig-draw" pathLength={1} d="M8 18 C 80 18, 150 24, 175 47" />
      <path className="rig-worm" strokeWidth={13} d="M70 92 Q 180 60 290 92" />
      {/* The hook's bend runs under the ring, so the ring is drawn over it. */}
      <g transform="translate(175 51)">
        <Hook kind="circle" L={16} R={9} P={7} />
      </g>
      <ellipse className="rig-ring" cx={184} cy={76} rx={4.5} ry={10} />
      <path className="rig-arrow" d="M56 80 q-7 9 0 18 M304 80 q7 9 0 18" />
      <Mark n={1} x={40} y={44} to={[40, 19]} />
      <Mark n={2} x={184} y={114} to={[184, 88]} />
      <Mark n={3} x={230} y={42} to={[194, 60]} />
      <Mark n={4} x={318} y={62} to={[288, 86]} />
    </>
  );
}

function TexasRig() {
  return (
    <>
      <path className="rig-line rig-draw" pathLength={1} d="M8 52 H128" />
      <path className="rig-lead" d="M72 52 C 82 42, 96 41, 106 43 L106 61 C 96 63, 82 62, 72 52 Z" />
      <path className="rig-hole" d="M76 52 H106" />
      <path className="rig-worm" strokeWidth={14} d="M141 52 H300" />
      <path className="rig-worm" strokeWidth={5} d="M300 52 q 10 -10 20 0 t 20 0 t 12 -2" />
      <path className="rig-hidden" d="M134 52 H214" />
      <circle className="rig-metal" cx={130} cy={52} r={3.5} />
      <path className="rig-metal" d="M214 59 A9 9 0 0 1 196 59" />
      <Mark n={1} x={88} y={20} to={[88, 44]} />
      <Mark n={2} x={238} y={94} to={[212, 66]} />
      <Mark n={3} x={174} y={94} to={[196, 62]} />
      <Mark n={4} x={326} y={22} to={[326, 46]} />
    </>
  );
}

function NedRig() {
  return (
    <>
      <rect className="rig-bed" x={0} y={98} width={360} height={22} />
      <path className="rig-bedline" d="M0 98 H360" />
      <path className="rig-line rig-draw" pathLength={1} d="M8 30 C 60 30, 108 40, 124 60" />
      <path className="rig-worm" strokeWidth={12} d="M138 85 L226 55" />
      <path className="rig-lead" d="M132 70 A14 14 0 0 0 132 98 Z" />
      <circle className="rig-metal" cx={126} cy={64} r={4} />
      <Mark n={1} x={96} y={60} to={[122, 80]} />
      <Mark n={2} x={252} y={84} to={[214, 64]} />
    </>
  );
}

function DropShot() {
  return (
    <>
      <rect className="rig-bed" x={0} y={160} width={360} height={20} />
      <path className="rig-bedline" d="M0 160 H360" />
      <path className="rig-line rig-draw" pathLength={1} d="M40 8 C 120 10, 176 30, 180 60 L180 138" />
      <g transform="translate(180 72) rotate(-90)">
        <Hook kind="j" L={18} R={8} P={8} />
      </g>
      <path className="rig-worm" strokeWidth={10} d="M196 54 L286 54" />
      <circle className="rig-metal" cx={180} cy={140} r={3} />
      <ellipse className="rig-lead" cx={180} cy={150} rx={8} ry={10} />
      <Mark n={1} x={96} y={42} to={[118, 13]} />
      <Mark n={2} x={146} y={96} to={[178, 76]} />
      <Mark n={3} x={300} y={30} to={[278, 50]} />
      <Mark n={4} x={230} y={136} to={[190, 148]} />
    </>
  );
}

function SlipBobber() {
  return (
    <>
      <rect className="rig-water" x={0} y={66} width={360} height={134} />
      <path className="rig-surface" d="M0 66 q 15 -4 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0" />
      <path className="rig-line rig-draw" pathLength={1} d="M20 8 C 80 10, 150 18, 170 46" />
      <path className="rig-line" d="M170 46 L170 166" />
      <rect className="rig-stop" x={165} y={44} width={10} height={5} rx={2} />
      <circle className="rig-bead" cx={170} cy={54} r={3.5} />
      <path className="rig-float-top" d="M163 76 A7 18 0 0 1 177 76 Z" />
      <path className="rig-float-bottom" d="M163 76 A7 18 0 0 0 177 76 Z" />
      <g transform="translate(170 166)">
        <Hook kind="j" L={12} R={6} P={7} />
      </g>
      <path className="rig-worm" strokeWidth={6} d="M171 182 q 7 3 12 -6" />
      <path className="rig-arrow" d="M136 46 H124 M130 46 V166 M136 166 H124 M130 46 l-4 7 M130 46 l4 7 M130 166 l-4 -7 M130 166 l4 -7" />
      <Mark n={1} x={228} y={30} to={[176, 46]} />
      <Mark n={2} x={228} y={58} to={[175, 54]} />
      <Mark n={3} x={228} y={90} to={[178, 82]} />
      <Mark n={4} x={228} y={160} to={[180, 172]} />
      <Mark n={5} x={100} y={106} to={[128, 106]} />
    </>
  );
}

/** The plain bobber rig a first trip starts with: the bobber, one split shot, the hook. */
function BobberRig() {
  return (
    <>
      <rect className="rig-water" x={0} y={62} width={360} height={124} />
      <path className="rig-surface" d="M0 62 q 15 -4 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0 t 30 0" />
      <path className="rig-line rig-draw" pathLength={1} d="M20 8 C 80 10, 150 18, 170 50" />
      <path className="rig-line" d="M170 74 L170 146.5" />
      <path className="rig-float-top" d="M158 62 A12 12 0 0 1 182 62 Z" />
      <path className="rig-float-bottom" d="M158 62 A12 12 0 0 0 182 62 Z" />
      <circle className="rig-lead" cx={170} cy={118} r={4.5} />
      <g transform="translate(170 150)">
        <Hook kind="j" L={12} R={6} P={7} />
      </g>
      <path className="rig-worm" strokeWidth={6} d="M171 166 q 7 3 12 -6" />
      <path className="rig-arrow" d="M136 62 H124 M130 62 V166 M136 166 H124 M130 62 l-4 7 M130 62 l4 7 M130 166 l-4 -7 M130 166 l4 -7" />
      <Mark n={1} x={228} y={26} to={[163, 41]} />
      <Mark n={2} x={228} y={58} to={[183, 60]} />
      <Mark n={3} x={228} y={114} to={[175, 117]} />
      <Mark n={4} x={228} y={160} to={[184, 162]} />
      <Mark n={5} x={100} y={114} to={[128, 114]} />
    </>
  );
}

const DRAWINGS: Record<Exclude<Key, StepKey>, { viewBox: string; draw: () => ReactNode }> = {
  bottom: { viewBox: "0 0 360 130", draw: SlidingSinkerRig },
  swivel: { viewBox: "0 2 360 72", draw: SwivelAndLeader },
  sizes: { viewBox: "0 36 400 200", draw: HookSizes },
  circle: { viewBox: "0 10 360 120", draw: CircleAndJ },
  wacky: { viewBox: "0 0 360 130", draw: WackyRig },
  texas: { viewBox: "0 0 360 110", draw: TexasRig },
  ned: { viewBox: "0 0 360 120", draw: NedRig },
  dropShot: { viewBox: "0 0 360 180", draw: DropShot },
  slipBobber: { viewBox: "0 0 360 200", draw: SlipBobber },
  bobber: { viewBox: "0 0 360 184", draw: BobberRig },
};

// The drawings that answer a beginner's next question about this one ("what
// is a barrel swivel and how do I tie it on", "what is a 4/0 hook": the owner
// asked these in a row, reading the sliding sinker rig), by handbook topic.
export const RELATED: Partial<Record<Key, string[]>> = {
  bottom: ["tackle-leaders", "knot-improved-clinch", "tackle-hooks", "tackle-circle-hooks"],
  swivel: ["knot-improved-clinch"],
  wacky: ["tackle-circle-hooks", "tackle-hooks"],
  texas: ["tackle-hooks"],
  dropShot: ["tackle-hooks"],
  sizes: ["tackle-circle-hooks"],
  circle: ["tackle-hooks"],
  bobber: ["rig-slip-bobber", "tackle-split-shot"],
  slipBobber: ["tackle-bobbers"],
  palomar: ["knot-improved-clinch"],
  clinch: ["knot-palomar"],
  surgeonsLoop: ["knot-joining"],
  blood: ["tackle-leaders"],
  spincastSpool: ["knot-arbor", "trouble-line-twist"],
  spinningFill: ["knot-arbor", "tackle-new-line"],
  arbor: ["tackle-new-line"],
  castSpinning: ["technique-bite"],
  setHook: ["tackle-circle-hooks", "technique-landing"],
  landing: ["technique-drag", "care-release"],
  drag: ["technique-landing"],
  release: ["care-deep-hook"],
  deepHook: ["care-release"],
  catfishHold: ["clean-catfish"],
  worm: ["tackle-hooks"],
  splitShot: ["tackle-bobbers"],
  fillet: ["clean-catfish", "clean-scaling"],
  catfishSkin: ["safe-handling", "clean-fillet"],
};

function isStep(key: Key): key is StepKey {
  return key in STEP_DRAWINGS;
}

/** A drawing of numbered parts with the list of what each number is. */
function PartsDrawing({ k, topic }: { k: Exclude<Key, StepKey>; topic: string }) {
  const words = useT().rigs[k];
  const { viewBox, draw: Draw } = DRAWINGS[k];
  const titleId = `rig-${topic}-${k}-title`;
  return (
    <figure className="rig" aria-labelledby={titleId}>
      <svg viewBox={viewBox} role="img" aria-labelledby={titleId}>
        <title id={titleId}>{words.title}</title>
        <Draw />
      </svg>
      <ol>
        {words.parts.map((part, i) => (
          <li key={part}>
            <b aria-hidden="true">{i + 1}</b>
            <span>
              <LinkedText text={part} skipTopic={topic} earlier={words.parts.slice(0, i)} />
            </span>
          </li>
        ))}
      </ol>
      {words.note && (
        <figcaption>
          <LinkedText text={words.note} skipTopic={topic} earlier={words.parts} />
        </figcaption>
      )}
    </figure>
  );
}

/** A drawing a step at a time: each step its words, then its own picture. */
function StepsDrawing({ k, topic }: { k: StepKey; topic: string }) {
  const words = useT().rigs[k];
  const steps = STEP_DRAWINGS[k];
  const titleId = `rig-${topic}-${k}-title`;
  return (
    <figure className="rig rig-steps" aria-labelledby={titleId}>
      <p id={titleId} className="rig-steps-title">
        {words.title}
      </p>
      <ol>
        {steps.map((Draw, i) => (
          <li key={i} style={{ "--i": i } as React.CSSProperties}>
            <p>
              <b aria-hidden="true">{i + 1}</b>
              <span>
                <LinkedText text={words.parts[i]} skipTopic={topic} earlier={words.parts.slice(0, i)} />
              </span>
            </p>
            <svg viewBox="0 0 160 120" aria-hidden="true">
              <Draw />
            </svg>
          </li>
        ))}
      </ol>
      {words.note && (
        <figcaption>
          <LinkedText text={words.note} skipTopic={topic} earlier={words.parts} />
        </figcaption>
      )}
    </figure>
  );
}

export function RigDiagram({ topic }: { topic: string }) {
  const all = useT();
  const rigs = all.rigs;
  const keys = rigKeys(topic);
  if (keys.length === 0) return null;
  const related = keys.flatMap((k) => RELATED[k] ?? []);
  return (
    <>
      {keys.map((k) => (isStep(k) ? <StepsDrawing key={k} k={k} topic={topic} /> : <PartsDrawing key={k} k={k} topic={topic} />))}
      {related.length > 0 && (
        <p className="rig-related">
          <span>{all.fish.rigRelated}</span>
          {related.map((id) => (
            // A plain link: the handbook hears the hash change and opens that chapter.
            <a key={id} href={`#${id}`}>
              {rigs[rigKeys(id)[0]].title}
            </a>
          ))}
        </p>
      )}
    </>
  );
}
