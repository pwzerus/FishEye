# 0066. The photo check on BioCLIP 2.5, with nothing fitted on iNaturalist photos

Date: 2026-11-21. Status: accepted (deploy waits on the owner).

## Context

The photo check (ADR 0037, 0053, 0063) was BioCLIP 2 with a classifier head
and a gate fitted on 25,567 iNaturalist photos fetched through GBIF (CC0 and
CC BY). On 2026-11-19 the owner showed a ChatGPT plan that pointed at
iNaturalist's Terms: "Users may not use any iNaturalist data for training
artificial intelligence, machine learning models … for commercial purposes"
(quoted by a forum moderator; whether it reaches photos fetched through GBIF is
disputed, with no staff answer). FishEye will charge for Plus, has no budget
for lawyers or photos, and its one data rule is commercial-safe sources
(`docs/data-sources.md`, "Needs human review" 0).

BioCLIP 2.5 Huge (imageomics/bioclip-2.5-vith14, MIT, published 2026-02-10)
names fish from its own text vectors better than BioCLIP 2 with its head did:
on 2,706 iNaturalist test photos uploaded from March 2026, which no model here
saw, 83.9% top-1 against 81.4% (int8 both). The owner chose on 2026-11-21 to
switch to it with nothing fitted on iNaturalist photos, and asked whether
Flickr's open-licence photos could train it further: they can't, as Flickr's
terms forbid robots and data gathering and Openverse's forbid scraping
(`docs/data-sources.md`, "Not used").

## Decision

**BioCLIP 2.5's encoder and text vectors, no head.** `tools/fish_id_b25/`
builds `models/fish-id/`: the image encoder exported to ONNX and quantized to
int8 per channel (640 MB), and the text vectors of every class
(`fish_id_classes.py`). Two things are fitted, neither on iNaturalist photos:

- **The logit scale**, one number: 50 instead of the model's own 98.9 (which
  is surer than it is right), by log-likelihood on the 492 Wikimedia Commons
  fish photos of the training set. `SOURCE.json` carries it as
  `calibrated_logit_scale`, which `FishRecognizer` reads.
- **The gate** ("is there a fish at all", ADR 0053), refitted the same way on
  BioCLIP 2.5's vectors. Fish: 3,539 Open Images photos (CC BY 2.0, from
  Google's own mirror), the 492 Commons photos and 8 Commons photos of anglers
  with their catch. Not fish: the shipped gate's photos (Open Images,
  Commons, open catalogues, screenshots), less 61 that Open Images verified as
  showing a fish (many of anglers with their catch, wrongly taught as "no
  fish" before), less 101 Flickr photos that had been fetched from Flickr's
  own servers by a script, less 7 whose credit could not be found, plus 193
  Commons aquatic animals checked by eye (turtles, dolphins, jellyfish).
  `GATE_CREDITS.json` credits all 9,353.

**Stricter thresholds, chosen on Commons photos.** With BioCLIP 2's
`Policy` (confirm 0.8, group 0.8), 5 claims of another kind of fish got
through on the 434 Commons test photos, against none for BioCLIP 2; at
confirm 0.9 and group 0.98, none. The thresholds were chosen there, not on
iNaturalist photos, which are only measured on.

**A head left behind is ignored.** A `head.npz` fitted on another encoder's
vectors is not used (a warning, not a crash), so a server with BioCLIP 2's
head beside BioCLIP 2.5 keeps working; the deploy removes it.

## Measured (int8, the app's own reading; `fit_gate.py`, 2026-11-21)

Against BioCLIP 2 with its head and gate, on the same photos:

| | BioCLIP 2 + head | BioCLIP 2.5, 0.9 / 0.98 |
|---|---|---|
| Top-1, 2,706 clean photos (Mar 2026 on) | 81.4% | 83.9% |
| Honest claims accepted, all 5,237 test photos | 71.1% | 66.4% |
| … with the exact species confirmed | 51.7% | 54.2% |
| Claims of another kind accepted (of 30,660) | 5 | 1 |
| Look-alikes confirmed as the species (of 1,983) | 7 | 7 |
| Fish with no guide accepted as one (of 111,773) | 79 | 45 |
| Real fish told "no fish" | 0.7% | 2.8% |
| Commons test photos: top-1 / claims accepted | 73.0% / 57.4% | 70.3% / 49.3% |
| Unrelated photos let through the gate (of 431) | 4 | 16 |
| Anglers' catch photos refused (of 31) | 5 | 3 |
| Memory / time a photo (laptop, two threads) | 340 MB / 0.54 s | 670 MB / 0.97 s |

No unrelated photo got any claim accepted, with either model: one that
passes the gate is answered "we couldn't confirm", not "this is a bass".

## Consequences

- Nothing that ships is fitted on iNaturalist photos. What remains open is
  BioCLIP's own training data (Imageomics trained it, as BioCLIP 2, on
  TreeOfLife-200M, which includes iNaturalist photos and some licensed
  non-commercial; they released the weights under MIT) and measuring on
  iNaturalist test photos.
- Fewer wrong fish are accepted and the exact species is confirmed more
  often; fewer honest claims are accepted overall (66% against 71%), more
  real fish are told "no fish" (2.8% against 0.7%), and web-style photos
  (Commons) fare worse, partly because int8 costs BioCLIP 2.5 about 5 points
  there (75.7% top-1 in fp32).
- The gate lets more unrelated photos through (16 against 4 of 431), mostly
  aquatic animals; its fish are aquariums, reefs and markets more than
  anglers' catches. FishEye users' own catch photos, once the privacy policy
  says they train the check, are the best source to close that.
- Twice the memory (about +330 MB on a 4 GB server) and twice the time a
  photo. Check `free -m` before deploying.
