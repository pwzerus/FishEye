"""Which real English words would Ask's spelling fix change? Run after editing _TARGETS.

From backend/:  .venv/Scripts/python tools/spelling/real_words.py [en.utf-8.spl]

The dictionary is Vim's English spell file, which comes with Git for Windows; the
format is in Vim's spellfile.c. Whatever this prints, apart from the deliberate
_SHORT words, goes in spelling._REAL_WORDS.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.setrecursionlimit(10000)
from app.services.rag import spelling  # noqa: E402

DEFAULT = "C:/Program Files/Git/usr/share/vim/vim91/spell/en.utf-8.spl"
BY_NOFLAGS, BY_INDEX, BY_FLAGS2 = 0, 1, 3
WF_REGION, WF_BANNED, WF_AFX = 0x01, 0x10, 0x20


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 9  # "VIMspell" and a version byte
        while self.byte() != 255:  # the sections before the word trees
            self.pos += 1  # the section's flags
            self.pos += 4 + int.from_bytes(self.data[self.pos:self.pos + 4], "big")

    def byte(self) -> int:
        self.pos += 1
        return self.data[self.pos - 1]

    def words(self) -> list[bytes]:
        """One word tree: the case-folded one comes first, the keep-case one after it."""
        size = int.from_bytes(self.data[self.pos:self.pos + 4], "big")
        self.pos += 4
        if not size:
            return []
        self.bytes_at, self.index = [0] * size, [0] * size
        self.node(0)
        found: list[bytes] = []
        self.walk(0, [], found)
        return found

    def node(self, start: int) -> int:
        count = self.byte()
        self.bytes_at[start] = count
        at = start + 1
        for _ in range(count):
            c = self.byte()
            if c == BY_NOFLAGS:
                self.index[at] = 0
            elif c == BY_INDEX:
                self.index[at] = -int.from_bytes(self.data[self.pos:self.pos + 3], "big") - 1
                self.pos += 3
                c = self.byte()
            elif c <= BY_FLAGS2:
                flags = self.byte()
                if c == BY_FLAGS2:
                    flags |= self.byte() << 8
                self.pos += bool(flags & WF_REGION) + bool(flags & WF_AFX)
                self.index[at] = flags
                c = 0
            self.bytes_at[at] = c
            at += 1
        for i in range(1, count + 1):
            if self.bytes_at[start + i]:
                if self.index[start + i] < 0:
                    self.index[start + i] = -self.index[start + i] - 1
                else:
                    self.index[start + i] = at
                    at = self.node(at)
        return at

    def walk(self, at: int, prefix: list[int], found: list[bytes]) -> None:
        for i in range(1, self.bytes_at[at] + 1):
            b = self.bytes_at[at + i]
            if b:
                self.walk(self.index[at + i], [*prefix, b], found)
            elif not self.index[at + i] & WF_BANNED:
                found.append(bytes(prefix))


def main() -> None:
    reader = Reader(Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT).read_bytes())
    found = {w.decode("utf-8", "ignore").lower() for _ in range(2) for w in reader.words()}
    words = sorted(w for w in found if w.isascii() and w.isalpha())
    changed = {w: spelling.fix(w) for w in words if spelling.fix(w) != w}
    print(f"{len(words)} words, {len(changed)} changed")
    print(" ".join(f"{a}>{b}" for a, b in changed.items()))


if __name__ == "__main__":
    main()
