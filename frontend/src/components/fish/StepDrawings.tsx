import type { ReactNode } from "react";

import {
  Arrow,
  Baitcaster,
  Finger,
  FishShape,
  Hand,
  Hook,
  Knife,
  KnotHook,
  No,
  Person,
  Rod,
  SpincastReel,
  SpinningReel,
  Spool,
  Wraps,
  Yes,
} from "./rigParts";

/**
 * Drawings that show how to do something, a step at a time: tying a knot,
 * putting line on a reel, casting, setting the hook, landing and releasing a
 * fish, hooking a bait, cleaning a catch (added 2026-11-16: the owner asked
 * for a drawing wherever the handbook teaches a knot, a threading or a
 * movement). Each step is its own small picture (160 × 120) with its
 * caption under it, from messages `rigs.<key>.parts`, in the order of the
 * topic's own text (backend angling_handbook.py). The part the reader moves
 * is drawn in the brand colour; a movement is an animated dashed arrow.
 */

export type Step = () => ReactNode;

/** Doubled line: two strands side by side, drawn as one path. */
function Double({ d, work = false }: { d: string; work?: boolean }) {
  return (
    <g>
      <path className={work ? "rig-double rig-double-work" : "rig-double"} d={d} />
      <path className="rig-double-in" d={d} />
    </g>
  );
}

function Water({ y = 50, h = 70 }: { y?: number; h?: number }) {
  return (
    <>
      <rect className="rig-water" x={0} y={y} width={160} height={h} />
      <path className="rig-surface" d={`M0 ${y} q 10 -3 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0`} />
    </>
  );
}

function Bobber({ x, y, under = false }: { x: number; y: number; under?: boolean }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <path className="rig-float-top" d="M-7 0 A7 7 0 0 1 7 0 Z" />
      <path className="rig-float-bottom" d="M-7 0 A7 7 0 0 0 7 0 Z" />
      {under && <path className="rig-arrow" d="M-12 -12 l4 4 M12 -12 l-4 4 M0 -16 v5" />}
    </g>
  );
}

function Label({ x, y, children, anchor = "middle" }: { x: number; y: number; children: ReactNode; anchor?: "start" | "middle" | "end" }) {
  return (
    <text className="rig-label" x={x} y={y} textAnchor={anchor}>
      {children}
    </text>
  );
}

function Pliers({ x, y, deg = 0 }: { x: number; y: number; deg?: number }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${deg})`}>
      <path className="rig-pliers" d="M0 -2 L-26 -9 M0 2 L-26 9" />
      <path className="rig-pliers-jaw" d="M0 -2 L14 -1 M0 2 L14 1" />
      <circle className="rig-knob" cx={0} cy={0} r={2.2} />
    </g>
  );
}

// ---------------------------------------------------------------- knots

const palomar: Step[] = [
  () => (
    <>
      <Double work d="M156 22 H18" />
      <KnotHook x={44} y={22} />
      <Arrow motion d="M92 42 H58" at={[58, 42]} deg={180} />
      <Label x={120} y={42}>4–6″</Label>
    </>
  ),
  () => (
    <>
      <Double d="M156 22 H44" />
      <Double work d="M44 22 C22 22 14 44 34 50 C58 58 92 50 90 34 C88 20 70 20 70 32 C70 46 96 64 124 70" />
      <KnotHook x={44} y={22} />
    </>
  ),
  () => (
    <>
      <Double d="M156 22 H44" />
      <Double work d="M44 22 C22 22 14 44 34 50 C58 58 92 50 90 34 C88 20 70 20 70 32 C70 46 96 64 124 70" />
      <KnotHook x={44} y={22} />
      <Arrow motion d="M126 76 C112 112 40 116 30 92" at={[30, 92]} deg={-110} />
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M156 22 H52" />
      <ellipse className="rig-knotblob" cx={54} cy={22} rx={6} ry={5} />
      <path className="rig-line" d="M57 26 l6 6" />
      <KnotHook x={44} y={22} />
      <Arrow d="M110 36 H150" at={[150, 36]} deg={0} />
      <Yes x={120} y={78} />
    </>
  ),
];

const surgeonsLoop: Step[] = [
  () => (
    <>
      <path className="rig-line" d="M156 56 H112" />
      <Double work d="M112 56 H26" />
      <path className="rig-line" d="M112 59 l10 10" />
      <Arrow d="M30 84 H108 M30 84 l5 -4 M30 84 l5 4" at={[108, 84]} deg={0} />
      <Label x={70} y={102}>1–2″</Label>
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M156 56 H128" />
      <Double work d="M128 56 H98 C74 56 66 26 86 24 C104 22 104 52 86 60 C70 66 48 64 26 64" />
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M156 56 H128" />
      <Double work d="M128 56 H98 C74 56 66 26 86 24 C104 22 104 52 86 60 C70 66 48 64 26 64" />
      <Arrow motion d="M26 74 C40 100 92 98 88 42" at={[88, 42]} deg={-90} />
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M156 56 H100" />
      <ellipse className="rig-knotblob" cx={96} cy={56} rx={7} ry={6} />
      <path className="rig-line rig-work" d="M90 54 C66 38 30 42 26 56 C30 70 66 74 90 58" />
      <path className="rig-line" d="M100 60 l6 7" />
      <Arrow d="M112 40 H146" at={[146, 40]} deg={0} />
      <Arrow d="M60 30 H24" at={[24, 30]} deg={180} />
    </>
  ),
];

const blood: Step[] = [
  () => (
    <>
      <path className="rig-line" d="M4 54 H112" />
      <path className="rig-leader" d="M156 66 H48" />
      <Arrow d="M48 88 H112 M48 88 l5 -4 M48 88 l5 4" at={[112, 88]} deg={0} />
      <Label x={80} y={106}>2″</Label>
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M4 58 H80" />
      <path className="rig-leader" d="M156 62 H48" />
      <path className="rig-work-line" d="M80 58 C84 50 88 50 90 60 C92 70 96 70 98 58 C100 48 104 48 106 60 C108 70 112 70 114 58 C116 48 120 48 122 60 C124 70 128 70 130 58" />
      <Arrow motion d="M130 58 C134 30 92 30 82 54" at={[82, 54]} deg={110} />
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M4 58 H80" />
      <path className="rig-leader" d="M156 62 H80" />
      <path className="rig-wraps" d="M84 52 l4 14 M92 52 l4 14 M100 52 l4 14 M108 52 l4 14 M116 52 l4 14" />
      <path className="rig-work-line rig-leader-work" d="M80 62 C76 70 72 70 70 60 C68 50 64 50 62 60 C60 70 56 70 54 60 C52 50 48 50 46 60 C44 70 40 70 38 60" />
      <Arrow motion d="M38 60 C30 92 74 96 80 66" at={[80, 66]} deg={-80} />
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M4 60 H66" />
      <path className="rig-leader" d="M94 60 H156" />
      <Wraps x0={66} x1={78} y={60} n={5} h={6} />
      <Wraps x0={82} x1={94} y={60} n={5} h={6} lean={-1} className="rig-wraps rig-wraps-leader" />
      <path className="rig-line" d="M80 54 l-3 -8" />
      <path className="rig-leader" d="M80 66 l3 8" />
      <Arrow d="M40 36 H8" at={[8, 36]} deg={180} />
      <Arrow d="M120 36 H152" at={[152, 36]} deg={0} />
    </>
  ),
];

const surgeonsKnot: Step[] = [
  () => (
    <>
      <path className="rig-line" d="M4 54 H130" />
      <path className="rig-leader" d="M156 62 H30" />
      <Arrow d="M30 88 H130 M30 88 l5 -4 M30 88 l5 4" at={[130, 88]} deg={0} />
      <Label x={80} y={106}>6″</Label>
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M4 56 H60" />
      <path className="rig-leader" d="M156 62 H112" />
      <Double work d="M60 58 H70 C92 58 98 26 80 24 C62 22 60 52 82 62 C96 68 104 62 112 60" />
      <Double d="M112 60 H130" />
      <Double d="M60 58 H40" />
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M4 58 H70" />
      <path className="rig-leader" d="M90 58 H156" />
      <ellipse className="rig-knotblob" cx={80} cy={58} rx={10} ry={6} />
      <path className="rig-line" d="M84 52 l5 -9" />
      <path className="rig-leader" d="M76 64 l-5 9" />
      <Arrow d="M40 34 H8" at={[8, 34]} deg={180} />
      <Arrow d="M120 34 H152" at={[152, 34]} deg={0} />
      <Yes x={80} y={96} />
    </>
  ),
];

// ------------------------------------------------------- line on a reel

const spincastSpool: Step[] = [
  () => (
    <>
      <Rod from={[4, 96]} to={[156, 96]} handle={0.3} />
      <rect className="rig-reel" x={30} y={50} width={40} height={38} rx={8} />
      <path className="rig-reel" d="M44 88 h12 v8 h-12 z" />
      <circle className="rig-spool-side" cx={72} cy={69} r={11} />
      <path className="rig-line rig-old" d="M80 64 c8 -6 14 4 8 10 c-6 6 4 12 10 8" />
      <path className="rig-cover" d="M96 50 h14 l30 14 v10 l-30 14 h-14 z" />
      <circle className="rig-hole-dot" cx={140} cy={69} r={2.5} />
      <Arrow motion d="M104 40 C116 32 128 38 130 48" at={[130, 48]} deg={80} />
      <Arrow d="M84 30 H122" at={[122, 30]} deg={0} />
    </>
  ),
  () => (
    <>
      <path className="rig-cover" d="M40 50 h20 l36 18 v8 l-36 18 h-20 z" />
      <circle className="rig-hole-dot" cx={96} cy={72} r={3} />
      <path className="rig-line rig-work" d="M156 72 H96" />
      <path className="rig-line rig-work rig-hidden-line" d="M96 72 H44" />
      <path className="rig-line rig-work" d="M44 72 C30 72 24 80 20 92" />
      <Arrow motion d="M150 56 H116" at={[116, 56]} deg={180} />
    </>
  ),
  () => (
    <>
      <Spool cx={62} cy={62} r={30} />
      <path className="rig-line rig-work" d="M156 44 H62 A12 12 0 1 0 62 74 H90" />
      <ellipse className="rig-knotblob" cx={70} cy={50} rx={5} ry={4} />
      <path className="rig-cover rig-ghost" d="M118 76 h8 l20 10 v4 l-20 10 h-8 z" />
      <Arrow motion d="M118 104 C104 110 98 100 98 92" at={[98, 92]} deg={-90} />
    </>
  ),
  () => (
    <>
      <Rod from={[18, 40]} to={[156, 18]} />
      <SpincastReel x={52} y={34} />
      <rect className="rig-filler" x={60} y={92} width={34} height={20} rx={4} />
      <ellipse className="rig-filler-top" cx={77} cy={92} rx={17} ry={5} />
      <path className="rig-line rig-work" d="M77 92 C77 72 74 58 70 46" />
      <Finger x={60} y={66} deg={-10} len={18} w={7} />
      <Arrow motion d="M28 22 C20 30 24 40 32 42" at={[32, 42]} deg={20} />
    </>
  ),
];

const spinningFill: Step[] = [
  () => (
    <>
      <Rod from={[10, 30]} to={[156, 30]} />
      <SpinningReel x={58} y={30} open />
      <path className="rig-line rig-work" d="M156 30 C120 36 80 52 48 50" />
      <ellipse className="rig-knotblob" cx={47} cy={50} rx={3.5} ry={3} />
      <Label x={40} y={92} anchor="start">⟳</Label>
    </>
  ),
  () => (
    <>
      <Rod from={[10, 30]} to={[156, 30]} />
      <SpinningReel x={58} y={30} />
      <path className="rig-line rig-work" d="M112 30 C112 60 118 84 120 108" />
      <Finger x={100} y={60} deg={0} len={14} w={7} />
      <Finger x={126} y={64} deg={180} len={14} w={7} />
      <Arrow motion d="M84 70 C78 82 70 82 66 74" at={[66, 74]} deg={-120} />
    </>
  ),
  () => (
    <>
      <rect className="rig-reel" x={44} y={40} width={78} height={40} rx={3} />
      <rect className="rig-spool-fill" x={48} y={28} width={70} height={64} rx={4} />
      <path className="rig-wraps" d="M56 28 v64 M66 28 v64 M76 28 v64 M86 28 v64 M96 28 v64 M106 28 v64" />
      <path className="rig-spool-lip" d="M40 16 C34 16 34 104 40 104 h8 C42 104 42 16 48 16 Z" />
      <path className="rig-arrow" d="M30 16 v12 M26 16 h8 M26 28 h8" />
      <Label x={24} y={26} anchor="end">⅛″</Label>
      <rect className="rig-reel" x={122} y={50} width={30} height={20} rx={4} />
      <Yes x={134} y={104} />
    </>
  ),
];

// --------------------------------------------------------------- casting

const castSpinning: Step[] = [
  () => (
    <>
      <Rod from={[14, 46]} to={[124, 34]} />
      <SpinningReel x={44} y={43} />
      <path className="rig-line" d="M124 34 V88" />
      <ellipse className="rig-lure" cx={124} cy={93} rx={4} ry={6} />
      <Arrow d="M140 34 V90 M140 34 l-3 6 M140 34 l3 6" at={[140, 90]} deg={90} />
      <Label x={116} y={70} anchor="end">10–18″</Label>
    </>
  ),
  () => (
    <>
      <Rod from={[4, 30]} to={[156, 30]} handle={0.3} />
      <g transform="translate(70 30) scale(2)">
        <SpinningReel x={0} y={0} open />
      </g>
      <path className="rig-line" d="M156 30 L66 35 C54 37 48 44 47 54" />
      <Finger x={30} y={44} deg={-14} len={34} w={11} />
      <Arrow motion d="M30 96 C20 88 22 72 32 64" at={[32, 64]} deg={-60} />
    </>
  ),
  () => (
    <>
      <Person x={60} y={114} arm={[70, 64]} arm2={[64, 52]} />
      <g className="rig-ghost">
        <Rod from={[70, 66]} to={[150, 56]} />
      </g>
      <Rod from={[70, 66]} to={[40, 6]} />
      <Arrow motion d="M140 46 C130 18 100 6 60 8" at={[60, 8]} deg={180} />
    </>
  ),
  () => (
    <>
      <Person x={44} y={114} arm={[54, 64]} arm2={[70, 56]} />
      <Rod from={[54, 66]} to={[124, 22]} />
      <circle className="rig-release" cx={98} cy={38} r={5} />
      <path className="rig-line" d="M124 22 C136 16 146 22 156 34" />
      <Arrow motion d="M50 18 C70 8 92 10 110 22" at={[110, 22]} deg={35} />
    </>
  ),
];

const castBaitcast: Step[] = [
  () => (
    <>
      <Rod from={[10, 58]} to={[126, 44]} />
      <Baitcaster x={42} y={55} />
      <Finger x={30} y={34} deg={10} len={18} w={8} />
      <path className="rig-line" d="M126 44 V80" />
      <ellipse className="rig-lure" cx={126} cy={85} rx={4} ry={6} />
      <Arrow d="M142 44 V82 M142 44 l-3 6 M142 44 l3 6" at={[142, 82]} deg={90} />
      <Label x={118} y={70} anchor="end">8–10″</Label>
    </>
  ),
  () => (
    <>
      <Rod from={[10, 70]} to={[156, 56]} />
      <Baitcaster x={70} y={66} />
      <Finger x={56} y={40} deg={14} len={20} w={9} />
      <Arrow motion d="M64 22 V36" at={[64, 36]} deg={90} />
      <path className="rig-spool-hold" d="M62 52 h16" />
    </>
  ),
  () => (
    <>
      <Person x={44} y={114} arm={[54, 64]} arm2={[70, 56]} />
      <Rod from={[54, 66]} to={[124, 22]} />
      <Finger x={60} y={52} deg={-60} len={14} w={7} />
      <Arrow motion d="M50 18 C70 8 92 10 110 22" at={[110, 22]} deg={35} />
      <path className="rig-line" d="M124 22 C136 16 146 22 156 34" />
    </>
  ),
  () => (
    <>
      <Water y={70} h={50} />
      <path className="rig-line" d="M4 20 C60 10 110 30 128 68" />
      <path className="rig-splash" d="M120 66 l-6 -8 M128 64 v-10 M136 66 l6 -8" />
      <Baitcaster x={34} y={44} />
      <Finger x={22} y={26} deg={20} len={16} w={8} />
      <Arrow motion d="M28 6 V18" at={[28, 18]} deg={90} />
    </>
  ),
];

// ---------------------------------------------------------- the drag

const drag: Step[] = [
  () => (
    <>
      <g transform="translate(30 30)">
        <SpinningReel x={0} y={0} />
        <circle className="rig-hot" cx={-12} cy={16} r={5} />
      </g>
      <g transform="translate(78 64)">
        <SpincastReel x={0} y={0} />
        <circle className="rig-hot" cx={0} cy={-18} r={5} />
      </g>
      <g transform="translate(124 100)">
        <Baitcaster x={0} y={0} />
        <circle className="rig-hot" cx={20} cy={-9} r={5} />
      </g>
    </>
  ),
  () => (
    <>
      <circle className="rig-reel" cx={80} cy={60} r={26} />
      <path className="rig-knob-ridges" d="M80 34 v8 M80 78 v8 M54 60 h8 M98 60 h8" />
      <Arrow motion d="M58 26 A40 40 0 0 1 102 26" at={[102, 26]} deg={30} />
      <Arrow motion d="M58 94 A40 40 0 0 0 102 94" at={[58, 94]} deg={150} />
      <Label x={124} y={26} anchor="start">+</Label>
      <Label x={36} y={100} anchor="end">−</Label>
    </>
  ),
  () => (
    <>
      <Rod from={[10, 96]} to={[156, 86]} />
      <SpinningReel x={52} y={93} />
      <path className="rig-line rig-work" d="M40 106 C40 70 44 40 48 20" />
      <Finger x={42} y={16} deg={-90} len={14} w={8} />
      <Arrow motion d="M68 50 V18" at={[68, 18]} deg={-90} />
    </>
  ),
  () => (
    <>
      <path className="rig-metal-thin" d="M36 4 V12" />
      <path className="rig-scale" d="M20 12 h32 v54 h-32 z" />
      <path className="rig-metal-thin" d="M28 24 h16 M28 34 h16 M28 44 h16 M28 54 h16" />
      <path className="rig-move-path rig-trail" d="M30 39 h12" />
      <path className="rig-line rig-work" d="M36 66 V112" />
      <Label x={64} y={36} anchor="start">⅓–½</Label>
      <Label x={64} y={60} anchor="start">20 lb →</Label>
      <Label x={64} y={80} anchor="start">7–10 lb</Label>
    </>
  ),
];

// ----------------------------------------------------- setting the hook

const setHook: Step[] = [
  () => (
    <>
      <Water y={60} h={60} />
      <Rod from={[6, 30]} to={[60, 18]} />
      <path className="rig-line rig-slack rig-ghost" d="M60 18 C90 70 110 30 120 60" />
      <path className="rig-line" d="M60 18 L120 58" />
      <Bobber x={120} y={60} />
      <Arrow motion d="M40 46 C34 54 26 54 22 46" at={[22, 46]} deg={-150} />
    </>
  ),
  () => (
    <>
      <Water y={50} h={70} />
      <path className="rig-line" d="M30 10 L90 64" />
      <Bobber x={92} y={70} under />
      <path className="rig-line" d="M92 77 V96" />
      <FishShape x={84} y={102} len={44} flip />
    </>
  ),
  () => (
    <>
      <Water y={80} h={40} />
      <g className="rig-ghost">
        <Rod from={[20, 76]} to={[130, 56]} />
      </g>
      <Rod from={[20, 76]} to={[96, 4]} />
      <path className="rig-line" d="M96 4 L150 84" />
      <Arrow motion d="M138 48 C130 20 116 10 104 8" at={[104, 8]} deg={-170} />
    </>
  ),
  () => (
    <>
      <Water y={80} h={40} />
      <Rod from={[20, 76]} to={[130, 56]} />
      <path className="rig-line" d="M130 56 L150 90" />
      <No x={100} y={22} />
      <Arrow motion d="M44 100 A12 12 0 1 0 44 99" at={[44, 99]} deg={180} />
      <g transform="translate(128 98) rotate(-90) scale(0.55)">
        <Hook kind="circle" L={22} R={12} P={8} />
      </g>
    </>
  ),
];

// ------------------------------------------------- playing and landing

const landing: Step[] = [
  () => (
    <>
      <Water y={80} h={40} />
      <path className="rig-rod" d="M16 100 Q60 20 112 34" />
      <path className="rig-handle" d="M16 100 l10 -22" />
      <path className="rig-line" d="M112 34 L128 98" />
      <FishShape x={128} y={98} len={30} flip />
      <Yes x={60} y={18} />
    </>
  ),
  () => (
    <>
      <Water y={70} h={50} />
      <Rod from={[14, 90]} to={[90, 30]} />
      <SpinningReel x={34} y={74} />
      <path className="rig-line" d="M90 30 L122 98" />
      <FishShape x={122} y={98} len={28} />
      <Arrow motion d="M126 112 H156" at={[156, 112]} deg={0} />
      <No x={56} y={104} />
    </>
  ),
  () => (
    <>
      <Water y={84} h={36} />
      <g className="rig-ghost">
        <Rod from={[14, 96]} to={[120, 52]} />
      </g>
      <Rod from={[14, 96]} to={[86, 8]} />
      <path className="rig-line" d="M86 8 L146 92" />
      <Arrow motion d="M118 44 C112 26 102 14 92 10" at={[92, 10]} deg={-150} />
      <Arrow motion d="M60 30 C80 40 96 52 104 62" at={[104, 62]} deg={50} />
    </>
  ),
  () => (
    <>
      <Water y={52} h={68} />
      <path className="rig-net" d="M86 70 C86 104 140 104 140 70 Z" />
      <path className="rig-handle" d="M140 70 L156 30" />
      <FishShape x={56} y={78} len={40} flip />
      <path className="rig-line" d="M56 78 L20 10" />
      <Arrow motion d="M60 96 H92" at={[92, 96]} deg={0} />
    </>
  ),
];

// ----------------------------------------------- caring for the fish

const release: Step[] = [
  () => (
    <>
      <FishShape x={40} y={60} len={80} />
      <Hand x={2} y={74} scale={0.75} />
      <Finger x={20} y={62} deg={-8} len={24} w={8} />
    </>
  ),
  () => (
    <>
      <FishShape x={20} y={58} len={120} />
      <Hand x={38} y={86} scale={0.8} />
      <Hand x={96} y={84} scale={0.8} />
      <Arrow d="M54 116 V104" at={[54, 104]} deg={-90} size={5} />
      <Arrow d="M112 116 V102" at={[112, 102]} deg={-90} size={5} />
    </>
  ),
  () => (
    <>
      <Water y={30} h={90} />
      <FishShape x={60} y={72} len={90} />
      <g transform="translate(34 72) rotate(-90) scale(0.8)">
        <Hook kind="j" L={26} R={8} P={10} />
      </g>
      <Pliers x={30} y={60} deg={-120} />
      <Arrow motion d="M24 92 C14 92 10 84 12 76" at={[12, 76]} deg={-100} />
    </>
  ),
  () => (
    <>
      <Water y={20} h={100} />
      <path className="rig-current" d="M8 40 H40 M8 100 H36 M120 32 H152 M126 104 H156" />
      <path className="rig-arrow" d="M40 40 l-6 -4 M40 40 l-6 4" />
      <FishShape x={44} y={70} len={90} />
      <Hand x={70} y={92} scale={0.7} />
      <Hand x={110} y={88} scale={0.6} />
    </>
  ),
];

const deepHook: Step[] = [
  () => (
    <>
      <FishShape x={60} y={64} len={90} />
      <path className="rig-line" d="M4 30 L60 62" />
      <path className="rig-cut" d="M44 44 l12 12 M56 44 l-12 12" />
      <Label x={50} y={34}>✂</Label>
    </>
  ),
  () => (
    <>
      <g transform="translate(70 30)">
        <Hook kind="j" L={40} R={12} P={16} />
      </g>
      <Pliers x={70} y={56} deg={180} />
      <Arrow motion d="M118 70 C130 50 124 30 104 24" at={[104, 24]} deg={-160} />
      <path className="rig-line" d="M70 26 L30 6" />
    </>
  ),
  () => (
    <>
      <g transform="translate(60 26) scale(1.6)">
        <Hook kind="j" L={30} R={10} P={14} />
      </g>
      <circle className="rig-hot" cx={92} cy={50} r={9} />
      <Pliers x={118} y={50} deg={180} />
    </>
  ),
];

const snag: Step[] = [
  () => (
    <>
      <Water y={64} h={56} />
      <path className="rig-rock" d="M110 120 C110 98 130 88 150 96 L160 120 Z" />
      <Rod from={[14, 90]} to={[70, 10]} />
      <path className="rig-line" d="M70 10 L132 98" />
      <Arrow motion d="M84 6 l-8 8 l8 8 l-8 8" at={[76, 30]} deg={135} />
    </>
  ),
  () => (
    <>
      <Water y={92} h={28} />
      <rect className="rig-bank" x={0} y={80} width={160} height={12} />
      <path className="rig-rock" d="M60 120 C60 106 80 100 100 104 L110 120 Z" />
      <g className="rig-ghost">
        <Person x={30} y={82} arm={[42, 50]} />
      </g>
      <Person x={130} y={82} arm={[118, 50]} />
      <path className="rig-line" d="M118 50 L84 106" />
      <Arrow motion d="M46 68 H112" at={[112, 68]} deg={0} />
    </>
  ),
  () => (
    <>
      <Water y={70} h={50} />
      <path className="rig-rock" d="M120 120 C120 100 140 92 160 98 L160 120 Z" />
      <Hand x={30} y={50} scale={0.8} />
      <path className="rig-line rig-work" d="M44 42 c4 4 4 12 0 16 M50 42 c4 4 4 12 0 16 M150 100 L56 50" />
      <Rod from={[8, 64]} to={[60, 54]} />
      <Arrow motion d="M28 92 H4" at={[4, 92]} deg={180} />
    </>
  ),
];

const catfishHold: Step[] = [
  () => (
    <>
      <FishShape x={20} y={70} len={124} catfish />
      <path className="rig-spine" d="M60 52 l2 -16 M42 76 l-10 14" />
      <Hand x={130} y={56} scale={1} flip />
      <Yes x={140} y={24} />
    </>
  ),
  () => (
    <>
      <FishShape x={30} y={70} len={110} catfish />
      <path className="rig-spine" d="M66 54 l2 -14 M50 76 l-10 14" />
      <circle className="rig-hot" cx={67} cy={42} r={7} />
      <circle className="rig-hot" cx={44} cy={84} r={7} />
      <No x={18} y={30} />
    </>
  ),
];

// ------------------------------------------------------------- baits

const worm: Step[] = [
  () => (
    <>
      <g transform="translate(40 14)">
        <Hook kind="j" L={64} R={14} P={22} />
      </g>
      <path className="rig-worm" strokeWidth={8} d="M120 104 C140 86 130 64 110 70 C96 74 84 70 78 82" />
      <Arrow motion d="M104 40 C92 44 80 54 74 66" at={[74, 66]} deg={120} />
    </>
  ),
  () => (
    <>
      <g transform="translate(40 14)">
        <Hook kind="j" L={64} R={14} P={22} />
      </g>
      <path className="rig-worm" strokeWidth={8} d="M40 26 V44 C52 46 54 52 40 56 C28 60 28 66 40 68 C52 70 52 76 40 80 C30 84 34 90 46 92 C60 94 68 92 68 74" />
      <Arrow motion d="M16 70 V34" at={[16, 34]} deg={-90} />
      <Label x={110} y={60} anchor="start">×3–5</Label>
    </>
  ),
  () => (
    <>
      <g transform="translate(30 10)">
        <Hook kind="j" L={64} R={14} P={22} />
      </g>
      <path className="rig-worm" strokeWidth={8} d="M30 24 V60 C40 64 42 70 30 74 C24 78 26 86 36 88 C50 90 58 86 58 74" />
      <path className="rig-worm" strokeWidth={8} d="M58 74 C64 100 92 108 104 92 C112 82 126 86 132 98" />
      <Arrow motion d="M136 74 q8 6 0 12 q-8 6 0 12" at={[136, 98]} deg={90} />
    </>
  ),
];

const minnow: Step[] = [
  () => (
    <>
      <FishShape x={30} y={60} len={100} lateral />
      <circle className="rig-hot" cx={30} cy={60} r={8} />
      <g transform="translate(24 46) scale(0.7)">
        <Hook kind="j" L={30} R={10} P={14} />
      </g>
    </>
  ),
  () => (
    <>
      <FishShape x={30} y={66} len={100} lateral />
      <path className="rig-spine-line" d="M48 66 C70 62 96 62 110 66" />
      <circle className="rig-hot" cx={84} cy={54} r={8} />
      <g transform="translate(76 38) scale(0.7)">
        <Hook kind="j" L={30} R={10} P={14} />
      </g>
    </>
  ),
  () => (
    <>
      <FishShape x={30} y={60} len={100} lateral />
      <circle className="rig-hot" cx={116} cy={58} r={8} />
      <g transform="translate(110 40) scale(0.7)">
        <Hook kind="j" L={30} R={10} P={14} />
      </g>
    </>
  ),
];

function Cricket({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <ellipse className="rig-bug" cx={0} cy={0} rx={32} ry={11} />
      <circle className="rig-bug" cx={-34} cy={-2} r={9} />
      <path className="rig-bug-leg" d="M10 6 l18 -22 l14 30 M-6 8 l-6 14 M-18 8 l-10 12 M-40 -8 q-16 -20 -26 -12 M-40 -6 q-10 -24 -4 -30" />
    </g>
  );
}

const cricket: Step[] = [
  () => (
    <>
      <Cricket x={84} y={70} />
      <circle className="rig-hot" cx={60} cy={64} r={8} />
      <g transform="translate(58 34) scale(0.7)">
        <Hook kind="j" L={36} R={10} P={14} />
      </g>
    </>
  ),
  () => (
    <>
      <Cricket x={70} y={70} />
      <circle className="rig-hot" cx={100} cy={70} r={8} />
      <g transform="translate(108 38) scale(0.7)">
        <Hook kind="j" L={36} R={10} P={14} />
      </g>
    </>
  ),
];

function Crayfish({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <path className="rig-cray" d="M-30 0 C-30 -12 10 -14 20 -8 L52 -6 C60 -6 62 6 52 6 L20 8 C10 14 -30 12 -30 0 Z" />
      <path className="rig-cray" d="M52 -6 l14 -6 l2 12 l-2 12 l-14 -6 z" />
      <path className="rig-cray" d="M-30 -4 C-46 -16 -60 -14 -58 -6 C-56 2 -44 0 -32 -2 M-30 4 C-46 16 -60 14 -58 6" />
      <path className="rig-fish-line" d="M24 -8 v16 M34 -7 v14 M44 -6 v12" />
    </g>
  );
}

const crayfish: Step[] = [
  () => (
    <>
      <Crayfish x={70} y={70} />
      <circle className="rig-hot" cx={128} cy={70} r={8} />
      <g transform="translate(118 42) scale(0.7)">
        <Hook kind="j" L={34} R={10} P={14} />
      </g>
      <Label x={128} y={104}>½″</Label>
    </>
  ),
  () => (
    <>
      <Crayfish x={70} y={70} />
      <circle className="rig-hot" cx={68} cy={60} r={8} />
      <g transform="translate(62 36) scale(0.7)">
        <Hook kind="j" L={34} R={10} P={14} />
      </g>
    </>
  ),
];

const splitShot: Step[] = [
  () => (
    <>
      <path className="rig-line" d="M4 60 H156" />
      <g transform="translate(80 40)">
        <circle className="rig-lead" cx={0} cy={0} r={14} />
        <path className="rig-groove" d="M-14 0 H14" />
      </g>
      <Arrow motion d="M80 18 V30" at={[80, 30]} deg={90} />
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M4 60 H156" />
      <circle className="rig-lead" cx={80} cy={60} r={12} />
      <Pliers x={80} y={60} deg={-90} />
      <Arrow motion d="M60 46 L70 54" at={[70, 54]} deg={40} />
      <Arrow motion d="M100 46 L90 54" at={[90, 54]} deg={140} />
    </>
  ),
];

const jigWork: Step[] = [
  () => (
    <>
      <Water y={10} h={110} />
      <path className="rig-bedline" d="M0 104 H160" />
      <path className="rig-line" d="M150 10 L120 94" />
      <ellipse className="rig-lead" cx={118} cy={98} rx={6} ry={5} />
      <Arrow motion d="M134 20 L118 84" at={[118, 84]} deg={105} />
    </>
  ),
  () => (
    <>
      <Water y={10} h={110} />
      <path className="rig-bedline" d="M0 104 H160" />
      <path className="rig-line" d="M150 10 L96 72" />
      <ellipse className="rig-lead" cx={94} cy={76} rx={6} ry={5} />
      <g className="rig-ghost">
        <ellipse className="rig-lead" cx={118} cy={98} rx={6} ry={5} />
      </g>
      <Arrow motion d="M116 92 L98 80" at={[98, 80]} deg={-145} />
    </>
  ),
  () => (
    <>
      <Water y={10} h={110} />
      <path className="rig-bedline" d="M0 104 H160" />
      <path className="rig-move-path rig-trail" d="M150 98 L132 74 L120 98 L102 74 L90 98 L72 74 L60 98" />
      <ellipse className="rig-lead" cx={60} cy={98} rx={6} ry={5} />
      <path className="rig-line" d="M60 98 L20 14" />
    </>
  ),
];

// ------------------------------------------------- cleaning the catch

const fillet: Step[] = [
  () => (
    <>
      <FishShape x={20} y={60} len={124} />
      <path className="rig-cut" d="M50 34 Q56 60 50 86" />
      <Knife x={60} y={6} deg={70} len={40} />
    </>
  ),
  () => (
    <>
      <FishShape x={20} y={60} len={124} />
      <path className="rig-cut" d="M50 60 H128" />
      <Knife x={26} y={60} deg={0} len={46} />
      <Arrow motion d="M84 76 H124" at={[124, 76]} deg={0} />
    </>
  ),
  () => (
    <>
      <path className="rig-board" d="M4 92 H156" />
      <path className="rig-fillet" d="M30 80 C40 64 110 62 132 80 Z" />
      <path className="rig-skin" d="M30 82 H140" />
      <Knife x={140} y={80} deg={180} len={48} />
      <Arrow motion d="M120 104 H70" at={[70, 104]} deg={180} />
    </>
  ),
];

const catfishSkin: Step[] = [
  () => (
    <>
      <FishShape x={20} y={64} len={124} catfish />
      <path className="rig-cut" d="M46 40 Q52 64 46 88" />
      <path className="rig-cut" d="M46 44 Q90 36 120 52" />
      <Knife x={70} y={8} deg={65} len={36} />
    </>
  ),
  () => (
    <>
      <FishShape x={20} y={64} len={124} catfish />
      <Hand x={10} y={64} scale={0.6} flip />
      <Pliers x={58} y={52} deg={-30} />
      <Arrow motion d="M70 30 C100 24 124 32 138 46" at={[138, 46]} deg={30} />
    </>
  ),
  () => (
    <>
      <path className="rig-board" d="M4 92 H156" />
      <path className="rig-fillet" d="M30 80 C40 62 110 60 132 80 Z" />
      <path className="rig-cut" d="M40 72 C70 66 100 66 124 74" />
      <Label x={80} y={110}>✂</Label>
    </>
  ),
];

const scaling: Step[] = [
  () => (
    <>
      <FishShape x={20} y={64} len={120} />
      <path className="rig-scales" d="M60 56 a4 4 0 0 1 8 0 M70 56 a4 4 0 0 1 8 0 M80 56 a4 4 0 0 1 8 0 M65 64 a4 4 0 0 1 8 0 M75 64 a4 4 0 0 1 8 0" />
      <path className="rig-spoon" d="M126 30 C140 22 150 30 146 40 C142 48 132 46 126 40 Z M126 36 L96 48" />
      <Arrow motion d="M124 82 H70" at={[70, 82]} deg={180} />
    </>
  ),
  () => (
    <>
      <Water y={40} h={80} />
      <FishShape x={30} y={78} len={100} />
      <Arrow motion d="M80 10 V34" at={[80, 34]} deg={90} />
    </>
  ),
];

const measure: Step[] = [
  () => (
    <>
      <path className="rig-ruler" d="M6 86 H154 v14 H6 z" />
      <path className="rig-metal-thin" d="M14 86 v6 M30 86 v6 M46 86 v6 M62 86 v6 M78 86 v6 M94 86 v6 M110 86 v6 M126 86 v6 M142 86 v6" />
      <FishShape x={14} y={60} len={132} />
      <path className="rig-cut" d="M14 30 V84 M146 30 V84" />
      <Arrow d="M14 26 H146 M14 26 l6 -4 M14 26 l6 4" at={[146, 26]} deg={0} />
    </>
  ),
  () => (
    <>
      <FishShape x={6} y={60} len={124} />
      <Finger x={136} y={22} deg={100} len={18} w={8} />
      <Finger x={136} y={98} deg={-100} len={18} w={8} />
      <Arrow motion d="M148 14 L140 32" at={[140, 32]} deg={115} />
      <Arrow motion d="M148 106 L140 88" at={[140, 88]} deg={-115} />
    </>
  ),
];

const bleed: Step[] = [
  () => (
    <>
      <FishShape x={20} y={64} len={124} />
      <path className="rig-spike" d="M26 10 L28 52" />
      <circle className="rig-hot" cx={29} cy={54} r={6} />
    </>
  ),
  () => (
    <>
      <Water y={30} h={90} />
      <FishShape x={20} y={74} len={124} />
      <path className="rig-cut" d="M44 54 Q50 74 44 94" />
      <circle className="rig-clock" cx={132} cy={14} r={10} />
      <path className="rig-clock-hands" d="M132 14 V7 M132 14 h5" />
      <Label x={116} y={19} anchor="end">5–10</Label>
    </>
  ),
];

// The improved clinch and arbor knots were one wide picture of four panels
// (RigDiagram); on a phone each panel came out about 80 px wide.
const clinch: Step[] = [
  () => (
    <>
      <path className="rig-line" d="M156 24 H46" />
      <path className="rig-work-line" d="M46 24 H36 C26 24 26 34 36 34 H100" />
      <KnotHook x={40} y={24} />
      <Arrow d="M54 52 H100 M54 52 l5 -4 M54 52 l5 4" at={[100, 52]} deg={0} />
      <Label x={108} y={57} anchor="start">5–6″</Label>
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M156 24 H46" />
      <path className="rig-work-line" d="M46 24 H38 C28 24 28 34 38 34 C44 34 46 30 50 16 L56 32 L62 16 L68 32 L74 16 L80 32 L86 16 L92 32 L98 16 L104 30 C108 40 112 46 120 50" />
      <KnotHook x={40} y={24} />
      <Label x={124} y={70}>×5–6</Label>
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M156 24 H46" />
      <path className="rig-work-line" d="M46 24 H38 C28 24 28 34 38 34 C44 34 46 30 50 16 L56 32 L62 16 L68 32 L74 16 L80 32 L86 16 L92 32 L98 16 L104 30 C116 52 70 64 46 40" />
      <KnotHook x={40} y={24} />
      <Arrow motion d="M118 60 C110 72 66 74 50 44" at={[50, 44]} deg={-120} />
      <Arrow motion d="M70 48 C78 40 90 40 96 48" at={[96, 48]} deg={50} />
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M156 24 H64" />
      <Wraps x0={48} x1={64} y={24} n={5} h={6} />
      <path className="rig-line" d="M64 30 l5 6" />
      <KnotHook x={40} y={24} />
      <Arrow d="M100 44 H146" at={[146, 44]} deg={0} />
      <Yes x={120} y={80} />
    </>
  ),
];

const arbor: Step[] = [
  () => (
    <>
      <Spool cx={48} cy={60} r={30} />
      <path className="rig-line" d="M156 48 H48" />
      <path className="rig-work-line" d="M48 48 A12 12 0 1 0 48 72 H104" />
      <Arrow motion d="M86 96 C70 108 40 104 30 92" at={[30, 92]} deg={-140} />
    </>
  ),
  () => (
    <>
      <Spool cx={48} cy={60} r={30} />
      <path className="rig-line" d="M156 48 H48" />
      <path className="rig-work-line" d="M48 48 A12 12 0 1 0 48 72 H92 C108 72 110 40 98 38 C86 36 88 60 108 62 H124" />
    </>
  ),
  () => (
    <>
      <Spool cx={48} cy={60} r={30} />
      <path className="rig-line" d="M156 48 H48" />
      <path className="rig-work-line" d="M48 48 A12 12 0 1 0 48 72 H92 C108 72 110 40 98 38 C86 36 88 60 108 62 H124" />
      <circle className="rig-knotblob" cx={126} cy={62} r={4.5} />
      <circle className="rig-hot" cx={126} cy={62} r={9} />
    </>
  ),
  () => (
    <>
      <Spool cx={48} cy={60} r={30} />
      <path className="rig-line" d="M156 48 H48" />
      <path className="rig-work-line" d="M48 48 A12 12 0 1 0 48 72 H58" />
      <ellipse className="rig-knotblob" cx={62} cy={50} rx={6} ry={5} />
      <Arrow d="M100 32 H148" at={[148, 32]} deg={0} />
      <Yes x={120} y={90} />
    </>
  ),
];

const knotTips: Step[] = [
  () => (
    <>
      <path className="rig-line" d="M156 30 H66" />
      <Wraps x0={50} x1={66} y={30} n={5} h={7} />
      <KnotHook x={40} y={30} />
      <path className="rig-drop" d="M86 54 c-5 8 -5 12 0 14 c5 -2 5 -6 0 -14 z M102 62 c-4 6 -4 10 0 11 c4 -1 4 -5 0 -11 z" />
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M156 30 H66" />
      <Wraps x0={52} x1={64} y={30} n={5} h={6} />
      <KnotHook x={40} y={30} />
      <Arrow motion d="M96 56 H148" at={[148, 56]} deg={0} />
    </>
  ),
  () => (
    <>
      <path className="rig-line" d="M156 30 H66" />
      <Wraps x0={52} x1={64} y={30} n={5} h={6} />
      <path className="rig-line" d="M64 36 l5 6" />
      <KnotHook x={40} y={30} />
      <path className="rig-clipper" d="M92 62 l-14 -16 M104 58 l-24 -12" />
      <Arrow d="M68 70 v-22" at={[68, 48]} deg={-90} size={5} />
      <Label x={76} y={84} anchor="start">≈⅛″</Label>
    </>
  ),
];

const spincastFix: Step[] = [
  () => (
    <>
      <Rod from={[4, 100]} to={[134, 40]} />
      <path className="rig-line rig-work" d="M134 40 c6 4 -4 8 2 12 c6 4 -4 8 2 12" />
      <circle className="rig-hot" cx={135} cy={50} r={14} />
      <SpincastReel x={40} y={88} pressed />
    </>
  ),
  () => (
    <>
      <circle className="rig-spool" cx={70} cy={62} r={38} />
      <circle className="rig-spool-hub" cx={70} cy={62} r={14} />
      <circle className="rig-pin" cx={104} cy={50} r={3.5} />
      <path className="rig-line rig-work" d="M56 34 C84 26 104 36 104 46 C104 56 86 60 70 76" />
      <Finger x={130} y={24} deg={150} len={24} w={8} />
      <Arrow motion d="M112 44 C122 40 128 34 130 26" at={[130, 26]} deg={-70} />
    </>
  ),
  () => (
    <>
      <Rod from={[4, 60]} to={[156, 50]} />
      <SpincastReel x={40} y={56} />
      <path className="rig-line rig-work" d="M156 50 L156 104" />
      <Finger x={120} y={92} deg={0} len={18} w={7} />
      <Arrow motion d="M24 82 A10 10 0 1 0 24 81" at={[24, 81]} deg={180} />
    </>
  ),
];

function DoughBall({ x, y, r }: { x: number; y: number; r: number }) {
  return <circle className="rig-dough" cx={x} cy={y} r={r} />;
}

const dough: Step[] = [
  () => (
    <>
      <g transform="translate(46 16)">
        <Hook kind="j" L={50} R={12} P={18} />
      </g>
      <DoughBall x={118} y={70} r={18} />
      <Arrow motion d="M98 66 L78 66" at={[78, 66]} deg={180} />
    </>
  ),
  () => (
    <>
      <g transform="translate(46 16)">
        <Hook kind="j" L={50} R={12} P={18} />
      </g>
      <ellipse className="rig-dough" cx={58} cy={72} rx={20} ry={18} />
      <Finger x={92} y={60} deg={190} len={16} w={8} />
      <Finger x={92} y={86} deg={170} len={16} w={8} />
      <Yes x={124} y={30} />
    </>
  ),
];

function Shrimp({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <path className="rig-cray" d="M-40 -6 C-40 -20 10 -24 30 -10 C40 -2 40 10 30 14 L20 16 C10 6 -10 6 -40 6 Z" />
      <path className="rig-cray" d="M30 14 l10 10 l-14 2 z" />
      <path className="rig-fish-line" d="M-10 -14 v18 M2 -14 v18 M14 -12 v18" />
      <path className="rig-fish-line" d="M-40 -6 q-14 -12 -20 -24 M-40 -4 q-18 -4 -26 -10" />
    </g>
  );
}

const shrimp: Step[] = [
  () => (
    <>
      <Shrimp x={84} y={70} />
      <circle className="rig-hot" cx={110} cy={66} r={8} />
      <g transform="translate(104 36) scale(0.7)">
        <Hook kind="j" L={34} R={10} P={14} />
      </g>
    </>
  ),
  () => (
    <>
      <g transform="translate(70 18)">
        <Hook kind="j" L={52} R={14} P={22} />
      </g>
      <path className="rig-cray" d="M62 46 C60 74 74 94 96 92 C104 90 106 80 104 64 L102 48 Z" />
      <path className="rig-hidden" d="M70 40 V76" />
      <Arrow motion d="M30 90 C34 70 44 58 56 52" at={[56, 52]} deg={-40} />
    </>
  ),
];

const panfishFillet: Step[] = [
  () => (
    <>
      <FishShape x={16} y={60} len={128} />
      <path className="rig-cut" d="M44 38 C70 34 92 36 104 52 L132 56" />
      <Knife x={18} y={22} deg={20} len={34} />
      <Arrow motion d="M60 28 H100" at={[100, 28]} deg={0} />
    </>
  ),
  () => (
    <>
      <FishShape x={16} y={60} len={128} />
      <path className="rig-cut" d="M44 34 Q50 60 44 86" />
      <path className="rig-cut" d="M46 60 C70 66 96 66 120 62" />
      <Knife x={40} y={102} deg={-20} len={36} />
    </>
  ),
];

/** A life jacket on a person standing at (x, y), their shoulders at y - 54. */
function Vest({ x, y, high = false }: { x: number; y: number; high?: boolean }) {
  const top = high ? y - 66 : y - 56;
  return (
    <g>
      <path className="rig-vest" d={`M${x - 11} ${top} h22 v${high ? 34 : 28} q-11 6 -22 0 z`} />
      <path className="rig-vest-strap" d={`M${x - 11} ${top + 12} h22 M${x - 11} ${top + 21} h22`} />
    </g>
  );
}

const lifejacket: Step[] = [
  () => (
    <>
      <Person x={80} y={112} arm={[96, 92]} />
      <Vest x={80} y={112} />
      <path className="rig-buckle" d="M76 68 h8 M76 77 h8" />
      <Yes x={124} y={40} />
    </>
  ),
  () => (
    <>
      <circle className="rig-head" cx={80} cy={50} r={8} />
      <path className="rig-person" d="M80 58 L80 86 M80 86 L72 112 M80 86 L88 112 M80 64 L66 32 M80 64 L94 32" />
      <Vest x={80} y={112} />
      <Arrow motion d="M50 70 V40" at={[50, 40]} deg={-90} />
      <Arrow motion d="M110 70 V40" at={[110, 40]} deg={-90} />
    </>
  ),
  () => (
    <>
      <circle className="rig-head" cx={80} cy={50} r={8} />
      <path className="rig-person" d="M80 58 L80 86 M80 86 L72 112 M80 86 L88 112 M80 64 L66 32 M80 64 L94 32" />
      <Vest x={80} y={112} high />
      <path className="rig-chin" d="M58 56 H102" />
      <Hand x={44} y={48} scale={0.45} />
      <Hand x={116} y={48} scale={0.45} flip />
      <Arrow motion d="M64 40 V26" at={[64, 26]} deg={-90} size={5} />
      <Arrow motion d="M96 40 V26" at={[96, 26]} deg={-90} size={5} />
      <No x={128} y={96} />
    </>
  ),
];

const shoreCast: Step[] = [
  () => (
    <>
      <rect className="rig-water" x={0} y={0} width={160} height={120} />
      <path className="rig-bank" d="M0 0 H52 C46 30 58 60 48 90 C44 104 50 114 52 120 H0 Z" />
      <circle className="rig-angler" cx={36} cy={62} r={6} />
      <Arrow motion d="M44 62 H140" at={[140, 62]} deg={0} />
      <No x={140} y={30} />
    </>
  ),
  () => (
    <>
      <rect className="rig-water" x={0} y={0} width={160} height={120} />
      <path className="rig-bank" d="M0 0 H52 C46 30 58 60 48 90 C44 104 50 114 52 120 H0 Z" />
      <circle className="rig-angler" cx={36} cy={62} r={6} />
      <Arrow motion d="M42 56 C52 40 56 24 58 8" at={[58, 8]} deg={-80} />
      <Arrow motion d="M42 68 C52 84 54 98 56 114" at={[56, 114]} deg={80} />
      <FishShape x={60} y={36} len={22} flip />
      <FishShape x={58} y={92} len={22} flip />
      <Yes x={128} y={60} />
    </>
  ),
];

const keepFish: Step[] = [
  () => (
    <>
      <rect className="rig-cooler" x={20} y={40} width={120} height={70} rx={8} />
      <rect className="rig-slush" x={26} y={58} width={108} height={46} rx={4} />
      <FishShape x={44} y={80} len={70} />
      <path className="rig-ice" d="M36 62 h8 v8 h-8 z M110 66 h8 v8 h-8 z M120 90 h8 v8 h-8 z M30 92 h8 v8 h-8 z" />
      <path className="rig-cooler-lid" d="M16 40 H144" />
    </>
  ),
  () => (
    <>
      <Water y={20} h={100} />
      <FishShape x={44} y={70} len={90} />
      <path className="rig-stringer" d="M10 10 C20 30 30 60 44 74" />
      <circle className="rig-hot" cx={46} cy={74} r={6} />
      <Yes x={22} y={104} />
      <No x={70} y={40} />
      <path className="rig-cut" d="M64 52 Q70 70 64 88" />
    </>
  ),
];

/** A stream seen from above, flowing down the picture, with a pool in it. */
function Stream() {
  return (
    <>
      <rect className="rig-bank" x={0} y={0} width={160} height={120} />
      <path className="rig-stream" d="M54 0 C46 30 58 60 50 120 H112 C120 60 106 30 112 0 Z" />
      <ellipse className="rig-pool" cx={82} cy={44} rx={24} ry={16} />
      <path className="rig-current" d="M70 8 v12 M96 8 v12 M66 78 v12 M98 80 v12" />
      <path className="rig-arrow" d="M70 20 l-3 -5 M70 20 l3 -5 M96 20 l-3 -5 M96 20 l3 -5" />
    </>
  );
}

const streamDrift: Step[] = [
  () => (
    <>
      <Stream />
      <circle className="rig-angler" cx={82} cy={112} r={5} />
      <Arrow motion d="M82 104 V76" at={[82, 76]} deg={-90} />
    </>
  ),
  () => (
    <>
      <Stream />
      <circle className="rig-angler" cx={82} cy={96} r={5} />
      <path className="rig-line" d="M82 90 C80 70 78 40 76 22" />
      <Arrow motion d="M92 86 C94 66 92 44 86 24" at={[86, 24]} deg={-100} />
    </>
  ),
  () => (
    <>
      <Stream />
      <circle className="rig-angler" cx={82} cy={96} r={5} />
      <path className="rig-line" d="M82 90 C84 76 80 62 78 50" />
      <path className="rig-worm" strokeWidth={4} d="M75 44 q3 4 6 0" />
      <Arrow motion d="M64 24 C62 40 66 52 70 62" at={[70, 62]} deg={70} />
    </>
  ),
];

function Ice({ hole = 80 }: { hole?: number }) {
  return (
    <>
      <rect className="rig-water" x={0} y={46} width={160} height={74} />
      <path className="rig-ice-sheet" d={`M0 30 H${hole - 8} V46 H0 Z M${hole + 8} 30 H160 V46 H${hole + 8} Z`} />
    </>
  );
}

const iceFish: Step[] = [
  () => (
    <>
      <Ice />
      <path className="rig-auger" d="M80 0 V44 M70 4 H90" />
      <path className="rig-wraps" d="M76 24 l8 4 M76 32 l8 4 M76 40 l8 4" />
      <Arrow motion d="M104 8 A12 6 0 1 1 104 9" at={[104, 9]} deg={180} />
      <Label x={92} y={62} anchor="start">4–6″</Label>
    </>
  ),
  () => (
    <>
      <Ice />
      <Rod from={[40, 22]} to={[80, 16]} />
      <path className="rig-line" d="M80 16 V84" />
      <ellipse className="rig-lure" cx={80} cy={90} rx={4} ry={7} />
      <Arrow motion d="M98 96 V70" at={[98, 70]} deg={-90} />
      <Arrow motion d="M108 70 V96" at={[108, 96]} deg={90} />
    </>
  ),
  () => (
    <>
      <Ice />
      <path className="rig-metal" d="M64 30 L96 30 M80 30 V6" />
      <path className="rig-flag" d="M80 6 L100 12 L80 18 Z" />
      <path className="rig-line" d="M80 30 V96" />
      <FishShape x={72} y={102} len={40} />
      <Arrow motion d="M112 24 V8" at={[112, 8]} deg={-90} />
    </>
  ),
];

function Boat({ x, y }: { x: number; y: number }) {
  return <path className="rig-boat" d={`M${x - 26} ${y - 8} H${x + 26} L${x + 18} ${y + 4} H${x - 18} Z`} />;
}

const trolling: Step[] = [
  () => (
    <>
      <Water y={30} h={90} />
      <path className="rig-bedline" d="M0 110 H160" />
      <Boat x={124} y={30} />
      <path className="rig-line" d="M104 24 C70 40 40 76 26 104" />
      <ellipse className="rig-lure" cx={24} cy={106} rx={7} ry={3.5} />
      <Arrow motion d="M138 46 H156" at={[156, 46]} deg={0} />
    </>
  ),
  () => (
    <>
      <Water y={30} h={90} />
      <Boat x={110} y={30} />
      <path className="rig-move-path rig-trail" d="M20 18 H60 M60 18 H96" />
      <path className="rig-line" d="M90 24 C64 40 44 66 30 86" />
      <ellipse className="rig-lure" cx={28} cy={88} rx={7} ry={3.5} />
      <FishShape x={44} y={96} len={34} flip />
      <Label x={140} y={16}>⇄</Label>
    </>
  ),
];

const hookInjury: Step[] = [
  () => (
    <>
      <Finger x={10} y={74} deg={0} len={110} w={30} />
      <g transform="translate(92 40) rotate(20)">
        <Hook kind="j" L={30} R={10} P={18} />
      </g>
      <Arrow motion d="M130 64 C138 50 134 34 122 28" at={[122, 28]} deg={-150} />
      <Yes x={30} y={30} />
    </>
  ),
  () => (
    <>
      <Finger x={10} y={74} deg={0} len={110} w={30} />
      <path className="rig-cup" d="M80 26 L110 26 L120 76 L70 76 Z" />
      <path className="rig-cross" d="M138 20 v20 M128 30 h20" />
      <No x={30} y={30} />
    </>
  ),
];

export const STEP_DRAWINGS = {
  hookInjury,
  streamDrift,
  iceFish,
  trolling,
  lifejacket,
  shoreCast,
  keepFish,
  clinch,
  arbor,
  knotTips,
  spincastFix,
  dough,
  shrimp,
  panfishFillet,
  palomar,
  surgeonsLoop,
  blood,
  surgeonsKnot,
  spincastSpool,
  spinningFill,
  castSpinning,
  castBaitcast,
  drag,
  setHook,
  landing,
  release,
  deepHook,
  snag,
  catfishHold,
  worm,
  minnow,
  cricket,
  crayfish,
  splitShot,
  jigWork,
  fillet,
  catfishSkin,
  scaling,
  measure,
  bleed,
} satisfies Record<string, Step[]>;

export type StepKey = keyof typeof STEP_DRAWINGS;
