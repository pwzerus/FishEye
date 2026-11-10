import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { ImageResponse } from "next/og";

/** The size every link preview is drawn at: what Facebook, Reddit, X,
 * WeChat and iMessage all crop well. */
export const OG_SIZE = { width: 1200, height: 630 };

let mark: Promise<string> | null = null;

/** The FishEye mark (public/brand), as a data URI the renderer can draw. */
function brandMark(): Promise<string> {
  mark ??= readFile(join(process.cwd(), "public/brand/fisheye-mark.svg")).then(
    (svg) => `data:image/svg+xml;base64,${svg.toString("base64")}`,
  );
  return mark;
}

/**
 * The picture a shared link shows: the mark, a headline and a line under it,
 * on the site's own colours. In English: a preview is drawn once and shown
 * to whoever sees the link, whatever their language, and the default font
 * has Latin letters only.
 */
export async function ogCard({ title, subtitle, eyebrow }: { title: string; subtitle: string; eyebrow?: string }) {
  const src = await brandMark();
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "64px 72px",
          background: "linear-gradient(135deg, #f7f8f2 0%, #e3f3f0 55%, #c9e8e4 100%)",
          color: "#0f2530",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {/* eslint-disable-next-line @next/next/no-img-element -- drawn by next/og, not the browser */}
          <img src={src} width={76} height={76} alt="" />
          <span style={{ fontSize: 44, fontWeight: 700, color: "#0b5d7a" }}>FishEye</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          {eyebrow && (
            <span style={{ fontSize: 28, color: "#0a7f84", textTransform: "uppercase", letterSpacing: 2 }}>{eyebrow}</span>
          )}
          <span style={{ fontSize: title.length > 28 ? 68 : 84, fontWeight: 700, lineHeight: 1.05 }}>{title}</span>
          <span style={{ fontSize: 34, color: "#33505c", lineHeight: 1.3, maxWidth: 1000 }}>{subtitle}</span>
        </div>
        <span style={{ fontSize: 26, color: "#0a7f84" }}>Free · learn to fish, from your first cast</span>
      </div>
    ),
    OG_SIZE,
  );
}
