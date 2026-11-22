# The fish photo check on BioCLIP 2.5, with no iNaturalist photo fitted on

What it is and why: `docs/adr/0066-bioclip-2-5-without-inaturalist.md`, and
for reading a photo once, `docs/adr/0067-read-a-photo-once.md`. Where each
photo set comes from and its licence: `docs/data-sources.md` ("Fish photo
check").

The model in `models/fish-id/` is BioCLIP 2.5 Huge's image encoder (int8
ONNX) and its own text vectors, with no classifier head. Two things are
fitted, neither on iNaturalist photos:

- **the logit scale** (one number, 50 against the model's own 98.9), by
  log-likelihood on the Wikimedia Commons fish photos of `fishid_cache/train`;
- **the gate** ("is there a fish at all"), a logistic on the same vectors.
  Fish: Open Images photos (CC BY 2.0), those Commons photos, and Commons
  photos of anglers with their catch. Not fish: the photos of
  `tools/fish_gate`, less 61 Open Images photos a person verified as showing
  a fish, plus Commons aquatic animals checked by eye. Photos that were
  fetched from Flickr's own servers by a script are not fitted on: Flickr's
  terms forbid robots and data gathering.

iNaturalist test photos are only measured on.

The app reads a photo's middle square alone, one photo a run (ADR 0067).
The scale was fitted on two views' vectors (the middle square and the whole
photo, averaged, 8 photos a run) and is kept; the gate is refitted on middle
squares read one a run, as the app reads them (step 8).

Run from `backend/`. Two Python environments: a GPU one with torch, open_clip
and safetensors (steps 1 and 2), and the backend's `.venv` (the rest). Keep
caches off a full system disk: set `HF_HOME`, `TEMP` and `TMP`. The work
folder of the gate's photo sets is `F:/tmp/fish_gate`, as in `tools/fish_gate`.

| Step | Command | What it does |
|---|---|---|
| 1 | `python -I tools/fish_id_b25/build.py text` | Text vectors for every class, `classes.json`, `SOURCE.json` in `models/fish-id-b25/` (weights read from `models/bioclip25-src/`) |
| 2 | `python -I tools/fish_id_b25/build.py export`, then `.venv/Scripts/python tools/fish_id_b25/build.py quantize` | fp32 ONNX (weights in files beside it), then `image_int8.onnx`, per channel |
| 3 | `python -I tools/fish_id_b25/oi_fish.py labels`, `meta`, `fetch` | Open Images fish photos: human-verified labels, CC BY 2.0 rows, from the dataset's S3 mirror, 1 s apart |
| 4 | `.venv/Scripts/python tools/fish_gate/collect_nonfish.py tools/fish_id_b25/queries_t3.json F:/tmp/fish_gate/nonfish_t3 8 300` | Commons aquatic animals that aren't fish; look through them and list any with a fish in `has_fish_t3.json` |
| 5 | `.venv/Scripts/python tools/fish_id_b25/embed_int8.py models/fish-id …` | int8 vectors of the test photos, the gate's sets, the Open Images fish, the Commons training photos and the aquatic animals (its docstring lists each), read as the app reads them: about 0.4 s a photo on eight laptop threads |
| 6 | `.venv/Scripts/python tools/fish_id_b25/credits.py` | `GATE_CREDITS.json`: everyone whose photo was fitted on; a photo with no credit found is left out of the fit |
| 7 | `.venv/Scripts/python tools/fish_id_b25/fit_gate.py --space int8 --write` | How the scale and the first gate were fitted (ADR 0066), on the "middle+whole" caches; writes `gate.npz` and the scale into `models/fish-id-b25/` |
| 8 | `.venv/Scripts/python tools/fish_id_b25/refit_gate.py --write` | Refits the gate on step 5's vectors, the same photos and weights as step 7, measures it against the installed gate, writes `models/fish-id/gate.npz` |

Steps 1 to 7 built `models/fish-id-b25/`, whose `image_int8.onnx`,
`text.npy`, `classes.json`, `SOURCE.json`, `gate.npz` and `GATE_CREDITS.json`
were copied into `models/fish-id/` (there is no `head.npz`); step 8 writes
there itself. Copy `models/fish-id/` to the server as `docs/deploy-aws.md`
says. `fit_gate.py` measures against BioCLIP 2 as shipped until 2026-11-21,
kept locally in `models/fish-id-bioclip2/`.
