# 0063. Fish of the sea in the photo check, left out far from the sea

Date: 2026-11-19. Status: accepted.

## Context

The owner's plan of 2026-11-18, step 2: the shore, pier and inshore fish of
every US coast, Alaska and Hawaii, in the photo ID. On 2026-11-18, 207 classes
were added to `fish_id_classes.py`: 23 freshwater fish from the US and Canada
list, and 184 fish of the sea (sharks and rays with an Elasmobranchii prompt).
That makes 294 classes: 27 guide species, 254 other fish, 13 not fish.

Photos, research-grade iNaturalist via GBIF, CC0 or CC BY only: 25,661 for
training (any country, 2008 to 2023) and 5,237 for testing (US, 2024 on; 2,173
before). The head fitted on them (below) names the new fish well, but on the
old 2,173 test photos it was worse at the lake fish that catches name:

| On the old test photos | Stage 1 head (87 classes) | 294 classes | 294, inland (below) |
|---|---|---|---|
| Top answer right (27 guide fish) | 82.2% | 79.9% | 81.2% |
| True claims accepted | 76.0% | 71.1% | 74.7% |
| Claims of another kind of fish accepted | 11 of 30,383 | 5 | 9 |
| Fish with no guide, claimed as a guide fish, accepted | 104 of 26,510 | 74 | 100 |

Most of the lost photos went to a fish of the sea that looks like a lake fish:
freshwater drum read as black drum, channel and blue catfish as hardhead or
gafftopsail catfish, northern pike as great barracuda, threadfin shad as
Atlantic bumper. And the gate (ADR 0053) turned away 23% of the sea fish test
photos: reef fish and rays photographed underwater, skates' egg cases, and a
crevalle jack held up on a pier.

## Decision

**Far from the sea, its fish are left out.** A catch with no coastal spot (ADR
0062: piers, jetties, fishing spots and boat ramps by the sea, not the Great
Lakes) within 50 km is inland (`services/coast.py`). There the check reads the
photo without the fish of the sea, the rest scaled back up to a whole, as if
the model had never known them (`fish_id.Identification.inland`,
`fish_id_classes.SEA_ONLY`). Eleven fish of the sea that swim far up rivers
stay everywhere (`UP_RIVERS`: striped mullet, snook, tarpon, Atlantic
needlefish, crevalle jack, southern and starry flounder, bull shark, Atlantic
stingray, Atlantic tomcod, eulachon). Saving a catch decides this from the
pin. The catch form sends the pin's point with its photo check so that its
advice matches; the point is used for that and not kept. The "what fish is
this?" page and Ask's camera send no place, so every fish counts there. While
no coastal spots are imported, nothing counts as inland.

**The gate, refitted with the sea fish.** Same tool and settings
(`tools/fish_gate/fit_gate4.py --cfg 5 4`), with all 25,661 training photos as
fish. On the same exam, against the gate it replaces:

| | Before | Now |
|---|---|---|
| Unrelated photos passed (of 431) | 4 | 4 |
| Real catches refused (of 31) | 8 | 5 |
| Sea fish test photos refused | 23.2% | 0.5% |
| Guide fish test photos refused | 1.1% | 0.7% |
| Other freshwater fish refused | 2.7% | 0.7% |
| Commons photos refused (of 448) | 2.9% | 6.0% |

The four unrelated photos that pass are now three underwater scenes (an
octopus and a sea turtle among them) and a satellite picture. The Commons
photos newly refused are mostly drawings, engravings and a plate of sashimi,
but also three real photos (a girl holding a bluegill, a bighead carp's head, a
round goby).

**The head, fitted on what BioCLIP reads as mostly fish.** The old gate had
cleaned the training photos (it threw out 4,833, most of them sea fish
photographed underwater), and a gate can't clean the photos it is now fitted
on. So a training photo is left out when BioCLIP's own weights put less than
half of it on fish (17 of 25,661; `fishid_cache/train/excluded.json`). Same
settings as stage 1; 265 classes fitted, 16 fish with under 8 photos keep
BioCLIP's weights (paddlefish, gag, Pacific halibut…). On all 5,237 test
photos (`fish_id_eval.py`): top answer right 79.6% of 1,209 guide photos, true
claims accepted 71.1%, claims of another kind accepted 5 of 30,660, fish with no
guide named 74.7% of 4,028 (fish of the sea 77.3% of 2,629, in 181 kinds; the
23 freshwater fish added 74.9%; the older ones 67.6%). Wild crucian carp
(`fishid_cache/crucian_test`, 43 photos): 36 named (stage 1: 36), 27 at 80% or
more (32); the owner's photo 77% (77%).

## Consequences

- The class list changed, so the server refuses the old model: deploying this
  copies `models/fish-id/` (`classes.json`, `text.npy`, `head.npz`,
  `SOURCE.json`, `TRAINING_CREDITS.json`, `gate.npz`, `GATE_CREDITS.json`; the
  encoder is unchanged) in the same step as the code (docs/deploy-aws.md).
  The files they replace are in `models/fish-id-v2-small/`.
- Coastal lakes, estuaries and rivers within 50 km of a coastal spot keep every
  fish, at the 71% above. Where spots are sparse (parts of Alaska, Louisiana's
  marshes) a place near the shore can count as inland; the check there is the
  one FishEye had before it knew any fish of the sea.
- The 23 freshwater fish added cost their older look-alikes: fish with no guide
  from before are named 67.6% of the time (72.0%).
- Underwater photos of fish pass the gate now, and so can an octopus or a sea
  turtle underwater. Skates' egg cases are read as skates.
- `GATE_CREDITS.json` also credits the 94 training photos the gate saw and the
  head didn't (fish with under 8 photos, and the 17 left out).
