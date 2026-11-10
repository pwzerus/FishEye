import { headers } from "next/headers";

/**
 * The address the site is being visited at, for the absolute links that
 * the sitemap, robots.txt and link previews need ("https://…/fish/…").
 *
 * Read from the request, so it is right on the server, on a laptop and
 * behind Caddy alike without another setting: Caddy passes the visitor's
 * Host and sets X-Forwarded-Proto. NEXT_PUBLIC_API_BASE_URL is the
 * fallback; in production it is the site's own address (Caddy routes /api).
 */
export async function siteOrigin(): Promise<string> {
  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host");
  if (host && /^[a-z0-9.-]+(:\d+)?$/i.test(host)) {
    const proto = h.get("x-forwarded-proto")?.split(",")[0].trim();
    const scheme = proto === "http" || proto === "https" ? proto : host.startsWith("localhost") ? "http" : "https";
    return `${scheme}://${host}`;
  }
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:3000").replace(/\/+$/, "");
}
