import type { NextConfig } from "next";

// The hosts a page may fetch from besides its own: the API (another origin
// only locally) and the map's styles, tiles, fonts and icons. A new map
// provider set through these variables is let in by setting it.
function origins(...urls: (string | undefined)[]): string[] {
  const out = new Set<string>();
  for (const url of urls) {
    try {
      if (url) out.add(new URL(url.replace(/\{[a-z]\}/g, "a")).origin);
    } catch {
      // Not a URL: nothing to allow.
    }
  }
  return [...out];
}
const connect = origins(
  process.env.NEXT_PUBLIC_API_BASE_URL,
  process.env.NEXT_PUBLIC_MAP_STYLE_URL,
  process.env.NEXT_PUBLIC_PLAIN_STYLE_URL || "https://tiles.openfreemap.org/styles/liberty",
  process.env.NEXT_PUBLIC_TILE_URL,
);

// Production pages may run only FishEye's own scripts and talk only to
// FishEye and the map hosts, so an injected script can neither load more
// code from elsewhere nor send what it reads anywhere. Inline scripts stay
// allowed: Next.js writes its page data inline. Photos and raster tiles
// are images from several hosts, so images may come from any https host.
// MapLibre's worker is a file of ours (scripts/copy-maplibre-worker.mjs),
// or a blob: copy of it. `next dev` keeps the short policy: its live
// reload needs eval and a websocket.
const strictPolicy = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  `connect-src 'self' ${connect.join(" ")}`.trim(),
  "worker-src 'self' blob:",
  "manifest-src 'self'",
  "frame-src 'none'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "object-src 'none'",
  "form-action 'self'",
].join("; ");
const shortPolicy = "frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'";

// On every page (the API sets its own: backend app/main.py). No page is meant
// to be framed, which is what clickjacking needs; the browser is told to
// trust each file's declared type; links to other sites carry only the
// origin; and of the browser's powers, only location is ever asked for ("Use
// my location").
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: process.env.NODE_ENV === "production" ? strictPolicy : shortPolicy },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), payment=(), usb=(), geolocation=(self)" },
];
// HSTS once the site is on HTTPS (the API's public address is the site's,
// baked in at build time: docker-compose.prod.yml).
if (process.env.NEXT_PUBLIC_API_BASE_URL?.startsWith("https://")) {
  securityHeaders.push({ key: "Strict-Transport-Security", value: "max-age=31536000" });
}

const nextConfig: NextConfig = {
  // Emit a self-contained server (.next/standalone) with only the
  // node_modules it actually uses, so the Docker image doesn't ship the
  // whole dev toolchain. `npm run dev` and `npm run build` are unaffected.
  output: "standalone",
  // No "X-Powered-By: Next.js": it tells nobody anything they need.
  poweredByHeader: false,
  // The site doesn't use next/image (photos come from the API, logos are
  // SVG), so its image optimizer (/_next/image) is turned off: an endpoint
  // nothing needs, where Next.js has had SSRF and remote-code-execution
  // holes (GHSA-cjq9-62q9-8jv4, GHSA-2464-fhr4-w9xw; fixed in 16.4.3).
  images: { unoptimized: true },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
