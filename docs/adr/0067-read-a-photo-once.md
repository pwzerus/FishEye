# 0067. Read a photo once: its middle square alone

Date: 2026-11-22. Status: accepted (deploy waits on the owner).

## Context

Since ADR 0066 the photo check has been BioCLIP 2.5 Huge (int8). It read each
photo twice, its middle square and the whole photo padded to a square, and
averaged the two. On the server (t3.medium, two vCPUs) that took about 5 s a
photo, and a reading holds both cores while it runs. On 2026-11-22 the owner
asked what reading once would cost, measured locally before deciding. Of the
two ways to fit the gate for it (below), they chose the refitted one.

## Decision

- **The middle square alone, one photo a run** (`FishRecognizer.embed`,
  `READING = "middle"`). The whole photo alone was measured too: worse on
  every line (78.3% top-1 on the clean photos), so it was dropped.
- **The gate refitted on middle squares read the app's way**
  (`tools/fish_id_b25/refit_gate.py`). It uses the same photos, weights and
  fit as ADR 0066, so `GATE_CREDITS.json` is unchanged. `gate.npz` now names
  its reading. The app still uses a gate fitted on another reading but logs a
  warning: such a gate is looser, and with none at all screenshots would pass
  as fish.
- **The logit scale stays at 50.** Fitted the same way on middle squares, it
  would be 42.5. That accepts fewer honest claims on the clean photos (61.5%
  against 70.2%) and fewer fish with no guide (15 against 38). At 50, both
  stay close to what was live (64.7% and 41).

## Measured (int8, one photo a run as the app reads, 2026-11-22)

| | Two views (until now) | Middle, two views' gate | Middle, gate refitted (shipped) |
|---|---|---|---|
| Time a photo, laptop, two threads | 1.67 s | 0.82 s | 0.82 s |
| Peak memory of the process, laptop | 744 MB | 723 MB | 723 MB |
| Top-1, 2,706 clean photos (Mar 2026 on) | 84.5% | 83.9% | 83.9% |
| … far from the sea, 1,543 photos | 86.3% | 85.0% | 85.0% |
| Honest claims accepted, clean photos | 64.7% | 69.0% | 70.2% |
| Claims of another kind accepted (of 17,162) | 0 | 2 | 2 |
| Look-alikes confirmed as the species (of 1,144) | 0 | 1 | 1 |
| Fish with no guide accepted as one, clean photos | 41 | 38 | 38 |
| Commons test photos (434): top-1 / claims accepted | 71.6% / 52.7% | 72.3% / 52.7% | 72.3% / 54.1% |
| Real fish told "no fish": clean / Commons | 3.0% / 6.5% | 3.7% / 7.8% | 2.9% / 6.9% |
| Unrelated photos let through the gate (of 431) | 20 | 27 | 16 |
| Anglers' catches refused (31 never fitted / all 62) | 3 / 5 | 2 / 4 | 4 / 8 |
| Claims accepted on unrelated photos | 0 | 0 | 0 |

- **Photo by photo**, on the 678 clean photos of guide species, 27 are named
  right only with two views and 23 only with the middle square. That is
  within noise. Honest claims accepted: 12 only with two views, 49 only with
  the middle square.
- **The new errors** are on two photos. 6320074058 is labelled yellow perch,
  but a sunfish fills the middle; it was read as a pumpkinseed at 0.99, so
  claims of a bluegill or a redear were accepted as the sunfish group.
  6273152533 is a smallmouth seen from above in shallow water, confirmed as
  a largemouth at 0.97. The Commons look-alike (a Guadalupe bass confirmed as
  a spotted bass) is in all three readings.
- **The three catches** refused that two views passed: two old black-and-white
  photos with the fish small in the frame, and a tournament angler holding a
  bass out at each edge of a wide photo, which the middle square cuts.
- **On the server**, about 2.5 s a photo is expected (5.1 s with two views,
  scaled by the laptop's ratio), to be measured after the deploy.

**ADR 0066 was measured 8 photos a run.** The int8 encoder quantizes each run
as a whole, so a photo's vector depends on the photos read beside it. ADR
0066's vectors were read 8 photos to a run; the app reads one. Read the app's
way, the model deployed on 2026-11-22 lets 20 unrelated photos of 431 through
the gate, not 16. Its top-1 on the clean photos is 84.5%, not 83.9%, and its
Commons claims accepted are 52.7%, not 49.3%. `embed_int8.py` now reads one
photo a run.

## Consequences

- Half the time a photo, so the rest of the API waits less behind it too.
- More honest claims are accepted, at the cost of the two errors above.
  Nothing is accepted on unrelated photos.
- A fish held out at the edges of a wide photo loses its head and tail to the
  square, and is more likely to be told "no fish". Portrait phone photos keep
  their full width.
- Deploy the code and `models/fish-id/gate.npz` together. New code with the
  old gate logs a warning and runs looser: 27 unrelated photos of 431 get
  through. Old code with the new gate notices nothing. To roll back, restore
  both.
- The two-view caches (`…-middle+whole.npz`) stay for `fit_gate.py`.
  `fish_id_eval.py` reads `…-middle.npz`; the test photos from before March
  2026 are not in it yet, and its first run reads them (about 20 minutes).
