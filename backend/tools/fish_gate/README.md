# The fish photo check's gate

`models/fish-id/gate.npz` answers one question before the species do: does this
photo show a fish at all? It is a logistic regression on the same BioCLIP
vectors the recognizer already makes, so it costs no extra time or memory.
Why it exists and how it was measured: `docs/adr/0053`.

Run from `backend/`, with `FISH_ID=on` and the backend's virtualenv:

1. `make_screens.py <out> 1200 1`: synthetic screenshots, documents, slides,
   charts and forms. Random layouts in FishEye's own handbook text; `<out>` is
   the `screens/` folder beside `neg.npz`.
2. `embed_neg.py`: vectors of photos with no fish: those screens, screenshots
   of FishEye, and the not-gear and gear photos of `gear_cache/` whose labels
   and captions mention no fish.
3. `collect_nonfish.py <queries.json> <folder> [per query] [per group]`: open-licence
   photos from Wikimedia Commons, one folder per group. Used for the hard
   negatives, for the catches and, kept apart, for the exam. Look through the
   results: the groups go into a fit as they are.
4. `eval_nonfish.py <folder> <out.json>`: every photo through the real
   `check_claim`, per group, plus the vectors the fit reads (`vectors_fish.npz`).
   `--gear` adds the gear camera.
5. `person_probe.py`: finds the fish training photos likeliest to show a person,
   which the fit counts extra.
6. `fit_gate4.py --cfg 5 4 [--write]`: fits with those weights, prints what each
   threshold does to everything left out of the fit (the exam, half of the
   catches, the fish test sets) and with `--write` saves `gate-v2.npz`.

Copy the result to `models/fish-id/gate.npz`. The scripts expect their work
folder at `F:/tmp/fish_gate`; change `OUT` if it is elsewhere. Who took the
photos is in `models/fish-id/GATE_CREDITS.json`, and only the weights ship.
