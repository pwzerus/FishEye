"""Read one photo out of a CommonCatalog parquet file without the rest.

common-canvas/commoncatalog-cc-by keeps every photo's JPEG inside its
parquet files (2-3 GB each, about 130 MB of images per row group). The
files carry an offset index (where each page of a column starts and which
row it begins with), which pyarrow doesn't expose; this reads the footer's
Thrift itself, finds the page that holds the row, and fetches only that
page (about one photo, ~1 MB).

    img = CCReader().image(file_name, row)   # JPEG bytes
"""
import struct
import threading

from hf_range import RangeFile

REPO = "common-canvas/commoncatalog-cc-by"


class Compact:
    """Just enough of Thrift's compact protocol to walk Parquet metadata."""

    def __init__(self, buf: bytes, pos: int = 0):
        self.b, self.p = buf, pos

    def byte(self):
        v = self.b[self.p]
        self.p += 1
        return v

    def varint(self):
        shift = result = 0
        while True:
            x = self.byte()
            result |= (x & 0x7F) << shift
            if not x & 0x80:
                return result
            shift += 7

    def zigzag(self):
        n = self.varint()
        return (n >> 1) ^ -(n & 1)

    def value(self, t):
        if t == 1:
            return True
        if t == 2:
            return False
        if t == 3:
            v = struct.unpack_from("b", self.b, self.p)[0]
            self.p += 1
            return v
        if t in (4, 5, 6):
            return self.zigzag()
        if t == 7:
            v = struct.unpack_from("<d", self.b, self.p)[0]
            self.p += 8
            return v
        if t == 8:
            n = self.varint()
            v = self.b[self.p:self.p + n]
            self.p += n
            return v
        if t in (9, 10):
            h = self.byte()
            size, et = h >> 4, h & 0x0F
            if size == 15:
                size = self.varint()
            return [self.value(et) if et not in (1, 2) else bool(self.byte() == 1) for _ in range(size)]
        if t == 11:
            size = self.varint()
            if not size:
                return {}
            kv = self.byte()
            return {self.value(kv >> 4): self.value(kv & 0x0F) for _ in range(size)}
        if t == 12:
            return self.struct()
        raise ValueError(f"thrift type {t}")

    def struct(self):
        out, last = {}, 0
        while True:
            h = self.byte()
            if h == 0:
                return out
            delta, t = h >> 4, h & 0x0F
            fid = last + delta if delta else self.zigzag()
            out[fid] = self.value(t)
            last = fid


def rle_bitpacked(buf: bytes, bit_width: int, count: int):
    """Definition levels (RLE / bit-packed hybrid)."""
    out, p = [], 0
    width = (bit_width + 7) // 8
    while len(out) < count and p < len(buf):
        c = Compact(buf, p)
        h = c.varint()
        p = c.p
        if h & 1:
            groups = h >> 1
            nbytes = groups * bit_width
            bits = int.from_bytes(buf[p:p + nbytes], "little")
            for i in range(groups * 8):
                out.append((bits >> (i * bit_width)) & ((1 << bit_width) - 1))
            p += nbytes
        else:
            v = int.from_bytes(buf[p:p + width], "little")
            p += width
            out += [v] * (h >> 1)
    return out[:count]


class CCReader:
    def __init__(self):
        self.meta = {}
        self.lock = threading.Lock()

    def _read(self, name, start, length):
        return RangeFile(REPO, name)._fetch(start, length)

    def _layout(self, name):
        """Per row group: first row, and the jpg column's page locations."""
        with self.lock:
            if name in self.meta:
                return self.meta[name]
        size = RangeFile(REPO, name).size
        tail = self._read(name, size - 8, 8)
        flen = struct.unpack("<I", tail[:4])[0]
        fmd = Compact(self._read(name, size - 8 - flen, flen)).struct()
        schema = fmd[2]
        leaves = [el[4].decode() for el in schema[1:] if 5 not in el]  # elements without children
        col = leaves.index("jpg")
        groups, first = [], 0
        for rg in fmd[4]:
            cc = rg[1][col]
            oi = Compact(self._read(name, cc[4], cc[5])).struct()
            pages = [(pl[1], pl[2], pl[3]) for pl in oi[1]]  # offset, size incl. header, first row
            groups.append({"first": first, "rows": rg[3], "pages": pages})
            first += rg[3]
        with self.lock:
            self.meta[name] = groups
        return groups

    def image(self, name: str, row: int) -> bytes:
        """A page holds ~70 photos (~65 MB), so it isn't read whole: the
        header and definition levels come from its first 64 KB, then the
        4-byte length in front of each earlier photo is read to step over
        it, and only the wanted photo's bytes are fetched."""
        for g in self._layout(name):
            if g["first"] <= row < g["first"] + g["rows"]:
                break
        else:
            raise IndexError(row)
        r = row - g["first"]
        k = max(i for i, p in enumerate(g["pages"]) if p[2] <= r)
        off, size, first_row = g["pages"][k]
        with RangeFile(REPO, name) as fh:
            fh.seek(off)
            head = fh.read(min(size, 2**16))
            c = Compact(head)
            hdr = c.struct()
            body_at = c.p
            if 5 in hdr:  # data page v1: [4-byte length][definition levels][values]
                n = hdr[5][1]
                dl_len = struct.unpack_from("<I", head, body_at)[0]
                levels = rle_bitpacked(head[body_at + 4:body_at + 4 + dl_len], 1, n)
                vals_at = off + body_at + 4 + dl_len
            elif 8 in hdr:  # data page v2: the levels' lengths are in the header
                n = hdr[8][1]
                dl_len, rl_len = hdr[8][5], hdr[8][6]
                levels = rle_bitpacked(head[body_at + rl_len:body_at + rl_len + dl_len], 1, n)
                vals_at = off + body_at + rl_len + dl_len
            else:
                raise ValueError("not a data page")
            want = r - first_row
            if levels[want] == 0:
                raise ValueError("no image in this row")
            p = vals_at
            for i in range(want):
                if levels[i]:
                    fh.seek(p)
                    p += 4 + struct.unpack("<I", fh.read(4))[0]
            fh.seek(p)
            ln = struct.unpack("<I", fh.read(4))[0]
            return fh.read(ln)
