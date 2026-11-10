"""Hand-check test photos on contact sheets, then turn the notes into labels.

    python -I handcheck.py sheets <gear_cache dir> <source>[@split] [cap_per_label]
        writes work/check-<source>[@split].json (the photos, in sheet order);
        then sheet.py makes the pictures. split is test unless given (val).
    python -I handcheck.py apply <gear_cache dir> <source> <notes.txt>
        notes: one line per photo, "<number> <label>", where label is
        item ids joined by "+", a group with "?" (rod?, reel?, lure?, hook?,
        float?, sinker?, bait?, fly?, gear?), "no" (no gear in it) or
        "drop" (gear too small or unclear to say). Merged into
        tools/gear_id/handcheck.json (in git: the test labels).
Only test or val photos are shown (val ones choose settings, test ones are
scored): the labels given here are what the fine score counts, so the
sheets carry no model's guess. Photos already checked are not shown again.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from taxonomy import ALL_GEAR, GROUPS, LURE_KINDS, LURES, NOT_GEAR  # noqa: E402

mode, root, name = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
source, _, which = name.partition("@")
which = which or "test"
work = root / "work"
labels = json.loads((work / "labels.json").read_text("utf-8"))
manifest = {m["id"]: m for m in json.loads((work / "manifest.json").read_text("utf-8"))}
SHORT = {"rod": "rod", "reel": "reel", "lure": "lure", "spoon": "spoon", "surface-lure": "surf", "spinnerbait": "spnb",
         "hook": "hook", "float": "float", "sinker": "sink", "bait": "bait", "tackle-box": "box", "tackle": "tackle",
         "fly-fishing": "fly"}

if mode == "sheets":
    cap = int(sys.argv[4]) if len(sys.argv) > 4 else 10_000
    oi = json.loads((root / "oi" / "labels.json").read_text("utf-8")) if source == "oi" else {}
    cats = json.loads((root / "commons_cat" / "files.json").read_text("utf-8")) if source == "commons" else {}
    by_label = defaultdict(list)
    for key, rec in labels.items():
        if rec["source"] != source or rec["split"] != which or rec["checked"]:
            continue
        if source == "oi":
            raw = key.split(":", 1)[1]
            if oi[raw]["kind"] != "gear":
                continue
            note = "+".join(SHORT[y] for y in oi[raw]["yes"])
            by_label[oi[raw]["yes"][0] if len(oi[raw]["yes"]) == 1 else "multi"].append((key, note))
        else:
            f = cats[key.split(":", 1)[1]]
            by_label[f["kind"]].append((key, f["kind"]))
    chosen = []
    for lab in sorted(by_label):
        chosen += sorted(by_label[lab])[:cap]
    items = [{"id": k, "path": manifest[k]["path"], "rotate": manifest[k].get("rotate", 0), "note": n} for k, n in chosen]
    (work / f"check-{name}.json").write_text(json.dumps(items, indent=0), encoding="utf-8")
    print(f"{len(items)} photos to check:", {k: min(len(v), cap) for k, v in sorted(by_label.items())})
else:
    items = json.loads((work / f"check-{name}.json").read_text("utf-8"))
    hand_path = Path(__file__).parent / "handcheck.json"
    hand = json.loads(hand_path.read_text("utf-8")) if hand_path.exists() else {}
    groups = {f"{g}?": m for g, m in (GROUPS | LURE_KINDS).items()} | {"lure?": LURES, "gear?": ALL_GEAR}
    n_set = 0
    for line in Path(sys.argv[4]).read_text("utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        num, lab = line.split(None, 1)
        key = items[int(num) - 1]["id"]
        lab = lab.strip()
        if lab == "drop":
            hand[key] = {"drop": True}
        elif lab == "no":
            hand[key] = {"allowed": NOT_GEAR}
        else:
            allowed = set()
            for part in lab.split("+"):
                if part in groups:
                    allowed |= set(groups[part])
                elif part in ALL_GEAR:
                    allowed.add(part)
                else:
                    raise SystemExit(f"line {num}: unknown label {part!r}")
            hand[key] = {"allowed": sorted(allowed)}
        n_set += 1
    hand_path.write_text(json.dumps(hand, indent=0), encoding="utf-8")
    print(f"{n_set} labels from {sys.argv[4]}; {len(hand)} hand labels in all")
