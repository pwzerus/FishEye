// Copies MapLibre's map worker into public/, where the page can load it.
//
// MapLibre 6 (ESM only) finds its worker next to its own file. Bundled by
// Next.js, that is a chunk under /_next/static, where the worker isn't, so
// the vector map failed with "Worker failed to load". BaseMap.tsx points
// MapLibre at this copy (setWorkerUrl). Runs before `next dev` and
// `next build` (package.json), so the copy always matches the installed
// version; public/maplibre/ is git-ignored.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
mkdirSync(join(root, "public", "maplibre"), { recursive: true });
copyFileSync(
  join(root, "node_modules", "maplibre-gl", "dist", "maplibre-gl-worker.mjs"),
  join(root, "public", "maplibre", "maplibre-gl-worker.mjs"),
);
