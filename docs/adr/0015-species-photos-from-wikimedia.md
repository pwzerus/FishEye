# ADR 0015: Real fish photos from Wikimedia, fetched at runtime

## Status
Accepted.

## Context

The fish guide pages pair an original illustration (drawn in the frontend
as SVG) with a real photograph. The illustration makes the page friendly;
the photo is what a beginner holding a fish actually compares against.
Photos need a licence that allows reuse, and attribution when that licence
requires it.

## Decision

`GET /api/species/photos` returns, per species, the lead image of its
English Wikipedia article, only if freely licensed:

- `prop=pageimages&pilicense=free` asks Wikipedia for free lead images
  only; the licence is checked again from Commons' `extmetadata` (the one
  mistake here that isn't cosmetic is showing a non-free photo).
- Author, licence name and the file page are returned with every photo, and
  the UI prints them under it. CC BY / BY-SA require that.
- All twelve species resolve in two batched requests (titles are
  pipe-joined), following redirects.
- Same adapter shape as NWS / Nominatim: timeout, one retry, circuit
  breaker, 7-day cache (1 day for "article has no free image"). On failure
  the photo is `null` — never a placeholder — and the page shows the
  illustration alone.
- `SPECIES_PHOTOS_ENABLED=false` turns it off entirely (no calls).

Why not download the images into the repo: no binaries in git, and no
licence review to redo by hand when an article's image changes.

## Consequences

- The fish pages depend on Wikipedia for photos; the guides themselves
  don't (separate endpoint, fetched independently).
- The images are hot-linked from upload.wikimedia.org by the browser,
  which Wikimedia permits.
- Commercial use: CC BY-SA photos can be used commercially with attribution
  and share-alike on the image itself; see docs/commercialization.md.
