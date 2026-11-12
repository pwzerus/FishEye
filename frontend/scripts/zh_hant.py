"""Traditional Chinese (Taiwan) for the site's own words, made from the Simplified.

The Simplified Chinese is the one written by hand; this turns it into
Traditional characters and Taiwan's usual words (OpenCC "s2twp", Apache-2.0),
then puts back the few words that rule gets wrong on a fishing site (FIXES).

Run from frontend/ after changing zh.ts, a zh table in names.ts or weather.ts,
or a zh name in the /start kit list:

    ../backend/.venv/Scripts/python scripts/zh_hant.py           # write the files
    ../backend/.venv/Scripts/python scripts/zh_hant.py --review  # list the word swaps

It writes src/i18n/zht.ts and, next to every `zh:` entry in names.ts,
weather.ts and FirstTrip.tsx, a `zht:` entry (replacing the last run's).
The backend turns its own Chinese the same way (app/knowledge/zh_hant.py).
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

import opencc

SRC = Path(__file__).resolve().parents[1] / "src"
_S2TWP = opencc.OpenCC("s2twp")
_S2T = opencc.OpenCC("s2t")

# Where the Taiwan rule picks a word this site doesn't mean (checked with
# --review, 2026-11-11). Applied in order, after the conversion.
FIXES: dict[str, str] = {
    "釋出": "發布",  # 发布: post a catch or a comment, not release software
    "稽核": "審核",  # 审核: moderators review a report; 稽核 is an audit
    "許可權": "權限",  # 定位权限: the location permission, as phones say it
    "區域性": "局部",  # 局部多云: forecasts in Taiwan say 局部 too
    "賬": "帳",  # 账户, 账号: 帳戶, 帳號 in Taiwan
    "隻能": "只能",  # 最多只能: "can only", read as the measure word 隻
    "隻有": "只有",
    # Mainland words Taiwan says otherwise, the rule keeps.
    "郵箱": "電子郵件",
    "反饋": "意見回饋",
    "浮漂": "浮標",  # what anglers in Taiwan call a bobber
    "漁輪": "捲線器",  # and a reel
    "得克薩斯": "德克薩斯",  # Texas, as Taiwan writes it; the other states come out right
    # The home-screen tip: the menus' own words on a phone set to Taiwan.
    "新增到主螢幕": "加入主畫面",
    "安裝應用”": "安裝應用程式”",
    "安卓": "Android",
    # Taiwan's quotation marks (after the fixes above, which match “”).
    "“": "「",
    "”": "」",
}


def zht(text: str) -> str:
    out = _S2TWP.convert(text)
    for wrong, right in FIXES.items():
        out = out.replace(wrong, right)
    return out


def zh_entries(lines: list[str]) -> list[tuple[int, int]]:
    """(first, last) line index of each two-space-indented `zh:` entry: a
    one-line value, or a `{` block closed by `  },` at the same indent."""
    found = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("  zh: "):
            if line.rstrip().endswith("{"):
                j = i + 1
                while not lines[j].startswith("  },"):
                    j += 1
                found.append((i, j))
                i = j + 1
                continue
            found.append((i, i))
        i += 1
    return found


def with_zht_tables(text: str) -> str:
    """names.ts / weather.ts with a `zht:` entry after each `zh:` one."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    entries = dict(zh_entries(lines))
    while i < len(lines):
        if i in entries:
            end = entries[i]
            block = lines[i : end + 1]
            out.extend(block)
            # Drop the previous run's zht entry, which follows directly.
            k = end + 1
            if k < len(lines) and lines[k].startswith("  zht: "):
                if lines[k].rstrip().endswith("{"):
                    while not lines[k].startswith("  },"):
                        k += 1
                k += 1
            converted = zht("\n".join(block)).split("\n")
            converted[0] = "  zht: " + converted[0][len("  zh: ") :]
            out.extend(converted)
            i = k
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


KIT_FIELD = re.compile(r'zh: "([^"]*)",(?: zht: "[^"]*",)?')


def with_zht_kit(text: str) -> str:
    return KIT_FIELD.sub(lambda m: f'zh: "{m.group(1)}", zht: "{zht(m.group(1))}",', text)


def messages(text: str) -> str:
    body = zht(text)
    body = body.replace("const zh: Messages", "const zht: Messages", 1)
    body = body.replace("export default zh;", "export default zht;", 1)
    header = (
        "// 由 zh.ts 自動產生（frontend/scripts/zh_hant.py，OpenCC s2twp）。\n"
        "// Generated from zh.ts by scripts/zh_hant.py: edit zh.ts and run it again, not this file.\n"
    )
    return header + body


def review(paths: list[Path]) -> None:
    """Each word the Taiwan rule swaps, beyond turning characters
    Traditional, once, with where it first shows up."""
    seen: dict[tuple[str, str], str] = {}
    for path in paths:
        for line in path.read_text(encoding="utf-8").split("\n"):
            plain, taiwan = _S2T.convert(line), zht(line)
            if plain == taiwan:
                continue
            m = difflib.SequenceMatcher(a=plain, b=taiwan, autojunk=False)
            for op, a0, a1, b0, b1 in m.get_opcodes():
                if op != "equal":
                    key = (plain[max(0, a0 - 1) : a1 + 1], taiwan[max(0, b0 - 1) : b1 + 1])
                    seen.setdefault(key, f"{path.name}: {line.strip()[:60]}")
    for (a, b), where in sorted(seen.items()):
        print(f"{a} -> {b}    ({where})")
    print(len(seen), "swaps")


def main() -> None:
    i18n = SRC / "i18n"
    kit = SRC / "components" / "start" / "FirstTrip.tsx"
    sources = [i18n / "zh.ts", i18n / "names.ts", i18n / "weather.ts", kit]
    if "--review" in sys.argv:
        review(sources)
        return
    (i18n / "zht.ts").write_text(messages((i18n / "zh.ts").read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    for name in ("names.ts", "weather.ts"):
        path = i18n / name
        path.write_text(with_zht_tables(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    kit.write_text(with_zht_kit(kit.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    print("wrote zht.ts, names.ts, weather.ts and FirstTrip.tsx")


if __name__ == "__main__":
    main()
