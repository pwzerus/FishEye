"""Do photos with nothing to do with fishing get past the checks? eval_nonfish.py root out.json

Fish check: `passes` means the catch form would accept it as a fish (check_claim with no species named).
Gear camera: `gear` means it would name a piece of gear. Vectors are cached in root/vectors_*.npz.
"""
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, 'F:/FishEye/backend')
sys.stdout.reconfigure(encoding='utf-8')
Image.MAX_IMAGE_PIXELS = None
from app.services.fish_id import NO_FISH, FishRecognizer, check_claim  # noqa: E402
from app.services.gear_id import GearRecognizer  # noqa: E402

root, out = Path(sys.argv[1]), sys.argv[2]
files = sorted(glob.glob(str(root / '*' / '*.jpg')))
rec = FishRecognizer(Path('F:/FishEye/backend/models/fish-id'))
WITH_GEAR = '--gear' in sys.argv
gear = GearRecognizer(Path('F:/FishEye/backend/models/gear-id')) if WITH_GEAR else None
print(rec.name, len(files), 'gear' if WITH_GEAR else 'fish only', flush=True)
cf = root / 'vectors_fish.npz'
cg = root / 'vectors_gear.npz'
vf = dict(np.load(cf)) if cf.exists() else {}
vg = dict(np.load(cg)) if cg.exists() else {}
res = []
for f in files:
    key = Path(f).parent.name + '/' + Path(f).stem
    try:
        if key not in vf:
            with Image.open(f) as im:
                vf[key] = rec.embed(im.convert('RGB'))
        if gear is not None and key not in vg:
            with Image.open(f) as im:
                vg[key] = gear.embed(im.convert('RGB'))
            if len(vg) % 50 == 0:
                np.savez(cg, **vg)
                print('gear', len(vg), flush=True)
    except Exception as e:
        print('bad', key, repr(e)[:80], flush=True)
        continue
    ident = rec.identify_vector(vf[key])
    v = check_claim(ident, None)
    rd = gear.read_vector(vg[key]) if gear is not None else None
    res.append(dict(key=key, path=f, group=Path(f).parent.name, gate=ident.gate, fish_p=round(ident.fish_probability, 3),
                    status=v.status, top=ident.fish(1)[0].slug, top_p=round(ident.fish(1)[0].probability, 3),
                    gear_p=round(rd.gear_probability, 3) if rd else None, is_gear=rd.is_gear if rd else False, gear=(rd.candidates[0].id if rd and rd.candidates else None)))
np.savez(cf, **vf)
if gear is not None:
    np.savez(cg, **vg)
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
by = defaultdict(list)
for r in res:
    by[r['group']].append(r)
tot, fp, gp = 0, 0, 0
for g, L in by.items():
    p = [r for r in L if r['status'] != NO_FISH]
    q = [r for r in L if r['is_gear']]
    tot += len(L)
    fp += len(p)
    gp += len(q)
    print(f'{g:12} n={len(L):3} fish-pass={len(p):3} gear-pass={len(q):3}  ', ' '.join(f"{r['top'][:14]}" for r in p[:6]), flush=True)
print(f'TOTAL {tot}: passed as fish {fp} ({fp / tot:.1%}), passed as gear {gp} ({gp / tot:.1%})', flush=True)
