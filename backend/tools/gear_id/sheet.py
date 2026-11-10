"""Contact sheets for checking labels by eye.

    python -I sheet.py <list.json> <out prefix> [cols rows tile]

list.json: [{"path": ..., "rotate": 0, "note": "short text"}, ...]
Writes <out prefix>-01.jpg, -02.jpg, ...: numbered tiles (numbering runs on
across sheets, starting at 1) with the note under each.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

items = json.loads(Path(sys.argv[1]).read_text("utf-8"))
prefix = Path(sys.argv[2])
cols, rows, tile = (int(x) for x in (sys.argv[3:6] if len(sys.argv) > 5 else (6, 5, 200)))
try:
    font = ImageFont.truetype("arial.ttf", 15)
except OSError:
    font = ImageFont.load_default()
cap = 20
per = cols * rows
prefix.parent.mkdir(parents=True, exist_ok=True)
for s in range(0, len(items), per):
    sheet = Image.new("RGB", (cols * tile, rows * (tile + cap)), "white")
    d = ImageDraw.Draw(sheet)
    for k, it in enumerate(items[s:s + per]):
        img = Image.open(it["path"]).convert("RGB")
        if it.get("rotate"):
            img = img.rotate(it["rotate"], expand=True)
        img.thumbnail((tile - 4, tile - 4))
        x, y = (k % cols) * tile, (k // cols) * (tile + cap)
        sheet.paste(img, (x + (tile - img.width) // 2, y + (tile - img.height) // 2))
        d.rectangle([x, y + tile, x + tile, y + tile + cap], fill="black")
        d.text((x + 3, y + tile + 2), f"{s + k + 1} {it.get('note', '')}"[:28], fill="yellow", font=font)
    out = f"{prefix}-{s // per + 1:02d}.jpg"
    sheet.save(out, quality=85)
    print(out)
