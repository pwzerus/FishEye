import type { NextConfig } from "next";

// On every page (the API sets its own: backend app/main.py). No page is meant
// to be framed, which is what clickjacking needs; the browser is told to
// trust each file's declared type; links to other sites carry only the
// origin; and of the browser's powers, only location is ever asked for ("Use
// my location"). The CSP leaves scripts, styles and images alone (map tiles
// and fish photos come from other hosts): it only rules out framing, a
// changed <base>, plugins and forms posting elsewhere.
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'" },
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
