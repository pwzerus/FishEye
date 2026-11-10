"""Find fish photos with a person in them: a probe trained on the people / no-people photos we have.

person_probe.py -> person_scores.npz (train, test, commons scores), and sheets of the likeliest ones to check by eye.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding='utf-8')
OUT = Path('F:/tmp/fish_gate')
C = Path('F:/FishEye/backend/fishid_cache')
NAME = 'vectors-bioclip-2-2957b322090f-int8-middle+whole.npz'


def fish(folder):
    z = np.load(folder / NAME)
    ph = [p for p in json.load(open(folder / 'manifest.json', encoding='utf-8'))['photos'] if str(p['gbif_id']) in z.files]
    return ph, np.stack([z[str(p['gbif_id'])] for p in ph]).astype(np.float32)


def groups(root):
    z = np.load(OUT / root / 'vectors_fish.npz')
    out = {}
    for k in z.files:
        out.setdefault(k.split('/')[0], []).append(z[k])
    return {g: np.stack(v).astype(np.float32) for g, v in out.items()}


g1, g2 = groups('nonfish'), groups('nonfish_u1')
yes = [g1[k] for k in ('people', 'presidents', 'celebrities', 'sports') if k in g1] + [g2[k] for k in ('u-leaders', 'u-famous') if k in g2]
no = [g1[k] for k in g1 if k not in ('people', 'presidents', 'celebrities', 'sports', 'homework', 'comics', 'art')] + [g2[k] for k in ('u-sky', 'u-places', 'u-space', 'u-food', 'u-things', 'u-animals', 'u-aquatic') if k in g2]
pos, neg = np.vstack(yes), np.vstack(no)
ph_tr, tr = fish(C / 'train')
ph_te, te = fish(C)
ph_co, co = fish(C / 'commons')
# fish photos without any hint of a person make the bulk of the "no" side
x = np.vstack([pos, neg, tr[::2]]).astype(np.float32)
y = np.concatenate([np.ones(len(pos)), np.zeros(len(neg) + len(tr[::2]))]).astype(np.float32)
w = np.concatenate([np.full(len(pos), .5 / len(pos)), np.full(len(neg) + len(tr[::2]), .5 / (len(neg) + len(tr[::2])))]).astype(np.float32)
W, b = np.zeros(x.shape[1], np.float32), 0.0
m1, m2 = np.zeros_like(W), np.zeros_like(W)
for t in range(1, 901):
    z = 25 * (x @ W) + b
    err = (1 / (1 + np.exp(-z)) - y) * w
    g = 25 * (x.T @ err)
    m1, m2 = .9 * m1 + .1 * g, .999 * m2 + .001 * g * g
    W = W - .03 * (m1 / (1 - .9 ** t)) / (np.sqrt(m2 / (1 - .999 ** t)) + 1e-8)
    b -= .03 * float(err.sum())
s = lambda v: 25 * (v @ W) + b
np.savez(OUT / 'person_scores.npz', tr=s(tr), te=s(te), co=s(co))
cell, cols, per = 225, 10, 60


def sheet(name, ph, score, n, folder):
    order = np.argsort(-score)[:n]
    rows = (len(order) + cols - 1) // cols
    S = Image.new('RGB', (cols * cell, rows * cell), 'white')
    d = ImageDraw.Draw(S)
    keys = []
    for i, j in enumerate(order):
        p = ph[j]
        f = folder / p['file']
        im = Image.open(f).convert('RGB')
        im.thumbnail((cell - 6, cell - 18))
        x_, y_ = (i % cols) * cell, (i // cols) * cell
        S.paste(im, (x_ + 3, y_ + 16))
        d.text((x_ + 3, y_ + 1), f"{i}:{str(p['gbif_id'])[-7:]}", fill='black')
        keys.append(str(p['gbif_id']))
    S.save(OUT / f'{name}.jpg', quality=78)
    json.dump(keys, open(OUT / f'{name}.json', 'w'))
    print(name, S.size, flush=True)


sheet('persons_train', ph_tr, s(tr), 100, C / 'train')
sheet('persons_test', ph_te, s(te), 100, C)
print('done', float((s(tr) > 0).mean()), float((s(te) > 0).mean()))
