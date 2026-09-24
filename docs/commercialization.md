# Commercialization plan: licences and data use

Agreed 2026-09-24. This is the order FishMate follows if it moves beyond a
portfolio project. It isn't legal advice; stage 3 exists because a lawyer
has to review it before anything is charged for or published to an app store.

## Stage 1: now (portfolio)

Nothing has to change. One thing is done now because it's cheap now and
expensive later:

- [x] **Keep the licence on every GBIF record** (`species_occurrences.license`,
  ADR 0012). Non-commercial records can then be switched off with one
  setting (`GBIF_EXCLUDE_NONCOMMERCIAL=true`) without re-importing.

## Stage 2: before launch

| Component | Problem | Action |
|---|---|---|
| Map tiles (`tile.openstreetmap.org`) | The OSMF tile policy allows commercial use, but says commercial services' access "may be withdrawn at any point". Heavy use is expected to go elsewhere. | Move to a tile provider (MapTiler, Stadia, Thunderforest, Mapbox…) or self-host. One URL and the attribution line in `LakeMap.tsx` / `LakeDetailMap.tsx`. Budget for it. |
| Geocoding (public Nominatim) | The public instance isn't for production traffic. | Self-host Nominatim (US extract) or use a paid geocoder. Only `backend/app/services/geocoding.py` changes; the frontend already goes through `/api/geocode` (ADR 0009). |
| GBIF records | About 12% of matched Texas records are CC BY-NC (mostly iNaturalist). 128 of 469 covered lakes rely on them alone. | Set `GBIF_EXCLUDE_NONCOMMERCIAL=true`. Cite GBIF with a download DOI (GBIF download API) rather than the search API. |
| TPWD text | Facts (which fish are in a lake) aren't copyrightable, but the scraper stores sentences from TPWD reports as evidence. | Replace them with our own paraphrase plus a link, or keep only short quotes. Keep the scraper polite (robots.txt, low rate). |
| Attribution page | Several sources require visible credit. | Add a "Data sources and licences" page: OpenStreetMap (ODbL), GBIF and its datasets, TPWD, NWS, tile provider. |

## Stage 3: before charging or publishing to an app store

- **Legal review**, focusing on:
  - ODbL: keep OSM-derived data (the lake list, OSM entrances) separate from
    our own data (species evidence, scores, guides, future community pins),
    per the OSM Collective Database Guideline. Showing the map in the app is
    a Produced Work and only needs attribution. Publishing a database that
    mixes OSM data with our changes (an open API, a data download) would
    have to be ODbL. Never write user data into the OSM-derived columns.
  - Terms of service and a privacy policy. Community pins will collect
    location and photos, which is a bigger risk than any data licence.
- **react-leaflet** is under the Hippocratic License 2.1, an "ethical source"
  licence that isn't OSI-approved. Normal use of a fishing app doesn't
  conflict with it, but some legal teams reject it. Fallback: use Leaflet
  directly (BSD-2-Clause). Medium effort.

## Already fine for commercial use

- Leaflet (BSD-2-Clause); Next.js, React, react-leaflet-cluster,
  leaflet.markercluster (MIT).
- NWS weather: US government data, public domain (credit it anyway).
- Poppins font: SIL Open Font License.
- Species guides: our own paraphrased text, every setup cited.
- The FishMate logo: original.
- An LLM provider, when one is added: subject to that provider's commercial
  terms.

## Sources

- [OSMF Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/)
- [OSMF Licence and Legal FAQ](https://osmfoundation.org/wiki/Licence/Licence_and_Legal_FAQ)
- [OSM Collective Database Guideline](https://wiki.openstreetmap.org/wiki/Collective_Database_Guideline)
- [OSM Produced Work Guideline](https://osmfoundation.org/wiki/Licence/Community_Guidelines/Produced_Work_-_Guideline)
- [OSM Attribution Guidelines](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines)
- [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)
- GBIF licence breakdown: `docs/experiments/2026-09-24-gbif-texas-coverage.md`
