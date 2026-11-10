"""The site's long text in other languages: the gear list, the fish guides and the handbook.

English stays the source (gear.py, species_guides.py, angling_handbook.py). A table is one language's
version of one of them, `<lang>_<name>.json`, keyed by where the text sits: `bait-worms#2` is the third
sentence of that handbook topic, `bluegill.setups#1.rod` a guide's second setup's rod. A string with no
translation stays English, and the API says so (`text_lang` / `body_lang` is left empty), so the page
can say the text is in English for now.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).parent
# Only these reach the file system: `lang` comes from the URL.
LANGUAGES = ("zh",)


@lru_cache(maxsize=None)
def table(name: str, lang: str) -> dict[str, str]:
    if lang not in LANGUAGES:
        return {}
    path = HERE / f"{lang}_{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


class Translator:
    """Looks up each string of one record, and remembers whether any was missing."""

    def __init__(self, name: str, lang: str, prefix: str = "") -> None:
        self.entries = table(name, lang)
        self.lang = lang
        self.prefix = prefix
        self.complete = True

    def text(self, key: str, english: str) -> str:
        found = self.entries.get(self.prefix + key)
        if found is None:
            self.complete = False
            return english
        return found

    def many(self, key: str, english: list[str] | tuple[str, ...]) -> list[str]:
        return [self.text(f"{key}#{i}", s) for i, s in enumerate(english)]

    @property
    def language(self) -> str | None:
        """The language of the record's text, or None if any of it stayed English."""
        return self.lang if self.entries and self.complete else None
