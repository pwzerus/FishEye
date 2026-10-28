# ADR 0037: Bait and tackle shops on the map; catches with a photo check

## Status
Accepted. Built and measured locally on 2026-10-27; not deployed. Catches
(ADR 0016's community pins) are switched on (`lib/features.ts`).

## Context

Two asks from the product owner, 2026-10-27:
1. Show bait and tackle shops near the water on the map.
2. Make Catches work like Fishbrain's: at the lake, drop a pin, take a photo
   of the fish, and share it; the app must check that the photo shows the
   fish the angler names ("a catfish posted as a bass must not go up"); and
   the account page shows where you have pinned.

Pins, photos, moderation and reports existed (ADR 0016) but were paused.

## Decision

### Shops
- From the Geofabrik OpenStreetMap extracts already cached for the lakes,
  offline (`data_import/tackle_shops.py`; data-sourcing rules: no bulk
  Overpass). What counts is in the module's docstring: shops tagged fishing
  or bait, gear shops tagged or named for fishing, any shop named for bait or
  tackle, and the three fishing retailers by `brand`. "Outfitters" alone does
  not count (in Georgia most are clothing). 1,292 shops in 51 states.
- One table, `tackle_shops`, keyed on the OSM element;
  `/api/shops?bbox=&state_code=` for the map, `/api/shops/near?lat=&lng=` for
  a lake's three nearest.
- On the map: a purple rounded square (not a lake's teardrop or a catch's
  badge), from zoom 8 in the state being explored, on by default with a
  "Bait & tackle" toggle; the popup has kind, name, address, hours, call,
  website, a directions link, and the ODbL credit with a link to the element.
  A lake's Entrances tab lists the nearest three with straight-line miles.

### The photo check
- **Model**: BioCLIP 2 (imageomics/bioclip-2, MIT; a CLIP ViT-L/14 trained on
  the tree of life, 2025), exported to ONNX and compressed to int8 (309 MB),
  run with the onnxruntime the API already has. No PyTorch on the server;
  the model is built on a developer's machine (`cli/build_fish_id_model.py`).
  Chosen over the first BioCLIP (ViT-B/16, 89 MB) after measuring both
  (below): it is four times slower and three times bigger, and much more
  accurate. BioCLIP stays buildable (`--model bioclip`) for a smaller server.
- **Classes** (`services/fish_id_classes.py`): the 18 guide species with a
  class (the hybrid striped bass is checked as "a white or striped bass"),
  32 fish with no guide (walleye, pike, gar, bullheads, other sunfish and
  trout, other carp…), and not-fish (people, dogs, turtles, scenes).
  Without the other fish, a walleye would come out as whichever guide
  species it looks least unlike.
- **Groups** of fish photos often can't tell apart, guide species and fish
  with no guide alike: black bass; white and striped bass; channel and blue
  catfish with the bullheads; crappie; the sunfish; shad; trout; carp.
- **A classifier head** fitted on 2015–2023 iNaturalist photos (CC0 / CC BY
  via GBIF; `cli/fish_id_train.py`), starting from the zero-shot weights and
  pulled towards them; the pull and the thresholds are chosen on each
  species' newest fifth of training observations, never on the test set.
- **Policy** (`services/fish_id.check_claim`): the photo is read twice
  (middle square, whole photo padded; mirrored copies too were measured no
  more accurate, at twice the time). Whether there is a
  fish comes from all classes; which fish, from the fish alone (a catch
  photo is often mostly the angler). The claim is *confirmed* when it is the
  likeliest fish with 80% of the fish probability, accepted *as its group*
  when the likeliest fish is in its group and the group has 80% (the pin
  then says "the photo shows a black bass; which kind is the angler's
  call"), and refused otherwise: a different fish (named, with a one-click
  "Change to …"), a fish with no guide ("choose Other"), no fish, or a photo
  too unclear to say. Every refusal also offers "Share without naming the
  fish": never a dead end.
- **Where it runs**: the catch form asks `/api/fish-id` as soon as a photo
  is chosen, fills in the fish it shows, and shows the verdict before
  anything is saved. Saving checks again on the server and never trusts the
  form (the same photo is read once: its vector is kept by hash); so does
  changing a pin's species later; the checked photo can't be removed while a
  species is named. "Other: largemouth bass" is checked as the guide species.
- **Off and missing**: `FISH_ID=off` (tests, CI) skips the check. On, a
  missing model refuses catches that name a fish (503) instead of letting
  them go up unchecked; the rest of the site is unaffected.

### The catch flow
- "Share catch" on the map, "Pin where I am" (or tap the map), photo first,
  then the fish (filled in), date (from the photo's EXIF when it has one,
  read on the device), title (defaults to the fish), notes, public/only me.
  A photo taken somewhere else offers "Move the pin there".
- The pin shows "✓ Photo-checked" (or the group) on cards, its page, the map
  popup and the admin lists. A public catch has a Share button. The account
  page's "My catches" has a map of every pin.
- **Browsed by place, never one nationwide pile** (added 2026-10-28, asked
  for by the product owner): the community page goes All states → a state →
  a county → a lake, each level listing the places below it with their
  number of catches; a state's or county's catches are listed under it.
  "Near me" opens the county you are in (`/api/pins/where`, not stored);
  with location already allowed it opens there by itself, otherwise it
  starts at the link's place, the last place browsed, or the state chosen
  on the map. A catch's state and county come from the Census county
  outlines (public domain, `services/counties.py`) when it is saved;
  catches saved before get theirs at startup. Counts are over the catches
  the viewer may see, so a private pin is never counted for anyone else.

## Measured

Test photos: 1,315 research-grade iNaturalist observations from 2024 on
(after both models' training data), 814 of guide species and 501 of fish
with no guide; never used for fitting or for choosing thresholds. Every
photo is checked against every claim an angler could make (19 species).
Full report: `reports/fish-id-eval-2026-10-27.md`.

| On the test photos | BioCLIP, zero-shot | BioCLIP + head | BioCLIP 2, zero-shot | **BioCLIP 2 + head (shipped)** |
|---|---|---|---|---|
| Right species is the top answer | 52% | 63% | 77% | **83%** |
| Honest claim accepted | 61%¹ | 65% | 75% | **81%** |
| Claim of another kind of fish accepted | 0.4%¹ | 0.3% | 0.1% | **0.06%** (8 of 13,559) |
| Look-alike passed as the species | 7.7%¹ | 1.8% | 1.4% | **0.9%** |
| Fish with no guide passed as an unrelated guide species | – | 0.2% | 0.0% | **0.1%** (11 of 9,203) |

¹ Before the fish with no guide and the stricter thresholds (0.5 / 0.6).
The first three columns read each photo four ways (mirrored too); the
shipped one two ways, which measured the same at half the time.

On two CPU threads BioCLIP 2 reads a photo in about 1 s (BioCLIP 0.3 s)
and adds about 330 MB of memory (BioCLIP 115 MB), with onnxruntime's memory
arena off.

## Consequences

- Accuracy is a measured rate, not a guarantee. Mistakes between kinds of
  fish (the catfish-as-bass case) are rare; look-alikes within a group are
  where it errs, which is why a group match never shows as "species
  confirmed".
- iNaturalist photos include nests, underwater and distant shots that a
  catch photo isn't, so the measured acceptance of honest claims understates
  real use; real catch photos should be collected (with consent) to
  re-measure.
- Training photos are scarce for some species (19 spotted bass, 21 threadfin
  shad in CC0 / CC BY); they are the weakest classes.
- The head is an adaptation of CC BY photos: their creators are credited in
  `TRAINING_CREDITS.json`, shipped with it (data-sources review item 7).
- Adding a guide species means adding its class and rebuilding the text
  vectors (the class digest makes a stale model refuse to load).
