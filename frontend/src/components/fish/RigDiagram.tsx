"use client";

import type { ReactNode } from "react";

import { useT } from "@/i18n/client";

import { RIG_DIAGRAMS, type RigKey } from "./rigTopics";

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

/** A numbered mark, with a thin line to what it names. */
function Mark({ n, x, y, to }: { n: number; x: number; y: number; to?: [number, number] }) {
  return (
    <g className="rig-mark">
      {to && <line className="rig-tick" x1={x} y1={y} x2={to[0]} y2={to[1]} />}
      <circle cx={x} cy={y} r={11} />
      <text x={x} y={y}>
        {n}
      </text>
    </g>
  );
}

/**
 * A hook in its own units: the eye at (0, 0), the shank down the y axis, the
 * bend opening upward. A J hook's point stands parallel to the shank; a
 * circle hook's turns back toward it. The caller places and turns it; the
 * stroke stays the same width however it is scaled.
 */
function Hook({ kind, L, R, P }: { kind: "j" | "circle"; L: number; R: number; P: number }) {
  let d: string;
  let barb: string;
  if (kind === "j") {
    d = `M0 3.5 L0 ${L} A${R} ${R} 0 0 0 ${2 * R} ${L} L${2 * R} ${L - P}`;
    barb = `M${2 * R} ${L - P + 2} l${-3.5} ${5}`;
  } else {
    const ex = 1.5 * R;
    const ey = L - 0.866 * R;
    const tx = ex - 0.866 * P;
    const ty = ey - 0.5 * P;
    d = `M0 3.5 L0 ${L} A${R} ${R} 0 1 0 ${ex} ${ey} L${tx} ${ty}`;
    barb = `M${tx + 1.7} ${ty + 1} l${-2} ${4.5}`;
  }
  return (
    <g className="rig-metal">
      <circle cx={0} cy={0} r={3.5} vectorEffect="non-scaling-stroke" />
      <path d={d} vectorEffect="non-scaling-stroke" />
      <path d={barb} vectorEffect="non-scaling-stroke" />
    </g>
  );
}

/** A barrel swivel lying along the line, starting at x: 44 units long, or 92 when big. */
function Swivel({ x, y, big = false }: { x: number; y: number; big?: boolean }) {
  const r = big ? 8 : 5;
  const len = big ? 60 : 24;
  const h = big ? 20 : 12;
  const left = x + r;
  const body = left + r;
  const right = body + len + r;
  return (
    <g>
      <circle className="rig-metal" cx={left} cy={y} r={r} />
      <rect className="rig-swivel-body" x={body} y={y - h / 2} width={len} height={h} rx={h / 2} />
      <path className="rig-metal-thin" d={`M${body + len / 3} ${y - h / 2} v${h} M${body + (2 * len) / 3} ${y - h / 2} v${h}`} />
      <circle className="rig-metal" cx={right} cy={y} r={r} />
    </g>
  );
}

/** A knot's wraps beside an eye, from x0 to x1 along y. */
function Wraps({ x0, x1, y, lean = 1 }: { x0: number; x1: number; y: number; lean?: 1 | -1 }) {
  const n = 5;
  const step = (x1 - x0) / (n - 1);
  const d = Array.from({ length: n }, (_, i) => `M${x0 + i * step - 2 * lean} ${y - 7} l${4 * lean} 14`).join(" ");
  return <path className="rig-wraps" d={d} />;
}

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

/** One panel of the clinch knot, its eye at (ox + 16, 64). */
function Eye({ ox }: { ox: number }) {
  return (
    <>
      <path className="rig-metal" d={`M${ox + 2} 64 H${ox + 8}`} />
      <circle className="rig-metal" cx={ox + 16} cy={64} r={8} />
    </>
  );
}

function ClinchKnot() {
  const through = (ox: number) => `M${ox + 86} 60 H${ox + 18} Q${ox + 10} 64 ${ox + 18} 68`;
  const wraps = (ox: number) =>
    `L${ox + 27} 68 L${ox + 31} 54 L${ox + 36} 68 L${ox + 40} 54 L${ox + 45} 68 L${ox + 49} 54 L${ox + 54} 68 L${ox + 58} 54 L${ox + 63} 68 L${ox + 67} 54`;
  return (
    <>
      {[90, 180, 270].map((x) => (
        <line key={x} className="rig-divider" x1={x} y1={28} x2={x} y2={112} />
      ))}
      {/* 1: through the eye, the tag end back beside the line */}
      <Eye ox={0} />
      <path className="rig-line" d={`${through(0)} H70`} />
      {/* 2: the tag end wrapped round the line */}
      <Eye ox={90} />
      <path className="rig-line" d={`${through(90)} ${wraps(90)} L${90 + 76} 46`} />
      {/* 3: back through the small loop by the eye, then the big loop */}
      <Eye ox={180} />
      <path className="rig-line" d={`${through(180)} ${wraps(180)} C${180 + 80} 34 ${180 + 34} 36 ${180 + 24} 62`} />
      <path className="rig-arrow" d={`M${180 + 24} 62 l-1 -7 M${180 + 24} 62 l6 -4`} />
      <path className="rig-arrow rig-dashed" d={`M${180 + 26} 70 C${180 + 40} 92 ${180 + 70} 92 ${180 + 80} 78`} />
      <path className="rig-arrow" d={`M${180 + 80} 78 l-7 1 M${180 + 80} 78 l-1 7`} />
      {/* 4: pulled snug, the tag end trimmed */}
      <Eye ox={270} />
      <path className="rig-line" d={`M${270 + 86} 62 H${270 + 18}`} />
      <Wraps x0={270 + 28} x1={270 + 44} y={62} />
      <path className="rig-line" d={`M${270 + 46} 57 l5 -5`} />
      <Mark n={1} x={45} y={18} />
      <Mark n={2} x={135} y={18} />
      <Mark n={3} x={225} y={18} />
      <Mark n={4} x={315} y={18} />
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

/** A reel's spool seen face on, centred at (ox + 26, 64). */
function Spool({ ox }: { ox: number }) {
  return (
    <>
      <circle className="rig-spool" cx={ox + 26} cy={64} r={22} />
      <circle className="rig-spool-hub" cx={ox + 26} cy={64} r={9} />
    </>
  );
}

function ArborKnot() {
  // In along the top of the hub, round it, and the tag end out along the bottom.
  const wrap = (ox: number) => `M${ox + 86} 52 H${ox + 26} A12 12 0 1 0 ${ox + 26} 76`;
  const overhand = (ox: number) => `H${ox + 52} C ${ox + 62} 76, ${ox + 66} 44, ${ox + 58} 44 C ${ox + 50} 44, ${ox + 54} 62, ${ox + 70} 62`;
  return (
    <>
      {[90, 180, 270].map((x) => (
        <line key={x} className="rig-divider" x1={x} y1={28} x2={x} y2={112} />
      ))}
      {/* 1: round the spool, the tag end beside the main line */}
      <Spool ox={0} />
      <path className="rig-line" d={`${wrap(0)} H70`} />
      {/* 2: the tag end knotted round the main line */}
      <Spool ox={90} />
      <path className="rig-line" d={`${wrap(90)} ${overhand(90)}`} />
      {/* 3: a stopper knot at the tip */}
      <Spool ox={180} />
      <path className="rig-line" d={`${wrap(180)} ${overhand(180)}`} />
      <circle className="rig-knot" cx={180 + 71} cy={62} r={3} />
      {/* 4: the main line pulled, the knot snug on the spool */}
      <Spool ox={270} />
      <path className="rig-line" d={`${wrap(270)} H${270 + 33}`} />
      <circle className="rig-knot" cx={270 + 38} cy={55} r={3.2} />
      <path className="rig-arrow" d={`M${270 + 58} 40 H${270 + 82} M${270 + 82} 40 l-6 -4 M${270 + 82} 40 l-6 4`} />
      <Mark n={1} x={45} y={18} />
      <Mark n={2} x={135} y={18} />
      <Mark n={3} x={225} y={18} />
      <Mark n={4} x={315} y={18} />
    </>
  );
}

const DRAWINGS: Record<Key, { viewBox: string; draw: () => ReactNode }> = {
  bottom: { viewBox: "0 0 360 130", draw: SlidingSinkerRig },
  swivel: { viewBox: "0 2 360 72", draw: SwivelAndLeader },
  clinch: { viewBox: "0 0 360 120", draw: ClinchKnot },
  sizes: { viewBox: "0 36 400 200", draw: HookSizes },
  circle: { viewBox: "0 10 360 120", draw: CircleAndJ },
  wacky: { viewBox: "0 0 360 130", draw: WackyRig },
  texas: { viewBox: "0 0 360 110", draw: TexasRig },
  ned: { viewBox: "0 0 360 120", draw: NedRig },
  dropShot: { viewBox: "0 0 360 180", draw: DropShot },
  slipBobber: { viewBox: "0 0 360 200", draw: SlipBobber },
  bobber: { viewBox: "0 0 360 184", draw: BobberRig },
  arbor: { viewBox: "0 4 360 112", draw: ArborKnot },
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
  bobber: ["rig-slip-bobber"],
  slipBobber: ["tackle-bobbers"],
};

export function RigDiagram({ topic }: { topic: string }) {
  const all = useT();
  const rigs = all.rigs;
  const key = RIG_DIAGRAMS[topic];
  if (!key) return null;
  const words = rigs[key];
  const { viewBox, draw: Draw } = DRAWINGS[key];
  const titleId = `rig-${topic}-title`;
  const related = RELATED[key];
  return (
    <>
      <figure className="rig" aria-labelledby={titleId}>
        <svg viewBox={viewBox} role="img" aria-labelledby={titleId}>
          <title id={titleId}>{words.title}</title>
          <Draw />
        </svg>
        <ol>
          {words.parts.map((part, i) => (
            <li key={part}>
              <b aria-hidden="true">{i + 1}</b>
              <span>{part}</span>
            </li>
          ))}
        </ol>
        {words.note && <figcaption>{words.note}</figcaption>}
      </figure>
      {related && (
        <p className="rig-related">
          <span>{all.fish.rigRelated}</span>
          {related.map((id) => (
            // A plain link: the handbook hears the hash change and opens that chapter.
            <a key={id} href={`#${id}`}>
              {rigs[RIG_DIAGRAMS[id]].title}
            </a>
          ))}
        </p>
      )}
    </>
  );
}
