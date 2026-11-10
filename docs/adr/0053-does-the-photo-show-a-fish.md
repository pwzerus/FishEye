# 0053. A second look: does the photo show a fish at all?

Date: 2026-11-10. Status: accepted.

## Context

A tester uploaded screenshots of a technical document as a catch and the photo
check said "looks like a Grass Carp". Of eight screenshots of FishEye itself,
seven came back with 75 to 100% "some fish" as well.

The classifier head was fitted on fish photos. Its not-fish classes (ADR 0037)
have no photos and keep their text vectors, so they sit on a different scale
from the fitted classes. A page of text, which resembles nothing in the
training set, spreads thinly over dozens of fish classes, and their sum clears
`min_fish`.

## Decision

A separate yes-or-no question, asked of the vector the recognizer already
computes: a logistic regression in `models/fish-id/gate.npz`, 4 KB, no extra
time or memory. Below `Policy.min_photo` (0.3) the photo's `fish_probability`
is 0, so every caller (the catch form, the "what fish is this?" page, Ask's
camera) reads it as no fish without changing. Without the file the app behaves
as before.

Fitted (`backend/tools/fish_gate/`) on the 5,142 fish training photos and 31
hand-picked photos of people with their catch, against 6,465 photos with no
fish: 1,200 synthetic screens, documents, slides, charts and forms in Chinese
and English; 96 screenshots of FishEye; 3,135 photos of people, food, animals,
boats and places; 1,031 of gear; and 1,003 picked to be hard, the kinds the first
version let through (portraits, comics, sky, landmarks, aquatic animals). Photos
whose labels or captions mention a fish were left out.

The hard photos count four times. The 300 fish photos likeliest to show a person
count five times and the 31 catches fifteen, because the rest of the fish photos
hardly ever have anyone in them, and a gate fitted on those learns that a person
means no fish.

## Results

An exam of 431 open-licence photos with no fish, collected after the first
version and never fitted on, run through the real `check_claim` path:

| | leaders | famous people | landmarks | sky | space | comics | homework, screens | animals | water animals | food | things | total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| photos | 40 | 40 | 40 | 37 | 40 | 40 | 40 | 35 | 40 | 40 | 39 | 431 |
| first version let through | | | | | | | | | | | | 17 (3.9%) |
| **shipped version let through** | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | **4 (0.9%)** |

The tester's 11 screenshots, also never fitted on, all came back as no fish.

What each threshold does, on the same model. None of these photos was fitted on:

| threshold | unrelated let through (431) | people with fish refused (150 from the test set) | hand-picked catches refused (31) | fish test set refused (2,173) | Commons fish refused (448) |
|---|---|---|---|---|---|
| 0.1 | 8 | 2.0% | 4 | 0.8% | 4.9% |
| 0.2 | 6 | 2.7% | 7 | 1.0% | 5.8% |
| **0.3** | **4** | **3.3%** | **8** | **1.15%** | **6.2%** |
| 0.5 | 4 | 4.0% | 9 | 1.4% | 8.7% |
| 0.8 | 3 | 5.3% | 10 | 2.3% | 15.6% |

0.3 is where more refusals stop buying anything: from there to 0.7 the unrelated
count doesn't move while real catches keep being refused.

**It isn't zero, and the price is real.** The four let through are a portrait,
a lizard's scales, an octopus and a stream full of leaves. Eight of the 31
catches were refused: six of people holding fish, but also a brook trout lying
beside a fly rod and a pile of fish on a white table, so it isn't only fish that
are small in the frame. The first version refused 7 of the same 31, so this
isn't a new cost of the second one. Refused doesn't mean blocked: the catch can
still be shared, it just isn't given a species.

Tried and dropped: also scoring the photo's four corners, so that a fish that's
small in the frame counts. Catches refused fell from 8 to 3 of 62, but unrelated
photos let through rose from 4 to 8 of 152.

## Consequences

Deploying needs `gate.npz` and `GATE_CREDITS.json` copied into
`backend/models/fish-id/` with the rest of the model (`docs/deploy-aws.md`).
Refit it if the encoder changes: the app ignores a gate made for another one.

The weakest groups are gear (a lure is made to look like a fish) and photos of
people with a small fish. More real catch photos are what would help most: only
62 hand-checked ones were found under open licences.
