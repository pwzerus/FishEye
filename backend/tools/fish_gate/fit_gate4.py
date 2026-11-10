"""The gate that ships, and its exam: fit_gate4.py [--write cf hf]

Fitted on: fish training photos, those with a person in them (people holding their catch) counted extra,
against every not-fish photo. The exam, never fitted on: nonfish_u1/, hand-picked real catches, and the fish test sets.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
OUT = Path('F:/tmp/fish_gate')
M = Path('F:/FishEye/backend/models/fish-id')
C = Path('F:/FishEye/backend/fishid_cache')
NAME = 'vectors-bioclip-2-2957b322090f-int8-middle+whole.npz'
ENCODER = 'bioclip-2@2957b322090f/int8'
CATCH = ['c-bank/162924696', 'c-bank/162924700', 'c-bank/18550330', 'c-bank/35869656', 'c-bank/32732787', 'c-bank/80296753', 'c-hold/157796413', 'c-hold/193809192',
         'c-hold/4992464', 'c-hold/47898691', 'c-hold/45486882', 'c-hold/43821505', 'c-hold/65531731', 'c-hold/65544807', 'c-hold/68988087']


def fish(folder):
    z = np.load(folder / NAME)
    keep = [str(p['gbif_id']) for p in json.load(open(folder / 'manifest.json', encoding='utf-8'))['photos']]
    return np.stack([z[k] for k in keep if k in z.files]).astype(np.float32)


train_pos, test_pos, commons_pos = fish(C / 'train'), fish(C), fish(C / 'commons')
scores = np.load(OUT / 'person_scores.npz')
train_person, test_person = scores['tr'], scores['te']
PERSON_TRAIN = train_person >= np.sort(train_person)[-300]  # the 300 likeliest to show hands or people
PERSON_TEST = test_person >= np.sort(test_person)[-150]
neg = np.load(OUT / 'neg.npz')
meta = json.load(open(OUT / 'neg.json', encoding='utf-8'))
base = {}
for k in neg.files:
    base.setdefault(meta[k]['group'], []).append(neg[k])
base = {g: np.stack(v).astype(np.float32) for g, v in base.items()}


def folder_vectors(root):
    z = np.load(OUT / root / 'vectors_fish.npz')
    out = {}
    for k in z.files:
        out.setdefault(k.split('/')[0], []).append(z[k])
    return {g: np.stack(v).astype(np.float32) for g, v in out.items()}


hard = folder_vectors('nonfish')
t2 = folder_vectors('nonfish_t2') if (OUT / 'nonfish_t2/vectors_fish.npz').exists() else {}
exam = folder_vectors('nonfish_u1')
zc = np.load(OUT / 'catch/vectors_fish.npz')
catch_all = [zc[k] for k in CATCH]
extra = OUT / 'catch_flickr.json'
if extra.exists():
    zf = np.load(OUT / 'catch_flickr/vectors_fish.npz')
    catch_all += [zf[k] for k in json.load(open(extra, encoding='utf-8'))]
catch_all = np.stack(catch_all).astype(np.float32)
catch_fit, catch = catch_all[::2], catch_all[1::2]
print('fish', len(train_pos), '| test', len(test_pos), '| catches fitted', len(catch_fit), 'exam', len(catch), flush=True)
print('not fish', {**{g: len(v) for g, v in base.items()}, 'hard': sum(len(v) for v in hard.values()), 't2': sum(len(v) for v in t2.values())}, '| exam', sum(len(v) for v in exam.values()), flush=True)


def fit(x, y, w, steps=1800, lr=.03, l2=1e-6, scale=25.0):
    W, b = np.zeros(x.shape[1], np.float32), 0.0
    m1, m2, b1, b2 = np.zeros_like(W), np.zeros_like(W), 0.0, 0.0
    for t in range(1, steps + 1):
        z = scale * (x @ W) + b
        err = (1 / (1 + np.exp(-z)) - y) * w
        g = scale * (x.T @ err) + l2 * W
        gb = float(err.sum())
        m1, m2 = .9 * m1 + .1 * g, .999 * m2 + .001 * g * g
        W = W - lr * (m1 / (1 - .9 ** t)) / (np.sqrt(m2 / (1 - .999 ** t)) + 1e-8)
        b1, b2 = .9 * b1 + .1 * gb, .999 * b2 + .001 * gb * gb
        b = b - lr * (b1 / (1 - .9 ** t)) / (np.sqrt(b2 / (1 - .999 ** t)) + 1e-8)
    return (scale * W).astype(np.float32), float(b)


def run(catch_factor, hard_factor):
    pos_w = np.concatenate([np.where(PERSON_TRAIN, catch_factor, 1.0), np.full(len(catch_fit), catch_factor * 3)])
    pos_w = .5 * pos_w / pos_w.sum()
    groups = {**base, **hard, **t2}
    is_hard = {g: g in hard or g in t2 for g in groups}
    neg_w = np.concatenate([np.full(len(v), hard_factor if is_hard[g] else 1.0) for g, v in groups.items()])
    neg_w = .5 * neg_w / neg_w.sum()
    x = np.vstack([train_pos, catch_fit, *groups.values()]).astype(np.float32)
    y = np.concatenate([np.ones(len(train_pos) + len(catch_fit)), np.zeros(sum(len(v) for v in groups.values()))]).astype(np.float32)
    W, B = fit(x, y, np.concatenate([pos_w, neg_w]).astype(np.float32))
    prob = lambda v: 1 / (1 + np.exp(-(v @ W + B)))
    tot = sum(len(v) for v in exam.values())
    for t in (.1, .2, .3, .4, .5, .6, .7, .8):
        ex = {g: int((prob(v) >= t).sum()) for g, v in exam.items()}
        pt = test_pos[PERSON_TEST]
        print(f'catch*{catch_factor} hard*{hard_factor} t={t}: unrelated passed {sum(ex.values())}/{tot} {[(g[2:], n) for g, n in ex.items() if n]} | refused: hands+fish {float((prob(pt) < t).mean()):.3f} of {len(pt)}, catches {int((prob(catch) < t).sum())}/{len(catch)}, fish test {float((prob(test_pos) < t).mean()):.4f}, commons {float((prob(commons_pos) < t).mean()):.3f}', flush=True)
    return W, B


if __name__ == '__main__':
    results = {}
    i = sys.argv.index('--cfg')
    cf, hf = float(sys.argv[i + 1]), float(sys.argv[i + 2])
    results[(cf, hf)] = run(cf, hf)
    if '--write' in sys.argv:
        W, B = results[(cf, hf)]
        np.savez(OUT / 'gate-v2.npz', w=W, b=np.array(B, np.float32), encoder=np.array(ENCODER))
        print('wrote', flush=True)
