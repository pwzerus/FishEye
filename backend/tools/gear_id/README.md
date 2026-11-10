# Gear camera: how the model in `models/gear-id/` is made

What it is and why it is built this way: `docs/adr/0048-gear-camera.md`.
Where the photos come from and their licences: `docs/data-sources.md`
("Gear photo recognition"). Everything downloaded goes to
`backend/gear_cache/` (git-ignored); only these scripts and the labels given
by eye (`handcheck.json`, with the notes they came from) are in git.

Two Python environments: the app's (`backend/.venv`, for `commons_cats.py`),
and a build one with PyTorch, open_clip >= 3, onnx and onnxruntime (a GPU
makes `embed.py` minutes instead of hours; everything else runs on a CPU).
Keep caches off a full system disk: set `HF_HOME`, `TEMP` and `TMP`.

Run from `backend/`, in order (`R=gear_cache`):

| Step | Command | What it does |
|---|---|---|
| 1 | `python -I tools/gear_id/oi_meta.py $R` | Picks Open Images photos (gear, hard negatives, plain negatives) from the label extracts `$R/oi_*.csv` and streams the image lists for their credits (CC BY 2.0 rows only) |
| 2 | `python -I tools/gear_id/oi_fetch.py $R` | Fetches them from the dataset's S3 mirror, 1 s apart, 640 px; about a third aren't on the mirror |
| 3 | `.venv/Scripts/python -I tools/gear_id/commons_cats.py` | Commons gear categories: PD, CC0, CC BY files, 500 px |
| 4 | `python -I tools/gear_id/build_labels.py $R` | `work/labels.json`, `labels_all.json`, `manifest.json`; split by author |
| 5 | `python -I tools/gear_id/make_prompts2.py $R/work` | The text for each class (prompts2 won on val; prompts3, with descriptions, didn't) |
| 6 | `python -I tools/gear_id/embed.py pe-core-l14-336 $R/work/manifest.json $R/work/prompts2.json $R/work/emb2/pe-core-l14-336.npz --reuse $R/work/emb2/pe-core-l14-336.npz` | Photo and text vectors (also for siglip2-so400m-384, used by step 7) |
| 7 | `python -I tools/gear_id/clean_train.py $R/work/labels_all.json $R/work/unfit.json <so400m.npz> <pe-l.npz>`, then `dupes.py <pe-l.npz> $R/work/labels_all.json $R/work/dupes.json`, then step 4 again | Leaves drawings, catch shots and near-copies out of training |
| 8 | `python -I tools/gear_id/export_onnx.py pe-core-l14-336 $R/onnx/pe-core-l14-336 $R/work/manifest.json`, then quantize per channel | ONNX encoder, fp32 and int8 |
| 9 | `python -I tools/gear_id/embed_onnx.py ... --only val,test --two-views` | The val and test photos read as the server reads them |
| 10 | `python -I tools/gear_id/train_eval.py <emb.npz> $R/work/labels.json <out.json> --save-head <head.npz>` | Fits the group head, picks its settings on val, scores test once |
| 11 | `python -I tools/gear_id/package_model.py pe-core-l14-336 $R models/gear-id [run tag]` | What the app reads, with SOURCE.json and TRAINING_CREDITS.json. The run tag picks the head (`results/<tag>-head.npz`); without it, `<key>-int8pc`. `work/labels.json` must be that run's labels: the credits come from it |

Checking labels by eye: `handcheck.py sheets $R oi` (or `commons`, `commons@val`)
lists photos, `sheet.py` draws numbered contact sheets, the notes
(`notes-*.txt`) say what each number shows, and `handcheck.py apply` turns
them into `handcheck.json`. The sheets carry no model's guess.

New photos (your own, from a tackle shop) go in as a new source in
`build_labels.py`; label a share of them by eye for test before trusting a
better score.

## More photos from open catalogues (2026-11-07)

| Step | Command | What it does |
|---|---|---|
| a | `python -I tools/gear_id/scan_catalogs.py <pd12m\|yfcc\|smithsonian\|commoncatalog> $R/open2 --sample 5573` | Searches the catalogues' text with `keywords.py` (52 items, ~2,600 names, 13 languages); text only, a few GB read, nothing kept but the matches. CommonCatalog goes through `hf_range.py` (Hugging Face rate-limits its own downloader) |
| b | `python -I tools/gear_id/fetch_candidates.py $R <batch> <sources>` | Downloads the close-up candidates at 640 px (`cc_images.py` reads a CommonCatalog photo out of its parquet page) and lists them in `work/check-<batch>.json` |
| c | `sheet.py`, then `handcheck.py apply $R <batch> notes-<batch>.txt` | Every photo labelled by eye (`notes-open1/openf/openc1/openc2.txt`); only these are trained on, all in train |
| d | step 6, then `open_dupes.py <pe-l.npz> $R/work/labels_all.json $R/work/dupes.json`, then step 4 | Vectors for the new photos; new photos that copy a val or test photo are left out (val and test never change) |

Of 2,466 photos found and checked, 1,913 were kept (about 450 show gear,
mostly flies, fly rods and reels; the rest teach "not gear"). Result on the
unchanged test set, int8 as the server runs it: exact item 87.1% -> 89.7%,
not-gear rejected 91.0% -> 96.2%, gear found 98.8% -> 95.1%.

Installed with `package_model.py ... pe-core-l14-336-int8pc-open` on
2026-11-08 (the earlier head's small files are in
`$R/work/before-open/gear-id/`; the encoder is the same file). Counted as
the page answers (`gear_id.POLICY`), on the 116 checked test gear photos:
named right 101 -> 101 (three more right first guesses fall below
`min_gear`), named for sure and right 56 -> 59; of 524 test photos with no
gear, answered as gear 46 -> 19. On val a lower `min_gear` only adds wrong
gear answers (both missed val photos read about 0.2), so POLICY is unchanged.
