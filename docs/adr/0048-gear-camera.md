# 0048. The gear camera: naming fishing gear from a photo

Date: 2026-11-07. Status: accepted (local, not deployed).

## Context

ADR 0047 put a photo beside each of the 52 things on /gear but left out
recognition: there were too few open photos. The product owner asked again:
a beginner holding a lure in a tackle shop, or a reel found in a garage,
should be able to photograph it and learn what it is. Every photo used must
allow commercial use (docs/data-sources.md), and the model must run on the
same small server as everything else (t3.small: 2 vCPUs, 2 GB, of which the
stack with the fish check uses about 1.4 GB).

## Decision

**Data.** Two open sources, nothing scraped (docs/data-sources.md, "Gear
photo recognition"):
- Open Images V7: photos labelled with gear classes, photos raters checked
  and found no gear in, and plain photos. Checked by eye, the labels from
  the Crowdsource app were wrong 35 times in 35 for Fishing rod, and
  `/m/02wg8` "Tackle" is the football tackle, so only the raters' and
  confident machine labels count as gear: about 280 photos, mostly rods. The
  rest give several thousand not-gear photos, which the camera needs as much.
- Wikimedia Commons gear categories (public domain, CC0, CC BY): close-ups
  of reels, lures, hooks, floats. Half are drawings, museum pieces or catch
  shots; a check with two models (P("a photo") averaged, below 0.4) leaves
  those out of training: on 101 photos checked by eye it caught 25 of 30
  drawings and lost 7 of 71 photos.
- Labels given by eye (`tools/gear_id/handcheck.json`): 338 photos for test
  and val, from contact sheets that show no model's guess, plus the 46
  photos already on /gear. Photos are split by author, and near-copies across
  the split (cosine > 0.95) are left out. Test: 164 gear photos, 116 of them
  labelled with the exact item, and 524 not-gear photos.

**Model.** Six open models with licences that allow commercial use were
compared on the same photos (test, after the head below):

| Model (licence) | Found gear | Rejected not-gear | Group right | Item right | Item in top 3 |
|---|---|---|---|---|---|
| PE-Core L/14-336, Meta (Apache 2.0) | 98.2% | 91.0% | 92.1% | **87.9%** | **96.6%** |
| PE-Core B/16, Meta (Apache 2.0) | 95.7% | 92.6% | 79.3% | 78.4% | 87.9% |
| SigLIP 2 SO400M/16-384, Google (Apache 2.0) | 90.9% | 91.0% | 79.3% | 78.4% | 84.5% |
| SigLIP 2 B/16-256, Google (Apache 2.0) | 95.1% | 81.3% | 74.4% | 68.1% | 82.8% |
| OpenCLIP ViT-B/32 LAION-2B (MIT) | 100% | 88.4% | 76.8% | 62.1% | 80.2% |
| BioCLIP 2, the fish model (MIT) | zero-shot item right 16% on an early test: it knows organisms, not tackle | | | | |

**Method.** The labelled photos say "a lure", rarely which lure, so what is
learnt from them is the group (rod, reel, line, hook, sinker, float, small
terminal tackle, lure, fly, bait, tackle box, tools, or not gear), and which
item inside the group is left to the model's own knowledge, through text
written for each item (`tools/gear_id/make_prompts2.py`):

    P(item) = sum over its groups g of P(g | photo) x P(item | g, photo)

P(g) is a linear head started from the groups' text vectors, kept near them,
fitted on the photos, and mixed half and half with the zero-shot group
answer (alpha 0.5, chosen on val). A head over all 52 items, trained the
same way, collapsed each group onto one item (item right 60%, from 85%
zero-shot); that is why the split. Descriptions of what each item looks like
(prompts3) did no better on val, so they aren't used. A photo is read as the
fish check reads one: the middle square and the whole photo padded, averaged.

**What ships.** `models/gear-id/`: PE-Core L's image encoder in ONNX, its
matrix multiplies compressed to int8 per channel (338 MB), the text vectors,
the head, SOURCE.json and TRAINING_CREDITS.json (every training photo with
its author, licence and page, as CC BY asks). Read the way the server reads
photos (int8, onnxruntime), test scores hold: item right 87.1%, in the top
three 96.6%, group 90.2%, gear found 98.8%, not-gear rejected 91.0%. On
this PC, 2.6 s a photo on two threads, and about 360 MB more memory.
`models/gear-id-small/` is the same build on PE-Core B (100 MB, 0.27 s,
about 120 MB): item right 76.7%, in the top three 87.9%.

Thresholds (`services/gear_id.Policy`): under 0.5 of "some gear", the photo
isn't gear (and if it looks most like a fish, the page points to the fish
check); a likeliest item with 0.6 of the gear share is named outright,
otherwise the three likeliest are offered with their photos to compare; under
0.2 nothing is offered (a blank or blurred picture spreads itself thin; on
val this cost no right answer).

**In the app.** `POST /api/gear/identify` (signed out: 10 a day per address
and 500 a day for everyone; signed in: 60 an hour) and a "What is this?"
camera on /gear in all five languages, linking each answer down to its card.
The photo is read and forgotten. `GEAR_ID=off` switches it off;
`GEAR_ID_MODEL_DIR` picks the model.

## Consequences

- The t3.small had no room for PE-Core L next to the fish check (about
  1.75 of 2 GB). The product owner moved the server to a t3.medium (4 GB)
  on 2026-11-07, so `models/gear-id` (PE-Core L) is the one to deploy;
  `models/gear-id-small` stays for a 2 GB server. Not deployed yet.
- The test set is small (116 photos with the exact item): read the item
  scores as about ±6 points. The 46 page photos were seen while the first
  prompts were written, so their score (41 of 44 right) flatters.
- Retraining: `backend/tools/gear_id/README.md`. Photos stay in
  `backend/gear_cache/` (git-ignored); the scripts and the labels given by
  eye are in git.

## Not done

- Close-ups of lures, hooks and bait are scarce in open data (Open Images
  has nine lure photos left after the label checks). Photos of real shelf
  items, taken by the team in a tackle shop and labelled, are what would
  improve the item scores most.
- One answer per photo: a tackle box full of lures gets one name, not a box
  around each lure.
- Not used: the Flickr API (no longer free), ImageNet (non-commercial terms),
  Objects365 and V3Det (no per-image licence), Roboflow sets (the uploader's
  rights can't be checked). COCO/LVIS photos with their own open licence and
  Smithsonian Open Access (CC0) are open candidates for later.
