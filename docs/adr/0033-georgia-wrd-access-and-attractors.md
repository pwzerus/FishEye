# ADR 0033: Georgia WRD's access sites and fish attractors

## Status
Accepted. Georgia's counterpart of ADR 0022 (TPWD's lakes and ramps).

## Context

Georgia's lakes came only from OpenStreetMap (unverified, access unknown)
plus GBIF records. Georgia's Wildlife Resources Division (WRD) publishes two
map layers as public ArcGIS feature services, used by its own fishing
forecasts and its "Interactive Map of Fishing Areas":

- **WRD_Water_Access_Points** (895 rows): boat ramps, piers and bank-fishing
  sites, each with its lake's name, type (major reservoir, small
  impoundment, river, trout stream, coast), status, county, acreage, and a
  Y/N flag for 44 fish species.
- **Fish_Attractors_View** (1,848 rows of activity "attractor"): brush piles,
  PVC trees, stake beds, pallets and so on, with type, placement date and
  depth.

Both layers carry no copyright or licence text. They are used for facts
only (where, what kind, which species, when placed); none of WRD's text,
photos or maps is copied, and every lake links back to WRD. Writing to WRD
for written permission is still the safe step before commercial use.

## Decision

`app/data_import/ga_wrd_import.py`, run after the Georgia OSM import:

- **Sites kept**: listed public, status Open, on a major reservoir or small
  impoundment. Closed, status unknown, not public, rivers, trout streams and
  the coast are counted and left out.
- **Finding the lake**: an OSM lake whose box (plus 300 m) holds the site
  and whose name matches WRD's lake name or site name ("A.H. Stephens SP -
  Lake Buncombe" -> "Lake Buncombe"). Failing that, the only lake whose box
  holds the site, but only if it doesn't look private (ADR 0032) and its
  box is 0.5-20x the acreage WRD gives. Several lakes and no name: listed,
  not guessed. No lake near: a lake already in the database under that name
  within the lake's search radius; otherwise a new lake at the median of
  WRD's sites ("sites", as TPWD's "ramps").
- **Add or confirm, never duplicate**: a site within 150 m of a confirmed
  access point is skipped. An OpenStreetMap entrance within 150 m is the
  same place, now confirmed by WRD: it is replaced by WRD's point. Farther
  OSM entrances stay, labelled unverified.
- **The lake** becomes verified and open, with WRD's guide species linked
  as confirmed (evidence names the sites), and an AgencyLakeProfile
  (agency `ga_wrd`): WRD's name for the lake, counties, acreage, its full
  species list as WRD names them, and the fishing forecast link for the 32
  lakes WRD writes one for (major reservoirs, or 200+ acres, so a pond
  called "Jackson" never gets Lake Jackson's forecast).
- **Attractors**: a new `fish_attractors` table, matched to the lake whose
  box holds them (a matching name first, then the smallest box), replaced
  wholesale on every run. Shown on the lake map as teal dots with type,
  year and depth, and as a count in the panel; never on a closed lake.
  Their year is shown because an old brush pile may have broken down.

The fetch needs the network (two layers, 1,000 rows a page); the import is
offline from the saved `ga_wrd_cache/`, like the other importers.

## Known gaps

- Not yet run against the full layers: the workspace this was written in
  can't reach ArcGIS. Tests use rows shaped like the real ones. The first
  real run's summary (unplaced sites, attractors outside every lake) is the
  check; fix with name aliases like TPWD's if needed.
- WRD's "spotted bass" flag is linked to the Spotted Bass guide. In several
  Georgia reservoirs that fish is now the Alabama bass.
- A lake's box is a rough shape: an attractor in a cove of a big reservoir
  can land on a small pond whose box overlaps it, when the names don't help.
