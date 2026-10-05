import { specFor, type FishSpec, type Pattern } from "@/lib/fishArt";

/**
 * An original comic-style fish illustration, drawn from the species' field
 * marks (see lib/fishArt.ts). Pure SVG, no hooks, so it renders on the
 * server and costs nothing to hydrate.
 *
 * The body is two cubic curves on top and two below; fins are placed by
 * sampling those same curves, so a fin always sits on the fish's actual
 * back whatever its shape. Fins and tail are drawn first and the body over
 * them, which hides their bases the way a real fin disappears into the body.
 */

const W = 260;
const H = 160;
const CY = 80;
const NX = 22;
const INK = "#10262f";

type Pt = [number, number];

function cubic(p0: Pt, p1: Pt, p2: Pt, p3: Pt, steps = 40): Pt[] {
  const pts: Pt[] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const u = 1 - t;
    const a = u * u * u;
    const b = 3 * u * u * t;
    const c = 3 * u * t * t;
    const d = t * t * t;
    pts.push([
      a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
      a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
    ]);
  }
  return pts;
}

function yAt(pts: Pt[], x: number): number {
  let best = pts[0];
  let bestD = Infinity;
  for (const p of pts) {
    const d = Math.abs(p[0] - x);
    if (d < bestD) {
      bestD = d;
      best = p;
    }
  }
  return best[1];
}

function f(n: number): string {
  return n.toFixed(1);
}

// Deterministic pseudo-random numbers, so speckles don't change per render
// (and server and client markup match).
function rng(seed: string) {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) h = Math.imul(h ^ seed.charCodeAt(i), 16777619);
  return () => {
    h += 0x6d2b79f5;
    let t = h;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface Geometry {
  outline: string; // body edge minus the tail-base segment, which the tail covers
  L: number;
  Dt: number;
  Db: number;
  tx: number;
  body: string;
  top: Pt[];
  bottom: Pt[];
  topAt: (frac: number) => number;
  bottomAt: (frac: number) => number;
  x: (frac: number) => number;
}

function geometry(s: FishSpec): Geometry {
  const L = s.length;
  const Dt = s.depthTop;
  const Db = s.depthBottom;
  const tx = NX + L;
  const x = (frac: number) => NX + frac * L;
  const noseY = CY + (s.flatHead ? 4 : 2);
  const N: Pt = [NX, noseY];
  const M: Pt = [x(s.peak), CY - Dt];
  const P: Pt = [tx, CY - s.peduncle];
  const Q: Pt = [tx, CY + s.peduncle];
  const B: Pt = [x(s.peak + 0.06), CY + Db];

  const t1: [Pt, Pt] = [
    [NX + 0.01 * L, CY - (s.flatHead ? 0.3 : 0.62) * Dt],
    [M[0] - (s.hump ? 0.07 : 0.2) * L, CY - Dt],
  ];
  const t2: [Pt, Pt] = [
    [M[0] + 0.22 * L, CY - Dt],
    [P[0] - 0.18 * L, CY - s.peduncle - 0.06 * Dt],
  ];
  const b1: [Pt, Pt] = [
    [Q[0] - 0.18 * L, CY + s.peduncle + 0.06 * Db],
    [B[0] + 0.22 * L, CY + Db],
  ];
  const b2: [Pt, Pt] = [
    [B[0] - 0.24 * L, CY + Db],
    [NX + 0.02 * L, CY + 0.55 * Db],
  ];

  const top = [...cubic(N, t1[0], t1[1], M), ...cubic(M, t2[0], t2[1], P)];
  const bottom = [...cubic(Q, b1[0], b1[1], B), ...cubic(B, b2[0], b2[1], N)];
  const c = (p: Pt) => `${f(p[0])} ${f(p[1])}`;
  const body =
    `M ${c(N)} C ${c(t1[0])}, ${c(t1[1])}, ${c(M)} C ${c(t2[0])}, ${c(t2[1])}, ${c(P)} ` +
    `L ${c(Q)} C ${c(b1[0])}, ${c(b1[1])}, ${c(B)} C ${c(b2[0])}, ${c(b2[1])}, ${c(N)} Z`;

  const outline =
    `M ${c(N)} C ${c(t1[0])}, ${c(t1[1])}, ${c(M)} C ${c(t2[0])}, ${c(t2[1])}, ${c(P)} ` +
    `M ${c(Q)} C ${c(b1[0])}, ${c(b1[1])}, ${c(B)} C ${c(b2[0])}, ${c(b2[1])}, ${c(N)}`;

  return {
    outline,
    L,
    Dt,
    Db,
    tx,
    body,
    top,
    bottom,
    x,
    topAt: (frac) => yAt(top, x(frac)),
    bottomAt: (frac) => yAt(bottom, x(frac)),
  };
}

// ---------------------------------------------------------------- fins

function spinyFin(g: Geometry, from: number, to: number, height: number, spines: number): string {
  const pts: string[] = [`M ${f(g.x(from))} ${f(g.topAt(from) + 6)}`];
  for (let i = 0; i <= spines; i++) {
    const frac = from + ((to - from) * i) / spines;
    const shape = Math.sin(Math.PI * (0.18 + (0.8 * i) / spines));
    const h = height * (0.35 + 0.65 * shape);
    const px = g.x(frac);
    pts.push(`L ${f(px)} ${f(g.topAt(frac) - h)}`);
    if (i < spines) {
      const mid = frac + (to - from) / spines / 2;
      pts.push(`L ${f(g.x(mid))} ${f(g.topAt(mid) - h * 0.74)}`);
    }
  }
  pts.push(`L ${f(g.x(to))} ${f(g.topAt(to) + 6)} Z`);
  return pts.join(" ");
}

function softFin(g: Geometry, from: number, to: number, height: number, side: "top" | "bottom"): string {
  const sign = side === "top" ? -1 : 1;
  const at = side === "top" ? g.topAt : g.bottomAt;
  const inset = side === "top" ? 6 : -6;
  const x0 = g.x(from);
  const x1 = g.x(to);
  const y0 = at(from);
  const y1 = at(to);
  return (
    `M ${f(x0)} ${f(y0 + inset)} ` +
    `C ${f(x0 - 2)} ${f(y0 + sign * height)}, ${f(x0 + (x1 - x0) * 0.55)} ${f(y0 + sign * height * 1.08)}, ` +
    `${f(x1 + 3)} ${f(y1 + sign * height * 0.3)} ` +
    `L ${f(x1)} ${f(y1 + inset)} Z`
  );
}

function finRays(g: Geometry, from: number, to: number, height: number, side: "top" | "bottom", n = 4) {
  const at = side === "top" ? g.topAt : g.bottomAt;
  const sign = side === "top" ? -1 : 1;
  return Array.from({ length: n }, (_, i) => {
    const frac = from + ((to - from) * (i + 0.7)) / (n + 0.6);
    const x0 = g.x(frac);
    const y0 = at(frac);
    const reach = height * (0.9 - (0.4 * i) / n);
    return `M ${f(x0)} ${f(y0)} L ${f(x0 + 4)} ${f(y0 + sign * reach)}`;
  }).join(" ");
}

function tailPath(s: FishSpec, g: Geometry): string {
  const T = g.L * (s.tail === "notched" ? 0.22 : 0.27);
  const Th = Math.max(g.Dt, g.Db) * (s.tail === "notched" ? 0.72 : 0.82);
  const bx = g.tx - 7;
  const pd = s.peduncle;
  const notch = s.tail === "notched" ? 0.8 : s.tail === "forked" ? 0.55 : 0.42;
  if (s.tail === "notched") {
    return (
      `M ${f(bx)} ${f(CY - pd)} C ${f(bx + 0.45 * T)} ${f(CY - pd - 0.3 * Th)}, ${f(bx + 0.9 * T)} ${f(CY - Th)}, ${f(bx + T)} ${f(CY - Th * 0.95)} ` +
      `Q ${f(bx + 0.86 * T)} ${f(CY - 0.4 * Th)}, ${f(bx + notch * T)} ${f(CY)} ` +
      `Q ${f(bx + 0.86 * T)} ${f(CY + 0.4 * Th)}, ${f(bx + T)} ${f(CY + Th * 0.95)} ` +
      `C ${f(bx + 0.9 * T)} ${f(CY + Th)}, ${f(bx + 0.45 * T)} ${f(CY + pd + 0.3 * Th)}, ${f(bx)} ${f(CY + pd)} Z`
    );
  }
  return (
    `M ${f(bx)} ${f(CY - pd)} Q ${f(bx + 0.45 * T)} ${f(CY - pd - 0.25 * Th)}, ${f(bx + T)} ${f(CY - Th)} ` +
    `Q ${f(bx + 0.66 * T)} ${f(CY - 0.35 * Th)}, ${f(bx + notch * T)} ${f(CY)} ` +
    `Q ${f(bx + 0.66 * T)} ${f(CY + 0.35 * Th)}, ${f(bx + T)} ${f(CY + Th)} ` +
    `Q ${f(bx + 0.45 * T)} ${f(CY + pd + 0.25 * Th)}, ${f(bx)} ${f(CY + pd)} Z`
  );
}

function tailRays(s: FishSpec, g: Geometry): string {
  const T = g.L * (s.tail === "notched" ? 0.2 : 0.24);
  const Th = Math.max(g.Dt, g.Db) * 0.62;
  const bx = g.tx - 2;
  return [-0.8, -0.4, 0.4, 0.8]
    .map((k) => `M ${f(bx)} ${f(CY + k * 4)} L ${f(bx + T * 0.8)} ${f(CY + k * Th)}`)
    .join(" ");
}

interface FinSet {
  back: string[]; // drawn behind the body
  rays: string[];
  extra?: string; // e.g. the shad's trailing dorsal thread
}

function dorsalFins(s: FishSpec, g: Geometry): FinSet {
  const Dt = g.Dt;
  switch (s.dorsal) {
    case "bass":
      return {
        back: [spinyFin(g, 0.29, 0.52, Dt * 0.44, 7), softFin(g, 0.51, 0.74, Dt * 0.46, "top")],
        rays: [finRays(g, 0.54, 0.72, Dt * 0.36, "top")],
      };
    case "split":
      return {
        back: [spinyFin(g, 0.27, 0.47, Dt * 0.48, 7), softFin(g, 0.54, 0.73, Dt * 0.42, "top")],
        rays: [finRays(g, 0.55, 0.71, Dt * 0.32, "top")],
      };
    case "crappie":
      return {
        back: [spinyFin(g, 0.45, 0.61, Dt * 0.5, 5), softFin(g, 0.6, 0.81, Dt * 0.56, "top")],
        rays: [finRays(g, 0.62, 0.79, Dt * 0.46, "top")],
      };
    case "sunfish":
      return {
        back: [spinyFin(g, 0.31, 0.57, Dt * 0.36, 8), softFin(g, 0.56, 0.81, Dt * 0.48, "top")],
        rays: [finRays(g, 0.59, 0.79, Dt * 0.4, "top")],
      };
    case "cat": {
      const adiposeFrom = 0.78;
      const adipose =
        `M ${f(g.x(adiposeFrom))} ${f(g.topAt(adiposeFrom) + 5)} ` +
        `Q ${f(g.x(0.84))} ${f(g.topAt(0.82) - Dt * 0.34)}, ${f(g.x(0.9))} ${f(g.topAt(0.9) + 4)} Z`;
      const sx = g.x(0.28);
      const spine = `M ${f(sx + 1)} ${f(g.topAt(0.28) + 2)} L ${f(sx + 5)} ${f(g.topAt(0.3) - Dt * 0.66)}`;
      return {
        back: [softFin(g, 0.28, 0.4, Dt * 0.6, "top"), adipose],
        rays: [finRays(g, 0.3, 0.39, Dt * 0.5, "top", 3)],
        extra: spine,
      };
    }
    case "shad": {
      const end = 0.57;
      const x0 = g.x(end);
      const y0 = g.topAt(end) - Dt * 0.3;
      const thread =
        `M ${f(x0 - 1)} ${f(y0 + 3)} C ${f(x0 + 14)} ${f(y0 + 2)}, ${f(g.x(0.74))} ${f(g.topAt(0.74) - 5)}, ` +
        `${f(g.x(0.84))} ${f(g.topAt(0.84) - 2)}`;
      return {
        back: [softFin(g, 0.42, end, Dt * 0.38, "top")],
        rays: [finRays(g, 0.44, 0.56, Dt * 0.34, "top", 3)],
        extra: thread,
      };
    }
  }
}

function bottomFins(s: FishSpec, g: Geometry): FinSet {
  const Db = g.Db;
  const pelvicAt = s.dorsal === "cat" ? 0.5 : s.dorsal === "shad" ? 0.46 : 0.3;
  const px = g.x(pelvicAt);
  const py = g.bottomAt(pelvicAt);
  const pelvic =
    `M ${f(px - 6)} ${f(py - 5)} Q ${f(px + 2)} ${f(py + Db * 0.42)}, ${f(px + 16)} ${f(py + Db * 0.34)} ` +
    `Q ${f(px + 10)} ${f(py + 4)}, ${f(px + 12)} ${f(py - 5)} Z`;
  const anal: Record<FishSpec["dorsal"], [number, number, number]> = {
    bass: [0.62, 0.77, 0.34],
    split: [0.62, 0.76, 0.34],
    crappie: [0.5, 0.79, 0.5],
    sunfish: [0.57, 0.79, 0.38],
    cat: [0.58, 0.86, 0.3],
    shad: [0.66, 0.88, 0.22],
  };
  const [a0, a1, ah] = anal[s.dorsal];
  return {
    back: [pelvic, softFin(g, a0, a1, Db * ah, "bottom")],
    rays: [finRays(g, a0 + 0.02, a1 - 0.01, Db * ah * 0.9, "bottom", s.dorsal === "cat" ? 6 : 4)],
  };
}

function pectoralFin(s: FishSpec, g: Geometry): string {
  const ox = g.x(s.dorsal === "cat" ? 0.2 : 0.23);
  const oy = CY + g.Db * 0.18;
  const len = g.L * 0.15;
  const w = (g.Dt + g.Db) * 0.13;
  return (
    `M ${f(ox)} ${f(oy - w * 0.5)} ` +
    `C ${f(ox + len * 0.5)} ${f(oy - w * 0.9)}, ${f(ox + len)} ${f(oy - w * 0.2)}, ${f(ox + len)} ${f(oy + w * 0.35)} ` +
    `C ${f(ox + len * 0.6)} ${f(oy + w * 0.9)}, ${f(ox + len * 0.1)} ${f(oy + w * 0.6)}, ${f(ox)} ${f(oy + w * 0.3)} Z`
  );
}

// ---------------------------------------------------------------- face

function mouthPath(s: FishSpec, g: Geometry): string {
  const n: Pt = [NX, CY + (s.flatHead ? 4 : 2)];
  const L = g.L;
  const Db = g.Db;
  switch (s.mouth) {
    case "huge":
      return `M ${f(n[0] + 1)} ${f(n[1])} Q ${f(NX + 0.1 * L)} ${f(CY + 0.22 * Db)}, ${f(NX + 0.19 * L)} ${f(CY + 0.02 * Db)}`;
    case "big":
      return `M ${f(n[0] + 1)} ${f(n[1])} Q ${f(NX + 0.07 * L)} ${f(CY + 0.18 * Db)}, ${f(NX + 0.13 * L)} ${f(CY + 0.04 * Db)}`;
    case "small":
      return `M ${f(n[0] + 1)} ${f(n[1] + 1)} Q ${f(NX + 0.03 * L)} ${f(CY + 0.1 * Db)}, ${f(NX + 0.06 * L)} ${f(CY + 0.05 * Db)}`;
    case "up":
      return `M ${f(n[0] + 1)} ${f(n[1] - 2)} Q ${f(NX + 0.05 * L)} ${f(CY + 0.14 * Db)}, ${f(NX + 0.11 * L)} ${f(CY - 0.06 * g.Dt)}`;
    case "cat":
      return `M ${f(n[0] + 1)} ${f(n[1])} Q ${f(NX + 0.05 * L)} ${f(CY + 0.2 * Db)}, ${f(NX + 0.1 * L)} ${f(CY + 0.14 * Db)}`;
  }
}

function barbels(g: Geometry): string {
  const L = g.L;
  const Db = g.Db;
  return [
    `M ${f(NX + 0.03 * L)} ${f(CY + 2)} C ${f(NX - 0.06 * L)} ${f(CY + 4)}, ${f(NX - 0.06 * L)} ${f(CY + 0.45 * Db)}, ${f(NX + 0.02 * L)} ${f(CY + 0.72 * Db)}`,
    `M ${f(NX + 0.05 * L)} ${f(CY)} C ${f(NX - 0.02 * L)} ${f(CY - 10)}, ${f(NX - 0.07 * L)} ${f(CY - 6)}, ${f(NX - 0.08 * L)} ${f(CY + 6)}`,
    `M ${f(NX + 0.07 * L)} ${f(CY + 0.4 * Db)} q -3 10 2 16`,
    `M ${f(NX + 0.1 * L)} ${f(CY + 0.42 * Db)} q -1 9 5 14`,
  ].join(" ");
}

// ---------------------------------------------------------------- markings

function patternShapes(p: Pattern, s: FishSpec, g: Geometry, rand: () => number) {
  const { L, Dt, Db, x } = g;
  const mark = s.colors.mark;
  switch (p.kind) {
    case "lateral-band": {
      const topEdge: string[] = [];
      const bottomEdge: string[] = [];
      const steps = 16;
      for (let i = 0; i <= steps; i++) {
        const frac = 0.19 + (0.84 * i) / steps;
        const jitter = (rand() - 0.5) * (p.blotchy ? 12 : 7);
        const bulge = p.blotchy && i % 3 === 0 ? 6 : 0;
        topEdge.push(`${f(x(frac))} ${f(CY - 0.14 * Dt + jitter - bulge)}`);
        bottomEdge.unshift(`${f(x(frac))} ${f(CY + 0.12 * Db + (rand() - 0.5) * 7 + bulge)}`);
      }
      return <path d={`M ${topEdge.join(" L ")} L ${bottomEdge.join(" L ")} Z`} fill={mark} opacity={0.72} />;
    }
    case "spots-below": {
      const dots = [];
      for (let row = 0; row < 3; row++) {
        for (let i = 0; i < 12; i++) {
          const frac = 0.3 + i * 0.05 + (row % 2) * 0.025;
          dots.push(
            <circle
              key={`${row}-${i}`}
              cx={f(x(frac))}
              cy={f(CY + 0.26 * Db + row * 0.14 * Db)}
              r={2}
              fill={mark}
              opacity={0.5}
            />,
          );
        }
      }
      return <g>{dots}</g>;
    }
    case "stripes": {
      const lines = [];
      for (let i = 0; i < p.count; i++) {
        const k = (i + 0.5) / p.count; // 0 = top, 1 = bottom
        const y = CY - 0.78 * Dt + k * (0.78 * Dt + 0.62 * Db);
        const sag = (k - 0.5) * 8;
        lines.push(
          <path
            key={i}
            d={`M ${f(x(0.2))} ${f(y + sag)} Q ${f(x(0.62))} ${f(y - sag * 0.3)}, ${f(x(0.99))} ${f(CY + (y - CY) * 0.62)}`}
            stroke={mark}
            strokeWidth={p.width}
            strokeLinecap="round"
            strokeDasharray={p.broken ? "14 6 6 7" : undefined}
            fill="none"
            opacity={p.opacity}
          />,
        );
      }
      return <g>{lines}</g>;
    }
    case "bars": {
      const bars = [];
      for (let i = 0; i < p.count; i++) {
        const frac = 0.28 + (0.6 * i) / Math.max(1, p.count - 1);
        bars.push(
          <rect
            key={i}
            x={f(x(frac) - L * 0.022)}
            y={f(CY - Dt - 4)}
            width={f(L * 0.044)}
            height={f(Dt + Db + 8)}
            rx={6}
            fill={mark}
            opacity={p.opacity}
          />,
        );
      }
      return <g>{bars}</g>;
    }
    case "speckles": {
      const blobs = [];
      for (let i = 0; i < 46; i++) {
        const frac = 0.16 + rand() * 0.84;
        const y = CY - Dt * 0.9 + rand() * (Dt + Db) * 0.9;
        blobs.push(
          <ellipse
            key={i}
            cx={f(x(frac))}
            cy={f(y)}
            rx={f(2 + rand() * 3.5)}
            ry={f(1.6 + rand() * 2.4)}
            fill={mark}
            opacity={0.62}
          />,
        );
      }
      return <g>{blobs}</g>;
    }
    case "dots": {
      const dots = [];
      for (let i = 0; i < 20; i++) {
        const frac = 0.22 + rand() * 0.72;
        const y = CY - Dt * 0.7 + rand() * (Dt * 0.7 + Db * 0.35);
        dots.push(<circle key={i} cx={f(x(frac))} cy={f(y)} r={f(1.4 + rand() * 1.1)} fill={mark} opacity={0.75} />);
      }
      return <g>{dots}</g>;
    }
  }
}

// ---------------------------------------------------------------- component

export function FishArt({
  slug,
  uid,
  className,
  title,
}: {
  slug: string;
  /** Unique per instance when the same fish appears twice on a page. */
  uid?: string;
  className?: string;
  /** Accessible name; omit when the fish's name is already next to it. */
  title?: string;
}) {
  const s = specFor(slug);
  const g = geometry(s);
  const id = `fa-${uid ?? slug}`;
  const rand = rng(slug);
  const dorsal = dorsalFins(s, g);
  const lower = bottomFins(s, g);
  const eyeCx = g.x(s.eye.x);
  const eyeCy = CY - s.eye.y * g.Dt;
  const gillX = g.x(s.dorsal === "cat" ? 0.17 : 0.2);
  const gillTop = g.topAt(s.dorsal === "cat" ? 0.17 : 0.2) + 8;
  const gillBottom = g.bottomAt(s.dorsal === "cat" ? 0.17 : 0.2) - 8;
  const tailFill = s.colors.tail ?? s.colors.fin;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className={className ? `fish-art ${className}` : "fish-art"}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <defs>
        <linearGradient id={`${id}-body`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={s.colors.back} />
          <stop offset="0.48" stopColor={s.colors.side} />
          {s.colors.breast && <stop offset="0.72" stopColor={s.colors.breast} />}
          <stop offset="0.86" stopColor={s.colors.belly} />
        </linearGradient>
        <clipPath id={`${id}-clip`}>
          <path d={g.body} />
        </clipPath>
      </defs>

      <g className="fish-art-swim">
        {/* tail */}
        <g className="fish-art-tail">
          <path d={tailPath(s, g)} fill={tailFill} stroke={INK} strokeWidth={3} strokeLinejoin="round" />
          <path d={tailRays(s, g)} stroke={INK} strokeWidth={1.2} opacity={0.28} fill="none" />
        </g>

        {/* fins behind the body */}
        {[...dorsal.back, ...lower.back].map((d, i) => (
          <path key={i} d={d} fill={s.colors.fin} stroke={INK} strokeWidth={2.6} strokeLinejoin="round" />
        ))}
        {[...dorsal.rays, ...lower.rays].map((d, i) => (
          <path key={`r${i}`} d={d} stroke={INK} strokeWidth={1.1} opacity={0.3} fill="none" />
        ))}
        {dorsal.extra && (
          <path d={dorsal.extra} stroke={INK} strokeWidth={2.2} fill="none" strokeLinecap="round" />
        )}

        {/* body, markings clipped to it, then the outline on top */}
        <path d={g.body} fill={`url(#${id}-body)`} />
        <g clipPath={`url(#${id}-clip)`}>
          {s.patterns.map((p, i) => (
            <g key={i}>{patternShapes(p, s, g, rand)}</g>
          ))}
          {s.dorsalSpot && (
            <ellipse cx={f(g.x(0.76))} cy={f(g.topAt(0.76) + 5)} rx={7} ry={5} fill={s.colors.mark} opacity={0.8} />
          )}
          {/* comic sheen */}
          <ellipse
            cx={f(g.x(0.46))}
            cy={f(CY - g.Dt * 0.52)}
            rx={f(g.L * 0.3)}
            ry={f(g.Dt * 0.14)}
            fill="#fff"
            opacity={0.2}
          />
        </g>
        <path d={g.outline} fill="none" stroke={INK} strokeWidth={3.2} strokeLinejoin="round" strokeLinecap="round" />

        {/* gill cover */}
        <path
          d={`M ${f(gillX)} ${f(gillTop)} Q ${f(gillX + g.L * 0.055)} ${f(CY + 4)}, ${f(gillX - 2)} ${f(gillBottom)}`}
          stroke={INK}
          strokeWidth={2.2}
          fill="none"
          strokeLinecap="round"
          opacity={0.7}
        />
        {s.earFlap && (
          <path
            d={`M ${f(gillX - 2)} ${f(CY - g.Dt * 0.3)} q ${f(g.L * 0.1)} -4 ${f(g.L * 0.09)} ${f(g.Dt * 0.22)} q -2 ${f(g.Dt * 0.16)} ${f(-g.L * 0.08)} ${f(g.Dt * 0.12)} Z`}
            fill={INK}
          />
        )}
        {s.shoulderSpot && (
          <circle cx={f(g.x(0.27))} cy={f(CY - g.Dt * 0.34)} r={f((g.Dt + g.Db) * 0.07)} fill={s.colors.mark} />
        )}

        {/* pectoral fin sits on the body */}
        <path d={pectoralFin(s, g)} fill={s.colors.fin} stroke={INK} strokeWidth={2.2} strokeLinejoin="round" opacity={0.95} />

        {/* face */}
        <path d={mouthPath(s, g)} stroke={INK} strokeWidth={2.6} fill="none" strokeLinecap="round" />
        {s.barbels && <path d={barbels(g)} stroke={INK} strokeWidth={2.2} fill="none" strokeLinecap="round" />}
        <circle cx={f(eyeCx)} cy={f(eyeCy)} r={s.eye.r} fill="#fff" stroke={INK} strokeWidth={2.2} />
        <circle cx={f(eyeCx)} cy={f(eyeCy)} r={f(s.eye.r * 0.7)} fill={s.eye.iris} />
        <circle cx={f(eyeCx + s.eye.r * 0.05)} cy={f(eyeCy)} r={f(s.eye.r * 0.44)} fill={INK} />
        <circle cx={f(eyeCx - s.eye.r * 0.22)} cy={f(eyeCy - s.eye.r * 0.28)} r={f(s.eye.r * 0.2)} fill="#fff" />
      </g>
    </svg>
  );
}
