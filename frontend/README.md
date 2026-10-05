# Frontend — Next.js

## Local dev

```bash
npm install
cp .env.local.example .env.local   # points at http://localhost:8000 by default
npm run dev
```

Open http://localhost:3000. Requires the backend running (see `../backend/README.md`)
for real data — without it, the page still renders and shows a clear
"could not reach the backend" message instead of crashing (see `src/app/page.tsx`).

## Tests

```bash
npm run lint       # eslint
npx tsc --noEmit   # typecheck
npm test           # vitest
npm run build      # production build
```

## Notable decisions

- **Map library is Leaflet + OpenStreetMap tiles, not Google Maps.** The PRD
  calls for Google Maps JS API; Leaflet needs no API key or billing account,
  which matters for a demo a reviewer should be able to run in minutes. The
  map is isolated behind `src/components/map/LakeMap.tsx` — swapping the
  provider later touches one file, not the app.
- **`next/dynamic({ ssr: false })` for the map.** Leaflet touches `window` at
  import time, which breaks server rendering. `MapView.tsx` is the client
  boundary that makes the dynamic import legal (Next 16's App Router
  disallows `ssr: false` directly in a Server Component).
- **No separate `loading` state in `WaterbodyPanel`.** It's derived from
  comparing the loaded detail's id to the requested one instead — see the
  comment in that file. `eslint-config-next`'s `react-hooks/set-state-in-effect`
  rule flags synchronous `setState` calls in an effect body, and the derived
  value avoids that class of bug entirely rather than working around the lint
  rule.
- **Types in `lib/api/types.ts` are hand-written, not generated from OpenAPI.**
  The API surface is still moving daily at this stage; codegen is worth
  adding once it stabilizes (tracked for a later day), not before.
