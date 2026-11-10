"""A seekable file over HTTP range requests to a Hugging Face dataset file.

Hugging Face lets an anonymous client make 3,000 "resolve" calls in five
minutes, and huggingface_hub's HfFileSystem spends one on every range read
(about 70 for reading a few columns of one parquet file), so a scan of
thousands of files stalls on "Rate limited". This resolves each file once
(its 302 points to a signed CDN address, valid for a while) and sends the
range reads to the CDN, which the limit doesn't count.

    with open_hf("common-canvas/commoncatalog-cc-by", path) as f:
        pq.ParquetFile(f, pre_buffer=True).read(columns=[...])
"""
import io
import threading
import time

import requests

UA = "FishEye-dataset-scan/1.0 (feedback.fisheyefishing@gmail.com)"
_local = threading.local()
_cache: dict[str, tuple[str, int, float]] = {}
_lock = threading.Lock()


def _session():
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
        _local.s.headers["User-Agent"] = UA
    return _local.s


def resolve(repo: str, path: str, fresh: bool = False):
    """(CDN url, size) for a dataset file; cached for 30 minutes."""
    key = f"{repo}/{path}"
    with _lock:
        hit = _cache.get(key)
    if hit and not fresh and time.time() - hit[2] < 1800:
        return hit[0], hit[1]
    url = f"https://huggingface.co/datasets/{repo}/resolve/main/{path}"
    for attempt in range(8):
        r = _session().head(url, allow_redirects=False, timeout=60)
        if r.status_code == 429:
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        loc, size = r.headers["Location"], int(r.headers["X-Linked-Size"])
        with _lock:
            _cache[key] = (loc, size, time.time())
        return loc, size
    raise RuntimeError(f"rate limited resolving {path}")


class RangeFile(io.RawIOBase):
    def __init__(self, repo: str, path: str):
        self.repo, self.path = repo, path
        self.url, self.size = resolve(repo, path)
        self.pos = 0
        self.bytes_read = 0
        self.blocks: list[tuple[int, bytes]] = []  # prefetched (start, data)

    def prefetch(self, ranges, workers=8):
        """Fetch (start, end) byte ranges at once; reads inside them are then
        served from memory."""
        import concurrent.futures as cf

        def get(r):
            a, b = r
            f = RangeFile.__new__(RangeFile)
            f.repo, f.path, f.url, f.size, f.pos, f.bytes_read, f.blocks = (
                self.repo, self.path, self.url, self.size, a, 0, [])
            return a, f._fetch(a, b - a)

        with cf.ThreadPoolExecutor(workers) as ex:
            for a, data in ex.map(get, ranges):
                self.blocks.append((a, data))
                self.bytes_read += len(data)

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        return self.pos

    def _fetch(self, start, n):
        for attempt in range(6):
            try:
                r = _session().get(self.url, headers={"Range": f"bytes={start}-{start + n - 1}"}, timeout=120)
                if r.status_code in (401, 403):  # the signed address ran out: resolve again
                    self.url, _ = resolve(self.repo, self.path, fresh=True)
                    continue
                r.raise_for_status()
                return r.content
            except requests.RequestException:
                if attempt == 5:
                    raise
                time.sleep(3 * (attempt + 1))
        raise RuntimeError("range read failed")

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        for a, data in self.blocks:
            if a <= self.pos and self.pos + n <= a + len(data):
                out = data[self.pos - a:self.pos - a + n]
                self.pos += n
                return out
        data = self._fetch(self.pos, n)
        self.pos += len(data)
        self.bytes_read += len(data)
        return data

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def open_hf(repo: str, path: str) -> RangeFile:
    return RangeFile(repo, path)


def read_columns(repo: str, path: str, columns: list[str], workers: int = 8):
    """A parquet file's columns, fetching only their bytes, all at once:
    the footer first (2 reads), then each row group's span of the wanted
    columns (runs of adjacent columns become one range)."""
    import pyarrow.parquet as pq

    f = RangeFile(repo, path)
    tail = f._fetch(f.size - 8, 8)
    flen = int.from_bytes(tail[:4], "little")
    footer_at = f.size - 8 - flen
    f.blocks.append((footer_at, f._fetch(footer_at, flen + 8)))
    md = pq.ParquetFile(f).metadata
    names = [md.row_group(0).column(j).path_in_schema for j in range(md.num_columns)]
    want = [j for j, n in enumerate(names) if n in columns]
    ranges = []
    for i in range(md.num_row_groups):
        rg = md.row_group(i)
        spans = []
        for j in want:
            c = rg.column(j)
            start = c.dictionary_page_offset if c.has_dictionary_page and c.dictionary_page_offset else c.data_page_offset
            spans.append((start, start + c.total_compressed_size))
        spans.sort()
        merged = [list(spans[0])]
        for a, b in spans[1:]:
            if a - merged[-1][1] < 256 * 1024:  # a small gap: one read
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        ranges += [tuple(m) for m in merged]
    f.prefetch(ranges, workers)
    f.seek(0)
    table = pq.ParquetFile(f, pre_buffer=False).read(columns=columns)
    return table, f.bytes_read
