/**
 * The parts the handbook's drawings are made of (RigDiagram.tsx and
 * StepDrawings.tsx): hooks, swivels, reels, a rod, a hand, a fish, a knife,
 * arrows. Plain SVG in each drawing's own units; colours are classes in
 * refinements.css, from the theme, so every drawing works in dark mode.
 */

/** A numbered mark, with a thin line to what it names. */
export function Mark({ n, x, y, to }: { n: number; x: number; y: number; to?: [number, number] }) {
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
export function Hook({ kind, L, R, P, eye = 3.5 }: { kind: "j" | "circle"; L: number; R: number; P: number; eye?: number }) {
  let d: string;
  let barb: string;
  if (kind === "j") {
    d = `M0 ${eye} L0 ${L} A${R} ${R} 0 0 0 ${2 * R} ${L} L${2 * R} ${L - P}`;
    barb = `M${2 * R} ${L - P + 2} l${-3.5} ${5}`;
  } else {
    const ex = 1.5 * R;
    const ey = L - 0.866 * R;
    const tx = ex - 0.866 * P;
    const ty = ey - 0.5 * P;
    d = `M0 ${eye} L0 ${L} A${R} ${R} 0 1 0 ${ex} ${ey} L${tx} ${ty}`;
    barb = `M${tx + 1.7} ${ty + 1} l${-2} ${4.5}`;
  }
  return (
    <g className="rig-metal">
      <circle cx={0} cy={0} r={eye} vectorEffect="non-scaling-stroke" />
      <path d={d} vectorEffect="non-scaling-stroke" />
      <path d={barb} vectorEffect="non-scaling-stroke" />
    </g>
  );
}

/** A hook drawn big for a knot: its eye (radius 7) at (x, y), the shank down. */
export function KnotHook({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <Hook kind="j" L={58} R={12} P={20} eye={7} />
    </g>
  );
}

/** A barrel swivel lying along the line, starting at x: 44 units long, or 92 when big. */
export function Swivel({ x, y, big = false }: { x: number; y: number; big?: boolean }) {
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
export function Wraps({ x0, x1, y, lean = 1, n = 5, h = 7, className = "rig-wraps" }: { x0: number; x1: number; y: number; lean?: 1 | -1; n?: number; h?: number; className?: string }) {
  const step = (x1 - x0) / (n - 1);
  const d = Array.from({ length: n }, (_, i) => `M${x0 + i * step - 2 * lean} ${y - h} l${4 * lean} ${2 * h}`).join(" ");
  return <path className={className} d={d} />;
}

/** A reel's spool seen face on. */
export function Spool({ cx, cy, r = 22 }: { cx: number; cy: number; r?: number }) {
  return (
    <>
      <circle className="rig-spool" cx={cx} cy={cy} r={r} />
      <circle className="rig-spool-hub" cx={cx} cy={cy} r={r * 0.41} />
    </>
  );
}

/** Two arrowhead strokes at (x, y), pointing at `deg` degrees (0 = right, 90 = down). */
export function head(x: number, y: number, deg: number, size = 6): string {
  const a = (deg * Math.PI) / 180;
  const p = (da: number) => {
    const b = a + Math.PI + da;
    return `M${x} ${y} L${(x + size * Math.cos(b)).toFixed(1)} ${(y + size * Math.sin(b)).toFixed(1)}`;
  };
  return `${p(0.45)} ${p(-0.45)}`;
}

/** A path with an arrowhead at its end. `motion` animates it, for a movement. */
export function Arrow({ d, at, deg, motion = false, size = 6 }: { d: string; at: [number, number]; deg: number; motion?: boolean; size?: number }) {
  return (
    <g className={motion ? "rig-move" : "rig-arrow"}>
      <path className={motion ? "rig-move-path" : undefined} d={d} />
      <path d={head(at[0], at[1], deg, size)} />
    </g>
  );
}

/** A rod from its butt to its tip; the first part is the handle. */
export function Rod({ from, to, handle = 0.26 }: { from: [number, number]; to: [number, number]; handle?: number }) {
  const hx = from[0] + (to[0] - from[0]) * handle;
  const hy = from[1] + (to[1] - from[1]) * handle;
  return (
    <g>
      <line className="rig-rod" x1={hx} y1={hy} x2={to[0]} y2={to[1]} />
      <line className="rig-handle" x1={from[0]} y1={from[1]} x2={hx} y2={hy} />
    </g>
  );
}

/** A spinning reel hanging under a rod at (x, y), seen from the side; the bail open or shut. */
export function SpinningReel({ x, y, open = false }: { x: number; y: number; open?: boolean }) {
  return (
    <g>
      <path className="rig-reel" d={`M${x - 3} ${y} h6 l-1 9 h-4 z`} />
      <rect className="rig-reel" x={x - 9} y={y + 9} width={18} height={13} rx={4} />
      <rect className="rig-spool-side" x={x - 12} y={y + 11} width={5} height={9} rx={1.5} />
      {open ? (
        <path className="rig-bail" d={`M${x - 12} ${y + 11} q -6 -10 4 -16`} />
      ) : (
        <path className="rig-bail" d={`M${x - 12} ${y + 11} q -5 4 0 9`} />
      )}
      <path className="rig-metal-thin" d={`M${x + 9} ${y + 15} h6 v6`} />
      <circle className="rig-knob" cx={x + 15} cy={y + 22} r={2.4} />
    </g>
  );
}

/** A spincast reel on top of a rod at (x, y): its cone points up the rod (to the right), the button at the back. */
export function SpincastReel({ x, y, pressed = false }: { x: number; y: number; pressed?: boolean }) {
  return (
    <g>
      <path className="rig-reel" d={`M${x - 10} ${y} v-14 q0 -4 4 -4 h10 l12 7 v4 l-12 7 z`} />
      <circle className="rig-spool-side" cx={x + 22} cy={y - 11} r={2} />
      <rect className={pressed ? "rig-button is-pressed" : "rig-button"} x={x - 15} y={y - 15} width={5} height={10} rx={2} />
    </g>
  );
}

/** A baitcaster on top of a rod at (x, y), its spool across the rod. */
export function Baitcaster({ x, y }: { x: number; y: number }) {
  return (
    <g>
      <rect className="rig-reel" x={x - 12} y={y - 17} width={24} height={15} rx={6} />
      <rect className="rig-spool-side" x={x - 7} y={y - 14} width={14} height={9} rx={2} />
      <path className="rig-metal-thin" d={`M${x + 12} ${y - 9} h7`} />
      <circle className="rig-knob" cx={x + 20} cy={y - 9} r={2.6} />
    </g>
  );
}

/** A finger (or a thumb), as a rounded bar from (x, y) at `deg` degrees. */
export function Finger({ x, y, deg = 0, len = 20, w = 8 }: { x: number; y: number; deg?: number; len?: number; w?: number }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${deg})`}>
      <rect className="rig-hand" x={0} y={-w / 2} width={len} height={w} rx={w / 2} />
      <path className="rig-nail" d={`M${len - 6} ${-w / 4} h3`} />
    </g>
  );
}

/** A hand seen from the side, palm down, fingers to the right; (x, y) the wrist. */
export function Hand({ x, y, scale = 1, flip = false }: { x: number; y: number; scale?: number; flip?: boolean }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${flip ? -scale : scale} ${scale})`}>
      <path
        className="rig-hand"
        d="M0 -7 C8 -11 22 -11 32 -8 L44 -6 C48 -5 48 0 44 0 L33 0 C30 4 26 7 20 8 L6 8 C2 8 0 5 0 2 Z"
      />
      <path className="rig-nail" d="M30 -4 h8 M34 -1 h6" />
    </g>
  );
}

/**
 * A fish lying on its side, its nose at (x, y), facing left, `len` long
 * (`flip` faces it right). `gill` draws the gill cover's edge, `lateral` the
 * lateral line, `spines` a catfish's fin spines and whiskers.
 */
export function FishShape({
  x,
  y,
  len,
  flip = false,
  gill = true,
  lateral = false,
  catfish = false,
  className = "rig-fish",
}: {
  x: number;
  y: number;
  len: number;
  flip?: boolean;
  gill?: boolean;
  lateral?: boolean;
  catfish?: boolean;
  className?: string;
}) {
  const h = len * (catfish ? 0.2 : 0.28);
  const body = `M0 0 C${len * 0.1} ${-h * 0.95} ${len * 0.45} ${-h * 1.05} ${len * 0.72} ${-h * 0.35}
    L${len * 0.8} ${-h * 0.18} L${len} ${-h * 0.75} C${len * 0.96} ${-h * 0.2} ${len * 0.96} ${h * 0.2} ${len} ${h * 0.75}
    L${len * 0.8} ${h * 0.18} L${len * 0.72} ${h * 0.35} C${len * 0.45} ${h * 1.05} ${len * 0.1} ${h * 0.95} 0 0 Z`;
  return (
    <g transform={`translate(${x} ${y}) scale(${flip ? -1 : 1} 1)`}>
      <path className={`${className} rig-fin`} d={`M${len * 0.3} ${-h * 0.88} C${len * 0.36} ${-h * 1.5} ${len * 0.5} ${-h * 1.45} ${len * 0.58} ${-h * 0.72} Z`} />
      <path className={className} d={body} />
      <circle className="rig-fish-eye" cx={len * 0.08} cy={-h * 0.18} r={Math.max(1.6, len * 0.022)} />
      {gill && <path className="rig-fish-line" d={`M${len * 0.2} ${-h * 0.62} Q${len * 0.25} 0 ${len * 0.2} ${h * 0.62}`} />}
      <path className={`${className} rig-fin`} d={`M${len * 0.24} ${h * 0.25} l${len * 0.1} ${h * 0.35} l${-len * 0.03} ${-h * 0.45} z`} />
      {lateral && <path className="rig-fish-line" d={`M${len * 0.22} ${-h * 0.1} C${len * 0.4} ${-h * 0.25} ${len * 0.6} ${-h * 0.1} ${len * 0.78} 0`} />}
      {catfish && (
        <path className="rig-fish-line" d={`M${len * 0.02} ${h * 0.15} q${-len * 0.08} ${h * 0.6} ${-len * 0.04} ${h * 1.1} M${len * 0.04} ${-h * 0.35} q${-len * 0.1} ${-h * 0.4} ${-len * 0.06} ${-h * 1.1}`} />
      )}
    </g>
  );
}

/** A knife from its handle end at (x, y) at `deg` degrees, `len` long. */
export function Knife({ x, y, deg = 0, len = 60 }: { x: number; y: number; deg?: number; len?: number }) {
  const hl = len * 0.35;
  return (
    <g transform={`translate(${x} ${y}) rotate(${deg})`}>
      <rect className="rig-knife-handle" x={0} y={-3.5} width={hl} height={7} rx={3} />
      <path className="rig-knife-blade" d={`M${hl} -3 L${len - 6} -3 Q${len} -2 ${len} 1 L${hl} 3 Z`} />
    </g>
  );
}

/** A person standing at (x, y) (the feet), facing right; `arm` is where a
 * hand is, `arm2` the other (both on a rod's handle when casting). */
export function Person({ x, y, arm, arm2 }: { x: number; y: number; arm: [number, number]; arm2?: [number, number] }) {
  const second = arm2 ? ` M${x} ${y - 46} L${arm2[0]} ${arm2[1]}` : "";
  return (
    <g>
      <circle className="rig-head" cx={x} cy={y - 62} r={8} />
      <path className="rig-person" d={`M${x} ${y - 54} L${x} ${y - 26} M${x} ${y - 26} L${x - 8} ${y} M${x} ${y - 26} L${x + 8} ${y} M${x} ${y - 46} L${arm[0]} ${arm[1]}${second}`} />
    </g>
  );
}

/**
 * The hook in a hooked fish's mouth: the line comes to (x, y), the fish's
 * nose, and the hook's bend sits under the jaw with its point up into it.
 * `flip` for a fish facing right. Added 2026-11-25: the owner saw lines that
 * simply ended at a fish's mouth, with no hook, and asked for the real thing.
 */
export function LipHook({ x, y, flip = false }: { x: number; y: number; flip?: boolean }) {
  return (
    <g className="rig-metal rig-lip-hook" transform={`translate(${x} ${y}) scale(${flip ? -1 : 1} 1)`}>
      <circle cx={0} cy={0} r={1.6} />
      <path d="M0 1.6 C0 5 1 8 4 8.4 C6.8 8.8 8.2 6.6 7.6 3.6" />
      <path d="M7.6 3.6 l-2.6 2" />
    </g>
  );
}

/** A cross for "don't" and a tick for "do", at (x, y). */
export function No({ x, y }: { x: number; y: number }) {
  return <path className="rig-no" d={`M${x - 6} ${y - 6} l12 12 M${x + 6} ${y - 6} l-12 12`} />;
}

export function Yes({ x, y }: { x: number; y: number }) {
  return <path className="rig-yes" d={`M${x - 7} ${y} l5 5 l9 -11`} />;
}
