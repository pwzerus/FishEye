"""Count photos of fishing gear in open image catalogues, by their text alone.

    python -I scan_catalogs.py <source> <out_dir> [--workers N] [--sample N]

Sources (all commercial-use licences only; docs/data-sources.md):
  pd12m          Spawning/PD12M on Hugging Face: 12.4M public-domain / CC0
                 photos, a machine caption each (metadata parquet, 2.3 GB).
  yfcc           dalle-mini/YFCC100M_OpenAI_subset metadata on Hugging Face:
                 14.8M Flickr photos with title, description and tags (5.2 GB
                 of jsonl.gz). Only "Attribution License" (CC BY 2.0) rows
                 are kept; the others are only counted. Images are on AWS,
                 s3://multimedia-commons/data/images/<key[:3]>/<key[3:6]>/<key>.jpg.
  smithsonian    Smithsonian Open Access on AWS (CC0): the museums that hold
                 gear (NMAH, NMAI, NMNH Anthropology, Cooper Hewitt, Postal),
                 objects with a CC0 image only.
  commoncatalog  common-canvas/commoncatalog-cc-by: every CC BY Flickr photo
                 in YFCC (14.6M) but 21 TB with the images inside, so only a
                 random --sample of its files is read (text columns only) and
                 the count is scaled up.

Nothing but text is read; no image is downloaded. Each source writes
<out_dir>/<source>.jsonl (one line per matching photo: id, licence, image
address, the words that matched, a short text) and <source>.summary.json
(how many were read and matched, per item and group). Files already read
are listed in <source>.done and skipped on a re-run.

The names searched for are in keywords.py; how a record matches is in
Matcher below.
"""
import argparse
import concurrent.futures as cf
import gzip
import io
import json
import random
import re
import sys
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import keywords as K  # noqa: E402

UA = "FishEye-dataset-scan/1.0 (feedback.fisheyefishing@gmail.com)"
CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯]")
NON_WORD = re.compile(r"[^\w]+", re.UNICODE)
SEGMENT = re.compile(r"[|,;!?\n、。，]|\.\s")


def norm(text: str) -> str:
    """Lower case, accents kept, apostrophes dropped, everything not a
    letter or digit turned into one space."""
    text = unicodedata.normalize("NFC", text).lower().replace("'", "").replace("’", "")
    return NON_WORD.sub(" ", text).strip()


class Matcher:
    """Names are looked up as word n-grams (1 to 6 words) of the record's
    text, and also with their spaces taken out, so the Flickr tag
    "fishingreel" finds "fishing reel". Names in Chinese, Japanese or
    Korean are looked for as plain substrings."""

    def __init__(self):
        self.terms: dict[str, list[tuple[str, str, str]]] = {}
        self.cjk: list[tuple[str, str, str, str]] = []
        for term, kind, target, strength in K.all_terms():
            if CJK.search(term):
                self.cjk.append((term.lower(), kind, target, strength))
                continue
            n = norm(term)
            if not n:
                continue
            for key in {n, n.replace(" ", "")}:
                if " " not in key and len(key) < 4 and key != n:
                    continue  # "pe line" -> "peline" is fine, "ul" alone is not
                self.terms.setdefault(key, []).append((kind, target, strength))
        self.ctx = {norm(c) for c in K.CONTEXT if not CJK.search(c)}
        self.ctx |= {norm(c).replace(" ", "") for c in K.CONTEXT if " " in c}
        self.ctx_cjk = [c for c in K.CONTEXT if CJK.search(c)]
        self.notgear = {norm(c) for c in K.NOT_GEAR_HINTS}

    WINDOW = 5  # a weak name counts with a fishing word at most this many words away

    @staticmethod
    def grams(tokens, n_max=6):
        """(start, end, text) of every run of 1 to n_max words."""
        for i in range(len(tokens)):
            for n in range(1, n_max + 1):
                if i + n > len(tokens):
                    break
                yield i, i + n, " ".join(tokens[i:i + n])

    def match(self, text: str):
        """Returns {"items": {id: "strong"|"weak"}, "groups": {...}, "context": [...],
        "words": [...], "not_gear": [...]} or None when nothing counts.

        A strong name counts wherever it is. A weak name counts only when a
        strong name is in the same record, or a fishing word (CONTEXT) is at
        most WINDOW words from it and isn't the phrase it sits in ("fly" in
        "fly fishing" is no fly). A name inside a longer name that matched
        ("line" in "fishing line") adds nothing of its own."""
        low = text.lower()
        # Names never run across a tag, field or sentence break: the tags
        # "fishing" and "fly" next to each other are not "fishing fly". The
        # word count runs on across breaks, so a fishing tag still counts as
        # context for the tag beside it.
        tokens, spans = [], []
        for seg in SEGMENT.split(text):
            seg_tokens = norm(seg).split()
            base = len(tokens)
            spans += [(a + base, b + base, g) for a, b, g in self.grams(seg_tokens)]
            tokens += seg_tokens
        hits = []  # (start, end, word, kind, target, strength)
        ctx_spans = []
        notgear = set()
        for a, b, g in spans:
            for kind, target, strength in self.terms.get(g, ()):
                hits.append((a, b, g, kind, target, strength))
            if g in self.ctx:
                ctx_spans.append((a, b, g))
            if g in self.notgear:
                notgear.add(g)
        has_cjk = bool(CJK.search(text))
        cjk_ctx = has_cjk and any(c in low for c in self.ctx_cjk)
        if has_cjk:
            for term, kind, target, strength in self.cjk:
                if term in low:
                    hits.append((-1, -1, term, kind, target, strength))
        if not hits:
            return None
        any_strong = any(h[5] == "strong" for h in hits)

        def inside(a, b, others):
            return any(oa <= a and b <= ob and (oa, ob) != (a, b) for oa, ob in others)

        hit_spans = [(h[0], h[1]) for h in hits if h[0] >= 0]
        items, groups, words = {}, {}, set()
        for a, b, word, kind, target, strength in hits:
            if a >= 0 and inside(a, b, hit_spans):
                continue
            if strength == "weak" and a >= 0 and any(ca <= a and b <= cb and (ca, cb) != (a, b)
                                                     for ca, cb, _ in ctx_spans):
                continue  # "fly" in "fly fishing" is no fly
            if strength == "weak" and not any_strong:
                if a < 0:
                    ok = cjk_ctx
                else:
                    ok = any(not (ca <= a and b <= cb) and not (a <= ca and cb <= b)
                             and min(abs(ca - b), abs(a - cb)) <= self.WINDOW for ca, cb, _ in ctx_spans)
                if not ok:
                    continue
            table = items if kind == "item" else groups
            if table.get(target) != "strong":
                table[target] = strength
            words.add(word)
        if not items and not groups:
            return None
        return {"items": items, "groups": groups, "words": sorted(words),
                "context": sorted({c for _, _, c in ctx_spans})[:8], "not_gear": sorted(notgear)}


# --------------------------------------------------------------------------
def fetch(url: str, tries: int = 5) -> bytes:
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retried, then raised
            if attempt == tries - 1:
                raise
            wait = 5 * (attempt + 1)
            if "429" in str(e):
                wait = 60
            time.sleep(wait)
    raise RuntimeError("unreachable")


class Out:
    """Thread-safe writer of matches, the done list, and the counts."""

    def __init__(self, out_dir: Path, source: str):
        self.dir = out_dir
        self.source = source
        self.lock = threading.Lock()
        self.jsonl = open(out_dir / f"{source}.jsonl", "a", encoding="utf-8")
        self.done_path = out_dir / f"{source}.done"
        self.done = set(self.done_path.read_text("utf-8").split()) if self.done_path.exists() else set()
        self.done_f = open(self.done_path, "a", encoding="utf-8")
        sp = out_dir / f"{source}.summary.json"
        s = json.loads(sp.read_text("utf-8")) if sp.exists() else {}
        self.read = Counter(s.get("read", {}))
        self.items = Counter(s.get("items", {}))
        self.items_strong = Counter(s.get("items_strong", {}))
        self.groups = Counter(s.get("groups", {}))
        self.matched = s.get("matched", 0)
        self.extra = Counter(s.get("extra", {}))

    def add_file(self, name: str, rows: list[dict], read: Counter, extra: Counter | None = None):
        with self.lock:
            for r in rows:
                self.jsonl.write(json.dumps(r, ensure_ascii=False) + "\n")
                self.matched += 1
                for i, s in r["m"]["items"].items():
                    self.items[i] += 1
                    if s == "strong":
                        self.items_strong[i] += 1
                for g in r["m"]["groups"]:
                    if not r["m"]["items"]:
                        self.groups[g] += 1
            self.read.update(read)
            if extra:
                self.extra.update(extra)
            self.jsonl.flush()
            self.done_f.write(name + "\n")
            self.done_f.flush()
            self.done.add(name)
            self.save()

    def save(self):
        (self.dir / f"{self.source}.summary.json").write_text(json.dumps({
            "read": self.read, "matched": self.matched, "items": dict(self.items.most_common()),
            "items_strong": dict(self.items_strong.most_common()), "groups_only": dict(self.groups.most_common()),
            "extra": self.extra, "files_done": len(self.done),
        }, indent=1, ensure_ascii=False), "utf-8")


def run_files(names, work, out: Out, workers: int, label: str):
    todo = [n for n in names if n not in out.done]
    print(f"{label}: {len(names)} files, {len(todo)} to read", flush=True)
    t0 = time.time()
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(work, n): n for n in todo}
        for k, f in enumerate(cf.as_completed(futs), 1):
            n = futs[f]
            try:
                f.result()
            except Exception as e:  # noqa: BLE001 - reported, the file stays not done
                print(f"  FAILED {n}: {e}", flush=True)
            if k % 25 == 0 or k == len(todo):
                el = time.time() - t0
                print(f"  {k}/{len(todo)} files, {out.matched} matches, {el/60:.1f} min, "
                      f"~{el / k * (len(todo) - k) / 60:.0f} min left", flush=True)


# --------------------------------------------------------------------------
HF = "https://huggingface.co/datasets"


def hf_files(repo: str, prefix: str, suffix: str):
    from huggingface_hub import HfApi
    info = HfApi().dataset_info(repo, files_metadata=True)
    return sorted(s.rfilename for s in info.siblings if s.rfilename.startswith(prefix) and s.rfilename.endswith(suffix))


def scan_pd12m(out: Out, workers: int, m: Matcher):
    import pyarrow.parquet as pq
    repo = "Spawning/PD12M"
    names = hf_files(repo, "metadata/", ".parquet")

    def work(name):
        data = fetch(f"{HF}/{repo}/resolve/main/{name}")
        t = pq.read_table(io.BytesIO(data), columns=["id", "url", "caption", "license", "source", "width", "height"])
        rows, read = [], Counter()
        for r in t.to_pylist():
            read["rows"] += 1
            hit = m.match(r["caption"] or "")
            if hit:
                rows.append({"id": r["id"], "licence": r["license"], "src": r["source"], "image": r["url"],
                             "w": r["width"], "h": r["height"], "text": (r["caption"] or "")[:300], "m": hit})
        out.add_file(name, rows, read)

    run_files(names, work, out, workers, "PD12M")


def scan_yfcc(out: Out, workers: int, m: Matcher):
    repo = "dalle-mini/YFCC100M_OpenAI_subset"
    names = hf_files(repo, "metadata/", ".jsonl.gz")

    def work(name):
        # "\n" only: splitlines() also breaks at U+2028 inside the text
        raw = gzip.decompress(fetch(f"{HF}/{repo}/resolve/main/{name}")).decode("utf-8")
        lines = [x for x in raw.split("\n") if x.strip()]
        rows, read, extra = [], Counter(), Counter()
        for line in lines:
            r = json.loads(line)
            lic = r.get("licensename") or ""
            read["rows"] += 1
            read[lic] += 1
            tags = urllib.parse.unquote_plus(r.get("usertags") or "")
            text = " | ".join([r.get("title_clean") or "", r.get("description_clean") or "", tags.replace(",", " , ")])
            hit = m.match(text)
            if not hit:
                continue
            if lic != "Attribution License":
                extra["matched_other_licence:" + lic] += 1
                continue
            rows.append({"id": r["photoid"], "licence": "CC BY 2.0", "author": r.get("unickname"),
                         "page": r.get("pageurl"), "key": r.get("key"),
                         "image": f"https://multimedia-commons.s3.amazonaws.com/data/images/{r['key'][:3]}/"
                                  f"{r['key'][3:6]}/{r['key']}.jpg" if r.get("key") else None,
                         "text": text[:300], "m": hit})
        out.add_file(name, rows, read, extra)

    run_files(names, work, out, workers, "YFCC (OpenAI subset)")


SI = "https://smithsonian-open-access.s3-us-west-2.amazonaws.com"
SI_UNITS = ["nmah", "nmai", "nmnhanthro", "chndm", "npm"]


def si_text(rec: dict) -> str:
    c = rec.get("content", {})
    parts = [rec.get("title") or ""]
    ft = c.get("freetext", {})
    for key in ("objectType", "name", "topic", "setName", "physicalDescription"):
        parts += [x.get("content", "") for x in ft.get(key, [])]
    ist = c.get("indexedStructured", {})
    for key in ("object_type", "topic"):
        parts += [x if isinstance(x, str) else "" for x in ist.get(key, [])]
    parts += [x.get("content", "")[:400] for x in ft.get("notes", [])[:2]]
    return " | ".join(p for p in parts if p)


def si_images(rec: dict):
    media = rec.get("content", {}).get("descriptiveNonRepeating", {}).get("online_media", {}).get("media", [])
    return [{"ids": x.get("idsId"), "url": x.get("content"), "res": [(r.get("label"), r.get("width"), r.get("height"))
                                                                    for r in x.get("resources", [])][:4]}
            for x in media if x.get("type") == "Images" and (x.get("usage") or {}).get("access") == "CC0"]


def scan_smithsonian(out: Out, workers: int, m: Matcher):
    names = []
    for u in SI_UNITS:
        lst = fetch(f"{SI}/?list-type=2&prefix=metadata/edan/{u}/").decode("utf-8")
        names += re.findall(r"<Key>([^<]+\.txt)</Key>", lst)

    def work(name):
        rows, read, extra = [], Counter(), Counter()
        for line in fetch(f"{SI}/{name}").decode("utf-8").split("\n"):  # not splitlines(): U+2028 in text
            if not line.strip():
                continue
            rec = json.loads(line)
            read["rows"] += 1
            hit = m.match(si_text(rec))
            if not hit:
                continue
            imgs = si_images(rec)
            if not imgs:
                extra["matched_no_cc0_image"] += 1
                continue
            rows.append({"id": rec.get("id"), "unit": rec.get("unitCode"), "licence": "CC0",
                         "page": rec.get("content", {}).get("descriptiveNonRepeating", {}).get("record_link"),
                         "images": imgs[:3], "n_images": len(imgs), "text": si_text(rec)[:300], "m": hit})
        out.add_file(name, rows, read, extra)

    run_files(names, work, out, workers, "Smithsonian")


def scan_commoncatalog(out: Out, workers: int, m: Matcher, sample: int):
    from hf_range import read_columns
    repo = "common-canvas/commoncatalog-cc-by"
    every = hf_files(repo, "", ".parquet")
    names = sorted(random.Random(7).sample(every, sample))
    out.extra["files_in_dataset"] = len(every)
    cols = ["photoid", "title", "usertags", "description", "licensename", "key", "pageurl", "unickname",
            "width", "height"]

    def work(name):
        rows, read = [], Counter()
        # only the text columns' bytes, straight from the CDN (hf_range.py):
        # about 2 MB a file instead of 3 GB, one rate-limited call a file
        t, _ = read_columns(repo, name, cols)
        for k, r in enumerate(t.to_pylist()):
            read["rows"] += 1
            tags = urllib.parse.unquote_plus(r.get("usertags") or "")
            text = " | ".join([urllib.parse.unquote_plus(r.get("title") or ""),
                               urllib.parse.unquote_plus(r.get("description") or "")[:600], tags.replace(",", " , ")])
            hit = m.match(text)
            if hit:
                # the image is only inside the parquet: file and row say where
                rows.append({"id": r["photoid"], "file": name, "row": k, "licence": r.get("licensename"),
                             "author": r.get("unickname"),
                             "page": r.get("pageurl"), "key": r.get("key"), "w": r.get("width"),
                             "h": r.get("height"), "text": text[:300], "m": hit})
        out.add_file(name, rows, read)

    run_files(names, work, out, workers, f"CommonCatalog CC-BY (sample of {sample} of {len(every)} files)")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("source", choices=["pd12m", "yfcc", "smithsonian", "commoncatalog"])
    ap.add_argument("out_dir")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--sample", type=int, default=50)
    a = ap.parse_args()
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    m = Matcher()
    out = Out(out_dir, a.source)
    if a.source == "pd12m":
        scan_pd12m(out, a.workers, m)
    elif a.source == "yfcc":
        scan_yfcc(out, a.workers, m)
    elif a.source == "smithsonian":
        scan_smithsonian(out, a.workers, m)
    else:
        scan_commoncatalog(out, a.workers, m, a.sample)
    out.save()
    print("done:", out.matched, "matches", flush=True)


if __name__ == "__main__":
    main()
