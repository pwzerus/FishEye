"""Synthetic screenshots, documents, slides, charts and forms: not-fish examples the training photos lack.

make_screens.py outdir count seed
Random layouts, no real page copied. The text comes from FishEye's own Chinese and English handbook.
"""
import glob
import json
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

out, count, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
os.makedirs(out, exist_ok=True)
rng = random.Random(seed)
FONT_DIR = 'C:/Windows/Fonts/'
LATIN = [f for f in ('arial.ttf', 'arialbd.ttf', 'times.ttf', 'calibri.ttf', 'segoeui.ttf', 'georgia.ttf', 'verdana.ttf', 'tahoma.ttf', 'consola.ttf') if os.path.exists(FONT_DIR + f)]
CJK = [f for f in ('msyh.ttc', 'msyhbd.ttc', 'simsun.ttc', 'simhei.ttf', 'Deng.ttf', 'simkai.ttf') if os.path.exists(FONT_DIR + f)]
MONO = [f for f in ('consola.ttf', 'cour.ttf') if os.path.exists(FONT_DIR + f)]
_cache = {}
T = 'F:/FishEye/backend/app/knowledge/translations/'
ZH = [v for n in ('zh_handbook.json', 'zh_guides.json') for v in json.load(open(T + n, encoding='utf-8')).values()]
sys.path.insert(0, 'F:/FishEye/backend')
EN = []
for f in glob.glob('F:/tmp/translate/handbook_*.tsv') + glob.glob('F:/tmp/translate/guides_*.tsv'):
    EN += [l.split('\t', 1)[1].strip() for l in open(f, encoding='utf-8') if '\t' in l]
# Photos pasted into some layouts: not-gear photos, and sometimes a fish (a page about fish is still a page).
PHOTOS = glob.glob('F:/FishEye/backend/gear_cache/oi/img/*.jpg')[:1500]
FISH = glob.glob('F:/FishEye/backend/fishid_cache/train/photos/*/*.jpg')[:3000]


def font(size, kind):
    name = rng.choice({'cjk': CJK, 'mono': MONO}.get(kind, LATIN))
    key = (name, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(FONT_DIR + name, size)
    return _cache[key]


def text(kind):
    return rng.choice(ZH if kind == 'cjk' else EN)


def pastel():
    return tuple(rng.randint(205, 250) for _ in range(3))


def strong():
    base = [rng.randint(20, 90), rng.randint(60, 150), rng.randint(120, 230)]
    rng.shuffle(base)
    return tuple(base)


def wrap(d, s, f, width):
    lines, line = [], ''
    for ch in s:
        if d.textlength(line + ch, font=f) > width:
            lines.append(line)
            line = ch
        else:
            line += ch
    if line:
        lines.append(line)
    return lines


def para(d, x, y, width, kind, size, color, n_lines=None, ymax=10 ** 6):
    f = font(size, kind)
    lines = wrap(d, text(kind), f, width)
    if n_lines:
        lines = lines[:n_lines]
    for l in lines:
        if y + size * 1.5 > ymax:
            break
        d.text((x, y), l, fill=color, font=f)
        y += int(size * rng.uniform(1.3, 1.7))
    return y


def paste_photo(im, x, y, w, h, fish=False):
    path = rng.choice(FISH if fish and FISH else PHOTOS or FISH)
    try:
        p = Image.open(path).convert('RGB')
    except Exception:
        return
    s = max(w / p.width, h / p.height)
    p = p.resize((max(w, int(p.width * s) + 1), max(h, int(p.height * s) + 1)))
    im.paste(p.crop((0, 0, w, h)), (x, y))


def box(d, xy, fill, line=None, r=None):
    r = rng.randint(0, 18) if r is None else r
    d.rounded_rectangle(xy, r, fill=fill, outline=line, width=rng.randint(1, 3))


def document(W, H, kind):
    bg = rng.choice([(255, 255, 255), (253, 253, 248), (247, 247, 250), (250, 246, 238)])
    im = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(im)
    m = int(W * rng.uniform(.05, .14))
    y = int(H * .05)
    y = para(d, m, y, W - 2 * m, kind, rng.randint(26, 46), strong(), 2) + 12
    size = rng.randint(13, 22)
    col = (rng.randint(20, 70),) * 3
    while y < H * .93:
        r = rng.random()
        if r < .55:
            y = para(d, m, y, W - 2 * m, kind, size, col, ymax=H) + rng.randint(8, 22)
        elif r < .75:
            for _ in range(rng.randint(2, 5)):
                d.ellipse((m, y + size // 3, m + 7, y + size // 3 + 7), fill=col)
                y = para(d, m + 18, y, W - 2 * m - 18, kind, size, col, 2, ymax=H) + 4
            y += 10
        elif r < .9:
            y = table(d, m, y, W - 2 * m, kind, size) + 14
        else:
            y = para(d, m, y, W - 2 * m, kind, size + 7, strong(), 1, ymax=H) + 10
    return im


def table(d, x, y, width, kind, size):
    rows, cols = rng.randint(3, 8), rng.randint(2, 6)
    h, w = int(size * 2.1), width // cols
    head = pastel()
    for r in range(rows):
        for c in range(cols):
            d.rectangle((x + c * w, y + r * h, x + (c + 1) * w, y + (r + 1) * h), fill=head if r == 0 else None, outline=(170, 170, 180))
            f = font(size - 2, kind)
            s = text(kind)[:rng.randint(2, 12)]
            d.text((x + c * w + 5, y + r * h + 5), wrap(d, s, f, w - 10)[0], fill=(40, 40, 50), font=f)
    return y + rows * h


def slide(W, H, kind):
    bg = rng.choice([(255, 255, 255), (250, 248, 255), pastel(), (28, 30, 44)])
    dark = sum(bg) < 200
    fg = (235, 235, 245) if dark else (35, 35, 60)
    im = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(im)
    if rng.random() < .5:
        d.rectangle((0, 0, W, int(H * .13)), fill=strong())
        para(d, int(W * .04), int(H * .03), int(W * .9), kind, rng.randint(26, 44), (255, 255, 255), 1)
    else:
        para(d, int(W * .05), int(H * .04), int(W * .9), kind, rng.randint(28, 48), fg, 1)
    y0 = int(H * .2)
    n = rng.randint(2, 5)
    w = int(W * .9 / n) - 14
    for i in range(n):
        x = int(W * .05) + i * (w + 14)
        h = rng.randint(int(H * .3), int(H * .7))
        fill = pastel() if not dark else tuple(rng.randint(45, 90) for _ in range(3))
        box(d, (x, y0, x + w, y0 + h), fill, line=strong())
        y = y0 + 10
        for _ in range(rng.randint(1, 4)):
            y = para(d, x + 10, y, w - 20, kind, rng.randint(12, 20), fg, 3, ymax=y0 + h - 6) + 8
        if i < n - 1 and rng.random() < .5:
            d.line((x + w, y0 + h // 2, x + w + 14, y0 + h // 2), fill=strong(), width=3)
    return im


def diagram(W, H, kind):
    im = Image.new('RGB', (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    boxes = []
    for _ in range(rng.randint(5, 12)):
        w, h = rng.randint(W // 8, W // 3), rng.randint(H // 12, H // 5)
        x, y = rng.randint(10, W - w - 10), rng.randint(10, H - h - 10)
        box(d, (x, y, x + w, y + h), rng.choice([pastel(), (235, 228, 255), (222, 234, 255)]), line=strong())
        para(d, x + 8, y + 6, w - 16, kind, rng.randint(11, 18), (40, 40, 70), 3, ymax=y + h - 4)
        boxes.append((x + w // 2, y + h // 2))
    for a, b in zip(boxes, boxes[1:]):
        d.line((a, b), fill=(90, 80, 170), width=2)
    return im


def chart(W, H, kind):
    im = Image.new('RGB', (W, H), rng.choice([(255, 255, 255), (248, 249, 252), (24, 26, 34)]))
    d = ImageDraw.Draw(im)
    dark = im.getpixel((0, 0))[0] < 100
    axis = (200, 200, 210) if dark else (70, 70, 80)
    para(d, 30, 14, W - 60, kind, rng.randint(18, 30), axis, 1)
    x0, y0, x1, y1 = 70, 70, W - 30, H - 50
    d.line((x0, y1, x1, y1), fill=axis, width=2)
    d.line((x0, y0, x0, y1), fill=axis, width=2)
    for i in range(1, 6):
        y = y1 - (y1 - y0) * i // 6
        d.line((x0, y, x1, y), fill=(120, 120, 130) if dark else (225, 225, 232))
        d.text((10, y - 8), str(rng.randint(1, 900)), fill=axis, font=font(13, 'lat'))
    n, t = rng.randint(4, 16), rng.choice(['bar', 'line', 'area', 'pie'])
    if t == 'bar':
        w = (x1 - x0) // n
        for i in range(n):
            h = rng.randint(10, y1 - y0)
            d.rectangle((x0 + i * w + 4, y1 - h, x0 + (i + 1) * w - 4, y1), fill=strong())
    elif t == 'pie':
        c, r, start = ((x0 + x1) // 2, (y0 + y1) // 2), min(x1 - x0, y1 - y0) // 2 - 6, 0
        while start < 360:
            end = min(360, start + rng.randint(30, 120))
            d.pieslice((c[0] - r, c[1] - r, c[0] + r, c[1] + r), start, end, fill=strong())
            start = end
    else:
        for _ in range(rng.randint(1, 3)):
            pts = [(x0 + (x1 - x0) * i // max(1, n - 1), rng.randint(y0, y1)) for i in range(n)]
            d.line(pts, fill=strong(), width=3)
    return im


def webpage(W, H, kind):
    bg = rng.choice([(255, 255, 255), (246, 247, 240), (245, 247, 250), (18, 20, 28)])
    dark = bg[0] < 100
    fg = (225, 228, 235) if dark else (35, 40, 50)
    card = (34, 37, 48) if dark else (255, 255, 255)
    im = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(im)
    bar = int(H * .07) + 30
    d.rectangle((0, 0, W, bar), fill=card)
    para(d, 20, 16, 200, kind, 24, strong(), 1)
    x = W // 3
    for _ in range(rng.randint(3, 7)):
        f = font(15, kind)
        s = text(kind)[:rng.randint(2, 8)]
        d.text((x, 20), s, fill=fg, font=f)
        x += int(d.textlength(s, font=f)) + 24
    y = bar + 24
    y = para(d, 30, y, W - 60, kind, rng.randint(26, 44), fg, 2) + 16
    cols = rng.randint(1, 4)
    w = (W - 30 * (cols + 1)) // cols
    while y < H - 80:
        h = rng.randint(120, 330)
        for c in range(cols):
            x = 30 + c * (w + 30)
            box(d, (x, y, x + w, y + h), card, line=(70, 72, 84) if dark else (225, 228, 232))
            yy = y + 12
            if rng.random() < .45:
                ph = int(h * .5)
                paste_photo(im, x + 8, yy, w - 16, ph, fish=rng.random() < .35)
                yy += ph + 8
            yy = para(d, x + 12, yy, w - 24, kind, rng.randint(13, 18), fg, 4, ymax=y + h - 30)
            if rng.random() < .4:
                b = (x + 12, y + h - 34, x + 112, y + h - 8)
                box(d, b, strong(), r=8)
        y += h + 24
    return im


def phone(W, H, kind):
    return webpage(min(W, H) // 2 + 120, max(W, H), kind)


def code(W, H, kind):
    im = Image.new('RGB', (W, H), rng.choice([(30, 30, 30), (40, 42, 54), (250, 250, 250), (0, 43, 54)]))
    d = ImageDraw.Draw(im)
    dark = im.getpixel((0, 0))[0] < 100
    y, size = 16, rng.randint(13, 20)
    words = 'def class return import from if else for while const let function async await self none true false print'.split()
    while y < H - size:
        x = 12 + rng.choice([0, 0, 24, 48, 72, 96])
        for _ in range(rng.randint(1, 8)):
            s = rng.choice(words) if rng.random() < .7 else ''.join(rng.choice('abcdefghij_()[]{}=:,0123') for _ in range(rng.randint(2, 12)))
            f = font(size, 'mono')
            c = tuple(rng.randint(120, 255) for _ in range(3)) if dark else tuple(rng.randint(0, 130) for _ in range(3))
            d.text((x, y), s, fill=c, font=f)
            x += int(d.textlength(s + ' ', font=f))
        y += int(size * 1.45)
    return im


def form(W, H, kind):
    im = Image.new('RGB', (W, H), rng.choice([(255, 255, 255), (247, 248, 243), (240, 242, 247)]))
    d = ImageDraw.Draw(im)
    m = W // 8
    y = para(d, m, 30, W - 2 * m, kind, rng.randint(24, 38), strong(), 1) + 18
    while y < H - 110:
        y = para(d, m, y, W - 2 * m, kind, 15, (70, 70, 80), 1) + 2
        h = rng.choice([38, 44, 90])
        box(d, (m, y, W - m, y + h), (255, 255, 255), line=(200, 202, 210), r=8)
        para(d, m + 10, y + 10, W - 2 * m - 20, kind, 14, (120, 120, 130), 1)
        y += h + 16
    box(d, (m, y, W - m, y + 44), strong(), r=10)
    return im


def chat(W, H, kind):
    im = Image.new('RGB', (W, H), rng.choice([(255, 255, 255), (236, 229, 221), (17, 24, 39)]))
    d = ImageDraw.Draw(im)
    y = 20
    while y < H - 90:
        f = font(16, kind)
        lines = wrap(d, text(kind), f, int(W * .6))[:4]
        h = 26 * len(lines) + 16
        left = rng.random() < .5
        x = 20 if left else int(W * .32)
        box(d, (x, y, x + int(W * .64), y + h), (255, 255, 255) if left else (200, 240, 190), r=14)
        for i, l in enumerate(lines):
            d.text((x + 12, y + 8 + 26 * i), l, fill=(30, 30, 30), font=f)
        y += h + 14
    return im


def sheet(W, H, kind):
    im = Image.new('RGB', (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    table(d, 0, 40, W, kind, rng.randint(13, 17))
    y = 0
    h = rng.randint(22, 30)
    w = rng.randint(70, 150)
    for r in range(H // h):
        for c in range(W // w + 1):
            d.rectangle((c * w, r * h, (c + 1) * w, (r + 1) * h), outline=(214, 216, 220))
            if rng.random() < .5:
                d.text((c * w + 4, r * h + 4), text(kind)[:rng.randint(1, 8)] if rng.random() < .5 else str(rng.randint(0, 99999)), fill=(40, 40, 40), font=font(13, kind))
    return im


def collage(W, H, kind):
    """A screenshot of screenshots: a row of small pages inside a form, as uploaded by a tester."""
    im = Image.new('RGB', (W, H), (248, 249, 244))
    n = rng.randint(2, 5)
    w = int(W / n) - 8
    for i in range(n):
        p = rng.choice(MAKERS)(w * 2, int(w * 1.5), kind).resize((w, int(w * .75)))
        im.paste(p, (4 + i * (w + 8), rng.randint(4, 40)))
    d = ImageDraw.Draw(im)
    y = int(w * .75) + 60
    while y < H - 20:
        y = para(d, 16, y, W - 32, kind, rng.randint(13, 18), (60, 60, 70), 2, ymax=H) + 12
    return im


MAKERS = [document, slide, diagram, chart, webpage, code, form, chat, sheet]
ALL = MAKERS + [phone, phone, collage, collage, document, slide, diagram]
n = 0
while n < count:
    W, H = rng.randint(500, 1600), rng.randint(420, 1300)
    kind = rng.choice(['cjk', 'cjk', 'lat'])
    maker = rng.choice(ALL)
    try:
        im = maker(W, H, kind)
    except Exception as e:
        print('skip', maker.__name__, repr(e)[:100], flush=True)
        continue
    name = f'{seed}_{n:05d}_{maker.__name__}'
    if rng.random() < .5:
        im.save(os.path.join(out, name + '.png'))
    else:
        im.save(os.path.join(out, name + '.jpg'), quality=rng.randint(60, 92))
    n += 1
print('made', n)
