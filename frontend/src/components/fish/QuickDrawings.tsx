import type { ReactNode } from "react";

import { Arrow, FishShape, Hand, LipHook, No, Rod, SpinningReel, Yes } from "./rigParts";
import type { MovingKey } from "./quickTopics";
import { STEP_DRAWINGS } from "./StepDrawings";

/**
 * The moving pictures of a quick take (QuickTake.tsx), 160 × 120 each, in
 * the drawings' own style (StepDrawings.tsx). They loop like a short GIF:
 * SVG animations, so the parts of one picture keep time with each other,
 * and the colours follow the theme. `motion` is false for a reader who
 * asked for less motion: the picture stands still, at the step's pose.
 */
export type Panel = (motion: boolean) => ReactNode;

const EASE = ".42 0 .58 1";

/** `attr` going through `values` at `times` (0 to 1), a loop every `dur` s. */
function Anim({ attr, values, times, dur }: { attr: string; values: string[]; times: number[]; dur: number }) {
  return (
    <animate
      attributeName={attr}
      dur={`${dur}s`}
      repeatCount="indefinite"
      values={values.join(";")}
      keyTimes={times.join(";")}
      calcMode="spline"
      keySplines={Array(times.length - 1).fill(EASE).join(";")}
    />
  );
}

/** The element's transform, the same way. */
function Move({ type, values, times, dur }: { type: "translate" | "rotate"; values: string[]; times: number[]; dur: number }) {
  return (
    <animateTransform
      attributeName="transform"
      type={type}
      dur={`${dur}s`}
      repeatCount="indefinite"
      values={values.join(";")}
      keyTimes={times.join(";")}
      calcMode="spline"
      keySplines={Array(times.length - 1).fill(EASE).join(";")}
    />
  );
}

/** Water from `y` down; `bank`, the bank the angler stands on, out to x. */
function Water({ y, bank }: { y: number; bank?: number }) {
  return (
    <>
      <rect className="rig-water" x={0} y={y} width={160} height={120 - y} />
      <path className="rig-surface" d={`M0 ${y} q 10 -3 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0 t 20 0`} />
      {bank !== undefined && (
        <>
          <path className="rig-bank" style={{ stroke: "none" }} d={`M0 ${y - 4} H${bank} C${bank + 8} ${y + 8} ${bank + 4} ${y + 26} ${bank + 12} 120 H0 Z`} />
          <path className="qt-bank-edge" d={`M0 ${y - 4} H${bank} C${bank + 8} ${y + 8} ${bank + 4} ${y + 26} ${bank + 12} 120`} />
        </>
      )}
    </>
  );
}

// ------------------------------------------------- playing and landing
// Still, the first four are the step drawings of the same topic.

const still = STEP_DRAWINGS.landing;

/** The fish pulls; the bent rod gives and springs back, the line stays tight. */
const tight: Panel = (m) => {
  if (!m) return still[0]();
  const t = [0, 0.5, 1];
  const dur = 2.2;
  return (
    <>
      <Water y={80} bank={40} />
      <path className="rig-handle" d="M16 104 L26 84" />
      <path className="rig-rod" d="M26 84 Q60 22 112 32">
        <Anim attr="d" values={["M26 84 Q60 22 112 32", "M26 84 Q66 30 120 48", "M26 84 Q60 22 112 32"]} times={t} dur={dur} />
      </path>
      <path className="rig-line" d="M112 32 L130 94">
        <Anim attr="d" values={["M112 32 L130 94", "M120 48 L138 98", "M112 32 L130 94"]} times={t} dur={dur} />
      </path>
      <g>
        <Move type="translate" values={["0 0", "8 4", "0 0"]} times={t} dur={dur} />
        <FishShape x={130} y={94} len={28} flip />
        <LipHook x={130} y={94} flip />
      </g>
      <Yes x={140} y={18} />
    </>
  );
};

/** The fish runs and takes line off the reel; the hand leaves the handle. */
const run: Panel = (m) => {
  if (!m) return still[1]();
  const t = [0, 0.75, 0.88, 0.881, 1];
  const dur = 2.6;
  const near = "M90 30 L108 98";
  const far = "M90 30 L144 98";
  return (
    <>
      <Water y={70} bank={54} />
      <Rod from={[14, 90]} to={[90, 30]} />
      <SpinningReel x={34} y={74} />
      <g opacity="0">
        <Anim attr="opacity" values={["0", "1", "0", "1", "0", "0"]} times={[0, 0.18, 0.36, 0.54, 0.72, 1]} dur={dur} />
        <path className="rig-move" d="M20 82 q-5 -6 0 -12 M13 86 q-8 -10 0 -20" />
      </g>
      <path className="rig-line" d={near}>
        <Anim attr="d" values={[near, far, far, near, near]} times={t} dur={dur} />
      </path>
      <g>
        <Anim attr="opacity" values={["1", "1", "0", "0", "1"]} times={t} dur={dur} />
        <g>
          <Move type="translate" values={["0 0", "36 0", "36 0", "0 0", "0 0"]} times={t} dur={dur} />
          <FishShape x={108} y={98} len={26} flip />
          <LipHook x={108} y={98} flip />
        </g>
      </g>
      <No x={56} y={106} />
    </>
  );
};

/** Pumping: the rod comes up and draws the fish in, then goes down while the reel turns. */
const pump: Panel = (m) => {
  if (!m) return still[2]();
  const t = [0, 0.35, 0.5, 0.85, 0.93, 0.931, 1];
  const dur = 3.2;
  const low = "0 14 96";
  const high = "-28 14 96";
  const start = "M120 52 L128 94";
  const lifted = "M87 7 L112 94";
  const lowered = "M120 52 L112 94";
  return (
    <>
      <Water y={84} bank={58} />
      <g>
        <Move type="rotate" values={[low, high, high, low, low, low, low]} times={t} dur={dur} />
        <Rod from={[14, 96]} to={[120, 52]} />
        <g opacity="0">
          <Anim attr="opacity" values={["0", "0", "1", "1", "0", "0", "0"]} times={t} dur={dur} />
          <Arrow motion d="M54 92 A8 8 0 1 0 54 91" at={[54, 91]} deg={180} />
        </g>
      </g>
      <path className="rig-line" d={start}>
        <Anim attr="d" values={[start, lifted, lifted, lowered, lowered, start, start]} times={t} dur={dur} />
      </path>
      <g>
        <Anim attr="opacity" values={["1", "1", "1", "1", "0", "0", "1"]} times={t} dur={dur} />
        <g>
          <Move type="translate" values={["0 0", "-16 0", "-16 0", "-16 0", "-16 0", "0 0", "0 0"]} times={t} dur={dur} />
          <FishShape x={128} y={94} len={26} />
          <LipHook x={128} y={94} />
        </g>
      </g>
      <g opacity="0">
        <Anim attr="opacity" values={["1", "1", "0", "0", "0", "0", "1"]} times={t} dur={dur} />
        <Arrow motion d="M134 40 C130 24 118 12 104 8" at={[104, 8]} deg={-165} />
      </g>
    </>
  );
};

/** The line brings the fish to the net held at the bank, head first; the
 * net comes up with it. */
const net: Panel = (m) => {
  if (!m) return still[3]();
  const t = [0, 0.4, 0.5, 0.7, 0.88, 0.94, 0.941, 1];
  const dur = 3.4;
  // One hand holds the rod out over the water, the other the net.
  const out = "M90 10 L124 76";
  const inNet = "M90 10 L56 76";
  const up = "M90 10 L56 48";
  return (
    <>
      <Water y={52} />
      <path className="rig-rod" d="M30 2 L90 10" />
      <g>
        <Anim attr="opacity" values={["1", "1", "1", "1", "1", "0", "0", "1"]} times={t} dur={dur} />
        <path className="rig-line" d={out}>
          <Anim attr="d" values={[out, inNet, inNet, up, up, up, out, out]} times={t} dur={dur} />
        </path>
        <g>
          <Move type="translate" values={["0 0", "-68 0", "-68 0", "-68 -28", "-68 -28", "-68 -28", "0 0", "0 0"]} times={t} dur={dur} />
          <FishShape x={124} y={76} len={34} />
          <LipHook x={124} y={76} />
        </g>
        <g>
          <Move type="translate" values={["0 0", "0 0", "0 0", "0 -28", "0 -28", "0 -28", "0 0", "0 0"]} times={t} dur={dur} />
          <path className="rig-net" d="M34 66 C34 100 94 100 94 66 Z" />
          <path className="rig-handle" d="M34 66 L16 30" />
        </g>
      </g>
    </>
  );
};

/** No net: a bass held up by the lower lip, thumb in its mouth. */
const lip: Panel = (m) => {
  const t = [0, 0.25, 0.5, 0.75, 1];
  return (
    <>
      <g>
        {m && <Move type="rotate" values={["0 80 26", "5 80 26", "0 80 26", "-5 80 26", "0 80 26"]} times={t} dur={3} />}
        <g transform="translate(80 26) rotate(90)">
          <FishShape x={0} y={0} len={76} />
        </g>
      </g>
      <g transform="translate(46 14) rotate(20)">
        <Hand x={0} y={0} scale={0.8} />
      </g>
      <Yes x={134} y={22} />
    </>
  );
};

/** Sharp teeth: keep the hand off the mouth, across the back behind the head. */
const behindHead: Panel = (m) => {
  const t = [0, 0.5, 1];
  return (
    <>
      {/* A long, slim fish: a pike's shape, not a sunfish's. */}
      <g transform="translate(12 82) scale(1 0.72)">
        <FishShape x={0} y={0} len={120} lateral />
      </g>
      <circle className="rig-hot" cx={16} cy={82} r={8}>
        {m && <Anim attr="opacity" values={["0.35", "1", "0.35"]} times={t} dur={1.6} />}
      </circle>
      <No x={20} y={56} />
      <g>
        {m && <Move type="translate" values={["0 0", "0 4", "0 0"]} times={t} dur={1.6} />}
        <g transform="translate(52 22) rotate(90)">
          <Hand x={0} y={0} scale={0.8} />
        </g>
      </g>
      <Yes x={86} y={28} />
    </>
  );
};

export const QUICK_DRAWINGS: Record<MovingKey, Panel[]> = {
  landing: [tight, run, pump, net, lip, behindHead],
};
