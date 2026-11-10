"""Open-licence photos with nothing to do with fishing, from Wikimedia Commons: collect_nonfish.py queries.json root [per_query] [max_per_group]

One job at a time, 3 s between requests. Saves 500 px thumbnails and found.json in root/<group>/.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, 'F:/FishEye/backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.cli.fish_id_commons import licence_ok  # noqa: E402

UA = 'open-licence-photo-search/1.0 (small one-off script)'
API = 'https://commons.wikimedia.org/w/api.php'
QUERIES = json.load(open(sys.argv[1], encoding='utf-8'))
ROOT = Path(sys.argv[2])
PER = int(sys.argv[3]) if len(sys.argv) > 3 else 8
MAX = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 40
FISHY = re.compile(r'fish|angl(er|ing)|trout|salmon|\bbass\b|carp\b|tuna|sushi|seafood|aquarium|shark|\beel\b|catch', re.I)
SKIP = re.compile(r'\.svg$|\.pdf$|\.djvu$|\.tiff?$|\.ogv$|\.webm$', re.I)


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            if attempt == 4:
                raise
            print('retry', str(e)[:60], flush=True)
            time.sleep(20 * (attempt + 1))


for group, qs in QUERIES.items():
    d = ROOT / group
    d.mkdir(parents=True, exist_ok=True)
    fj = d / 'found.json'
    found = json.load(open(fj, encoding='utf-8')) if fj.exists() else {}
    for q in qs:
        params = dict(action='query', format='json', generator='search', gsrnamespace=6, gsrsearch=q + ' filetype:bitmap', gsrlimit=30,
                      prop='imageinfo', iiprop='url|size|extmetadata|mime', iiurlwidth=500,
                      iiextmetadatafilter='LicenseShortName|Artist|LicenseUrl')
        try:
            data = json.loads(get(API + '?' + urllib.parse.urlencode(params)))
        except Exception as e:
            print('ERR', group, q, str(e)[:80], flush=True)
            continue
        time.sleep(2.2)
        pages = sorted(data.get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 0))
        kept = 0
        for p in pages:
            if kept >= PER:
                break
            t = p['title']
            if t in found or SKIP.search(t) or FISHY.search(t) or 'imageinfo' not in p:
                continue
            ii = p['imageinfo'][0]
            m = ii.get('extmetadata', {})
            lic = m.get('LicenseShortName', {}).get('value', '')
            if not licence_ok(lic) or ii.get('mime') not in ('image/jpeg', 'image/png') or not ii.get('thumburl'):
                continue
            if ii['width'] < 300 or ii['height'] < 300:
                continue
            found[t] = dict(title=t, pageid=p['pageid'], query=q, thumb=ii['thumburl'], page_url=ii['descriptionurl'], licence=lic,
                            artist_html=m.get('Artist', {}).get('value', ''))
            kept += 1
        print(group, q, len(found), flush=True)
    n = 0
    for t, f in list(found.items())[:MAX]:
        out = d / f"{f['pageid']}.jpg"
        if out.exists():
            continue
        try:
            out.write_bytes(get(f['thumb']))
            n += 1
        except Exception as e:
            print('thumb fail', t[:50], str(e)[:60], flush=True)
        time.sleep(2.2)
    json.dump(found, open(fj, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('DONE', group, len(found), 'new', n, flush=True)
print('ALL DONE', flush=True)
