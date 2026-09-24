# ADR 0009: Location search — a backend geocoding proxy over Nominatim

## Context

The map only ever showed the handful of hand-verified lakes seeded for the
demo (7 at last count), all in Texas, with no way to search for a place or
recenter on the user's own location. That's fine for a scripted demo walk-
through, but it doesn't survive the obvious next question: what happens
when someone opens this somewhere other than Texas?

Two separate problems hide inside "make the map not just show 7 lakes":

1. **The search/locate interaction itself** — an address box and a "use my
   location" button, and the map reacting to either. This is buildable now
   and doesn't depend on how much data the backend has.
2. **Data coverage** — the database only has hand-verified Texas lakes.
   Searching Chicago will correctly find nothing, because there is nothing
   to find, not because the search is broken. This ADR is about (1) only;
   (2) is a separate, larger project (more state DNR scrapers, or a
   generic OSM water-body overlay) and isn't solved here — the empty-state
   message in MapView.tsx says so explicitly rather than pretending
   otherwise.

## Decision: geocode through this app's own backend, never from the browser

A geocoder turns free text ("Lake Fork, TX") into coordinates. The natural-
seeming choice — call a public geocoding API directly from the browser — is
wrong for the specific provider this project can afford (Nominatim, chosen
for the same reason NWS was chosen for weather: free, keyless, and this is
a portfolio/demo project, not a funded product):

**Nominatim's usage policy explicitly disallows exactly this app's future
shape.** Its policy
(<https://operations.osmfoundation.org/policies/nominatim/>) is written for
"light, user-initiated queries" from a small number of clients, with a
1-request-per-second hard cap, mandatory caching, and specific language
that a *distributed app* — many independent clients each hitting the
public endpoint — is not the intended use. That's not a hypothetical
concern raised while scoping this: it's precisely what "put this on the App
Store" would produce, since every installed copy would otherwise be its
own independent client.

The fix isn't a different provider yet — it's an architectural boundary:
**the frontend never calls Nominatim. It calls this app's own
`GET /api/geocode`, which calls Nominatim.** This one change gets three
things for free:

- **Request volume decouples from user count.** What actually reaches
  Nominatim depends on how many *distinct, uncached* place names get
  searched — not how many people are searching them. A hundred users
  searching "Lake Fork" the same week is one live Nominatim call and
  ninety-nine cache hits (see `app/services/geocoding.py`'s cache, TTL 30
  days — coordinates don't go stale the way a weather forecast does).
  This is what turns "many users" back into the "light usage" shape the
  policy asks for.
- **The rate cap is enforceable in one place.** `_throttle()` in
  `geocoding.py` enforces Nominatim's 1-req/sec cap process-wide, which is
  only possible because there's a single process making the calls.
- **Swapping providers later costs one file.** If this ever needs Google
  Places or Mapbox (real UX upgrades: autocomplete-as-you-type, better
  coverage), only `geocoding.py`'s internals change. The frontend, the API
  contract, and the App Store binary are all untouched — the same
  provider-behind-a-boundary shape as the LLM (ADR 0007) and weather
  adapters, just enforced by a network boundary instead of an ABC, since
  there's only one plausible free provider today and no swapping
  motivation yet to justify a `GeocodingProvider` interface nobody would
  implement a second time.

## Implementation

`app/services/geocoding.py` — same PRD §17 reliability shape as
`weather_adapter.py` (timeout, retry, circuit breaker, cache, fallback),
with one deliberate difference: **no fabricated fallback value.** Weather's
fallback is a clearly-marked placeholder snapshot, because "conditions
unknown" is itself a valid, honest thing to score against. There's no
equivalent honest placeholder for "where is this place" — inventing
coordinates would be exactly the kind of fabrication this project's design
refuses to do elsewhere (the TPWD scraper, `ai_advisor.py`'s grounding
checks). So a Nominatim outage raises `GeocodingUnavailable`, which the API
layer turns into a 503 — distinct from a 404, which means "checked, no such
place." Conflating the two would tell someone "no such place" when the
truth is "couldn't check right now," which is a worse and more misleading
answer to give someone trying to find a lake.

`GET /api/geocode?q=...` — the only thing in this app allowed to talk to
Nominatim. Requests are scoped to `countrycodes=us` (matches the PRD's own
scope: US freshwater fishing for beginners).

Frontend: `LocationSearchBar.tsx` (address box + "use my location", the
latter via the browser's own Geolocation API — no geocoding needed for
that path at all) feeds a resolved point up to `MapView.tsx`, which
re-queries `GET /api/waterbodies?lat=&lng=&radius_km=` (a filter the
backend already had, per the PRD's own API draft; the map just never used
it that way) and re-centers the map (`LakeMap.tsx`'s `FitToView`, which
fits to markers when there are any, or flies to the searched point when
there aren't — see the empty-state banner for that second case).

## Consequences

- Searching outside the seeded lakes' area correctly returns nothing, and
  says so plainly. This ADR does not attempt to fix that — see (2) above.
- The public Nominatim instance is still a shared, best-effort community
  resource. Real production traffic at real scale would still eventually
  need self-hosting or a paid provider; this ADR buys correctness at
  today's usage level and a cheap swap path, not a permanent exemption from
  ever having to revisit this.
- No API key, no billing account, no secret to keep out of the frontend
  repo for this feature — consistent with every other external integration
  in this codebase so far (NWS, TPWD, the mock LLM).
