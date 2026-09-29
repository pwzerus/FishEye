# ADR 0019: Keep the largest lakes when a map view holds too many

## Status
Accepted. Follows ADR 0018, whose last consequence was that the API had no
answer for a view holding far more lakes than the map can show.

## Context

The map asks for the lakes in its viewport with `limit=2000`. That was
harmless at Texas scale. At national scale a viewport a few degrees wide over
Minnesota matches about 150,000 lakes, and two things in `list_waterbodies`
were wrong for it — neither visible until there was that much data:

1. **The limit was applied in Python.** The endpoint loaded every match into
   memory, ordered them, and sliced. Measured against a million synthetic
   waterbodies (the same set as ADR 0018):

   | view | matched | old endpoint | peak memory |
   |---|---|---|---|
   | lower 48 | 905,450 | 34.2 s | 1.6 GB |
   | Minnesota (~7°) | 152,017 | 6.0 s | 269 MB |

2. **"The first 2000" meant the first 2000 by name.** Verified lakes were
   sorted first, then everything else alphabetically. Truncating that keeps
   the lakes whose names begin with A, B and C — a scatter with no meaning —
   and drops a 40 km² reservoir in favour of a pond called "Aspen Pond".

The frontend already has part of the answer: below zoom 8 it asks for
verified lakes only (`MIN_ZOOM_FOR_ALL_LAKES`), and it shows a chip when a
response reaches its limit. So the national zoom-out is handled there. What
was not handled is zoom 8 and above in a dense region, which is where a view
can still match 150,000 rows.

## Decision

Verified lakes are always kept, first. The rest are ranked by size and the
largest fill the remaining room. The limit is applied in the database.

- `waterbodies.extent_km2` — bounding-box area in km², written by the OSM
  importer from the bounds it already fetches. A size proxy used only to
  rank; a long thin reservoir overstates itself, which is fine for ranking.
  `0` for verified rows (never ranked) and for OSM rows imported before the
  column existed (they rank last until the importer is re-run).
- The endpoint runs two queries — verified, then non-verified ordered by
  `extent_km2 DESC` — each with a SQL `LIMIT`. Not one query ordered by
  `(tier, size)`: a composite sort cannot use an index, so it would sort
  every match in view to keep two thousand.
- `ix_waterbodies_verified_lat_lng`, a partial index over verified rows only.
  Verified is ~0.5% of the table; without it the "verified in view" query
  scans the whole `(latitude, longitude)` index and discards the rest —
  114 ms at a million rows against 5.8 ms with it.
- `ix_waterbodies_extent` on `extent_km2 DESC` serves the ranked half.

Measured after, same data, same 2,000-row limit:

| view | new endpoint |
|---|---|
| lower 48 | 67 ms |
| Minnesota (~7°) | 73 ms |
| metro (~1°) | 80 ms |

No new API surface. The frontend already infers truncation from a response
that reaches its limit; only the chip's wording changes, from "the first
2000" to "the largest 2000".

`app/db/upgrades.py` adds the column and both indexes to a database built
before them, on every startup, idempotently. `create_all` never alters an
existing table, and the project has no migration tool, so without this every
developer's populated database would fail with "no such column" on the first
map request. On the million-row table the upgrade takes 0.7 s.

## Consequences

- A request's cost now tracks the limit rather than the number of matches.
- What gets dropped from a crowded view is the smallest ponds. Sensible, but
  worth knowing: in a city with 2,600 mapped ponds, the small park pond that
  ADR 0010 calls "often the best beginner spot there is" is what a wide view
  leaves out until the person zooms in.
- Selection is by size alone, so it follows where the big lakes are. A view
  straddling a lake-dense area and an empty one fills with the dense side's
  biggest lakes. Even coverage would need per-grid-cell selection, which has
  to scan every match to assign cells (measured at 1.25 s for the national
  view); it is not worth it until this proves a problem.
- Existing OSM rows have `extent_km2 = 0` until the importer is re-run, so
  they tie and fall back to name order — the previous behaviour — rather than
  break.
- Not fixed here: verified markers are never clustered on the map ("there are
  few of them"). That holds while it is true. See the note in `LakeMap.tsx`.

## Alternatives considered

- **Also cap by viewport span in the API** (return no OSM lakes for a
  continental view). Redundant: the frontend's zoom gate already does this,
  and a second rule in the API for the same case can only disagree with it.
- **Server-side grid aggregation** (one bubble per cell, with counts). The
  honest answer for a national overview, but measured at 1.25 s per request
  for the lower 48 without precomputation, and precomputing per zoom level is
  new infrastructure. Revisit if a national overview becomes a product goal.
- **A `total` count in the response** so the chip could say "2,000 of
  152,017". A `COUNT(*)` over the view is 100 ms at the national view, paid
  on every pan for a number the chip does not need to be truthful.
- **A generated or computed rank at query time** instead of a stored column:
  the area is a property of the OSM geometry, which is not kept after import.
