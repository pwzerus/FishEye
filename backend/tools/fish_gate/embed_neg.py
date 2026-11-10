"""Vectors of photos that show no fish, read the way the recognizer reads a catch photo.

embed_neg.py  (from backend/, FISH_ID=on) -> F:/tmp/fish_gate/neg.npz + neg.json (key -> group, path)
"""
import glob
import json
import random
import re
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
Image.MAX_IMAGE_PIXELS = None
from app.services.fish_id import FishRecognizer  # noqa: E402

OUT = Path('F:/tmp/fish_gate')
G = Path('gear_cache')
rng = random.Random(11)
FISHY = re.compile(r'fish|trout|bass\b|salmon|carp\b|catch|angl|pike|perch|walleye|sturgeon|shark|\beel\b|tuna|seafood|sushi|aquarium|koi\b|goldfish|crappie|bluegill|marlin|sardine|herring|mackerel', re.I)
labels = json.load(open(G / 'work/labels_all.json', encoding='utf-8'))
paths = {x['id']: x['path'] for x in json.load(open(G / 'work/manifest.json', encoding='utf-8'))}
oi = json.load(open(G / 'oi/labels.json', encoding='utf-8'))
# What the open catalogues say about each photo
said = {}
for f in glob.glob(str(G / 'open2/candidates-*.json')):
    d = json.load(open(f, encoding='utf-8'))
    for L in (d.values() if isinstance(d, dict) else [d]):
        for c in (L if isinstance(L, list) else [L]):
            if isinstance(c, dict) and 'id' in c:
                said[c['id']] = (c.get('text') or '') + ' ' + ' '.join(c.get('words') or [])
BAIT_FISH = {'bait-minnow', 'bait-cut', 'bait-shad'}
groups = {'oi-x': [], 'open-x': [], 'gear': []}
for k, v in labels.items():
    p = paths.get(k)
    if not p or not Path(p).exists():
        continue
    a = v['allowed']
    is_x = any(x.startswith('x-') for x in a)
    words = said.get(k, '')
    if k.startswith('oi:'):
        o = oi.get(k[3:], {})
        words += ' ' + ' '.join(o.get('yes', [])) + ' ' + ' '.join(map(str, (o.get('machine') or {})))
    if FISHY.search(words) or BAIT_FISH & set(a):
        continue
    if is_x:
        groups['oi-x' if k.startswith('oi:') else 'open-x'].append((k, p))
    else:
        groups['gear'].append((k, p))
for name, n in (('oi-x', 99999), ('open-x', 99999), ('gear', 1400)):
    rng.shuffle(groups[name])
    print(name, len(groups[name]), '->', n, flush=True)
    groups[name] = groups[name][:n]
groups['screens'] = [(Path(p).name, p) for p in sorted(glob.glob(str(OUT / 'screens/*')))]
groups['real-screens'] = [(Path(p).name, p) for p in sorted(glob.glob('F:/tmp/ui/shots/*.png') + glob.glob('F:/tmp/ui/*.png'))]
print({k: len(v) for k, v in groups.items()}, flush=True)

rec = FishRecognizer(Path('models/fish-id'))
done = {}
meta = {}
if (OUT / 'neg.npz').exists():
    done = dict(np.load(OUT / 'neg.npz'))
    meta = json.load(open(OUT / 'neg.json', encoding='utf-8'))
n, t0 = 0, time.time()
order = [(g, k, p) for g, L in groups.items() for k, p in L]
rng.shuffle(order)
for g, k, p in order:
    key = f'{g}|{k}'
    if key in done:
        continue
    try:
        with Image.open(p) as im:
            vec = rec.embed(im)
    except Exception as e:
        print('bad', key[:60], repr(e)[:80], flush=True)
        continue
    done[key] = vec.astype(np.float32)
    meta[key] = dict(group=g, path=str(p))
    n += 1
    if n % 250 == 0:
        np.savez(OUT / 'neg.npz', **done)
        json.dump(meta, open(OUT / 'neg.json', 'w', encoding='utf-8'))
        print(n, 'of', len(order), round((time.time() - t0) / n, 3), 's/photo', flush=True)
np.savez(OUT / 'neg.npz', **done)
json.dump(meta, open(OUT / 'neg.json', 'w', encoding='utf-8'))
print('DONE', len(done), flush=True)
