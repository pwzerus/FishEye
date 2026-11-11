import type { MetadataRoute } from "next";

/**
 * What a phone needs to keep FishEye on its home screen as an app: its own
 * icon, its own window without the browser's bars, and the cream the pages
 * are drawn on while it opens. iPhones read the same page's apple-icon.png
 * and appleWebApp tags (app/layout.tsx). The icons are the apple icon's fish
 * at 192 and 512 pixels; the maskable one keeps the fish inside the circle
 * Android may crop it to.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "FishEye",
    short_name: "FishEye",
    description: "Find water to fish, learn the fish, and share your catch.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#f7f8f2",
    theme_color: "#f7f8f2",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
