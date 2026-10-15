"""Read TPWD's lake pages and survey reports (as saved by tpwd_fetch.py).

Pure functions from HTML to data: no network, no database. What the
statewide import does with the result is in tpwd_statewide_import.py.

Two kinds of page per lake, both by TPWD's Inland Fisheries Division:

- The lake page (/fishboat/fish/recreational/lakes/<slug>/): location,
  surface area, the "Predominant Fish Species" list, TPWD's own
  poor / fair / good / excellent rating of the fishing for each species
  group, and a link to the latest survey report.
- The survey report summary (/publications/pwdpubs/lake_survey/<id>/):
  the biologists' prose, which names the species they sampled.

Species are only ever matched against the hand-curated aliases in
tpwd_lake_survey_scraper.KNOWN_SPECIES, and each match keeps the exact text
it came from as evidence. A generic word ("Crappie", "Catfish") names no
particular species and matches nothing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

from app.data_import.tpwd_lake_survey_scraper import (
    _SENTENCE_SPLIT_RE,
    KNOWN_SPECIES,
    SpeciesMention,
    species_in_sentence,
)

BASE = "https://tpwd.texas.gov"
RATING_LEVELS = ("Poor", "Fair", "Good", "Excellent")

# alias -> canonical name, for whole-phrase lookups
_ALIAS_TO_SPECIES: dict[str, str] = {
    alias: canonical for canonical, aliases in KNOWN_SPECIES.items() for alias in aliases
}
_SPACE = re.compile(r"\s+")
_PARENS = re.compile(r"\([^)]*\)")
_JOINERS = re.compile(r"\s*(?:,|&|/|\band\b)\s*", re.IGNORECASE)


def _clean(text: str) -> str:
    return _SPACE.sub(" ", text).strip()


def species_in_phrase(phrase: str) -> list[str]:
    """The guide species a list item such as TPWD's "Channel, blue & flathead
    catfish" or "White & hybrid striped bass" names, in order.

    The shared noun at the end ("catfish", "striped bass") is distributed
    over the modifiers before it, and a candidate counts only if it is
    exactly one of the curated aliases: "white" + "bass" is White Bass,
    "hybrid" + "striped bass" is Hybrid Striped Bass, and "white" +
    "striped bass" (not an alias) is nothing.
    """
    text = _clean(_PARENS.sub(" ", phrase)).lower().rstrip(" .")
    parts = [p for p in _JOINERS.split(text) if p]
    if not parts:
        return []
    last_words = parts[-1].split()
    suffixes = [" ".join(last_words[i:]) for i in range(1, len(last_words))]
    found: list[str] = []

    def add(candidate: str) -> None:
        name = _ALIAS_TO_SPECIES.get(candidate)
        if name and name not in found:
            found.append(name)

    for part in parts:
        add(part)
        if part is not parts[-1]:
            for suffix in suffixes:
                add(f"{part} {suffix}")
    return found


@dataclass(frozen=True)
class Rating:
    label: str  # TPWD's own species-group label, e.g. "White & Hybrid Striped Bass"
    rating: str  # one of RATING_LEVELS


@dataclass
class LakePage:
    slug: str
    name: str
    url: str
    access_url: str
    report_id: str | None
    wb_code: str | None
    location: str | None
    surface_acres: int | None
    max_depth_ft: int | None
    impounded: str | None
    predominant: list[str] = field(default_factory=list)  # list items, as TPWD wrote them
    ratings: list[Rating] = field(default_factory=list)

    @property
    def species(self) -> dict[str, str]:
        """Guide species named in the predominant-species list -> the list
        item that named it."""
        named: dict[str, str] = {}
        for item in self.predominant:
            for name in species_in_phrase(item):
                named.setdefault(name, item)
        return named


def _main(soup: BeautifulSoup) -> Tag:
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.find("main") or soup.body or soup


def _number(pattern: str, text: str) -> int | None:
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _section_list(main: Tag, heading: str) -> list[str]:
    for h in main.find_all("h6"):
        if heading.lower() in h.get_text(" ", strip=True).lower():
            sibling = h.find_next_sibling()
            if sibling is not None and sibling.name == "ul":
                return [_clean(li.get_text(" ", strip=True)).rstrip(" .") for li in sibling.find_all("li")]
            return []
    return []


def _ratings(soup: BeautifulSoup) -> list[Rating]:
    table = soup.find("table", id="Ratings")
    if table is None:
        return []
    levels: list[str] = []
    out: list[Rating] = []
    for row in table.find_all("tr"):
        heads = row.find_all("th")
        cells = row.find_all("td")
        if heads and not cells:
            levels = [_clean(h.get_text(" ", strip=True)).title() for h in heads[1:]]
            continue
        if not heads or not cells:
            continue
        label = _clean(heads[0].get_text(" ", strip=True))
        marked = [i for i, td in enumerate(cells) if td.find("img") or _clean(td.get_text()).strip("\xa0 ")]
        if len(marked) != 1 or marked[0] >= len(levels):
            continue  # unrated, or ambiguous: say nothing rather than guess
        level = levels[marked[0]]
        if level in RATING_LEVELS:
            out.append(Rating(label, level))
    return out


def parse_lake_page(html: str, slug: str) -> LakePage:
    soup = BeautifulSoup(html, "html.parser")
    title = _clean(soup.title.get_text(" ", strip=True)) if soup.title else slug
    name = re.sub(r"^Fishing\s+", "", title)
    report = re.search(r"/lake_survey/(pwd_rp_t3200_\d+)", html)
    wb_code = re.search(r"WB_code=(\d+)", html)
    ratings = _ratings(soup)
    main = _main(soup)
    text = _clean(main.get_text(" ", strip=True))
    location = re.search(r"Location:\s*(.+?)(?=\s+Surface area:|\s+Maximum depth:|\s+Impounded:|$)", text)
    impounded = re.search(r"Impounded:\s*([0-9]{4}(?:\s*[-/]\s*[0-9]{2,4})?)", text)
    root = f"{BASE}/fishboat/fish/recreational/lakes/{slug}/"
    return LakePage(
        slug=slug,
        name=name,
        url=root,
        access_url=root + "access.phtml",
        report_id=report.group(1) if report else None,
        wb_code=wb_code.group(1) if wb_code else None,
        location=location.group(1).strip() if location else None,
        surface_acres=_number(r"Surface area:\s*([\d,]+)", text),
        max_depth_ft=_number(r"Maximum depth:\s*([\d,]+)", text),
        impounded=impounded.group(1) if impounded else None,
        predominant=_section_list(main, "Predominant Fish Species"),
        ratings=ratings,
    )


# A sentence that names a fish is not always saying the fish is there: "No
# White Crappie were collected", "Hybrid Striped Bass stocking was
# discontinued", "the regulation for Blue and Channel Catfish was modified".
# Any sentence with one of these words is not used as evidence of presence.
# Deliberately blunt: it also drops some sentences that do show presence
# ("Spotted Bass were more abundant ... due to the lack of vegetation"). A
# missed species costs less than a fish that isn't there.
_NOT_PRESENCE = re.compile(
    r"\b(?:no|not|none|never|absent|lack\w*|without|n't"
    r"|discontinu\w*|eliminat\w*|eradicat\w*|extirpat\w*|fail\w*|unsuccessful"
    # "length limit", not "present in limited numbers"
    r"|stock\w*|regulation\w*|(?:length|slot|bag|daily) limits?|bag)\b",
    re.IGNORECASE,
)


def survey_mentions(text: str) -> list[SpeciesMention]:
    """Species the text says are present, each with the first sentence that
    says so (see _NOT_PRESENCE for what doesn't count)."""
    found: dict[str, SpeciesMention] = {}
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        if _NOT_PRESENCE.search(sentence):
            continue
        for name in species_in_sentence(sentence.lower()):
            found.setdefault(name, SpeciesMention(name, sentence.strip()))
    return list(found.values())


@dataclass
class ReportPage:
    report_id: str
    url: str
    lake_name: str
    year: int | None
    mentions: list[SpeciesMention]  # presence only: see survey_mentions


def parse_report_page(html: str, report_id: str) -> ReportPage:
    """The summary's own text only: from its title to the end of the
    article, not the sidebar (which lists other years and other lakes)."""
    soup = BeautifulSoup(html, "html.parser")
    main = _main(soup)
    h1 = main.find("h1")
    heading = _clean(h1.get_text(" ", strip=True)) if h1 else ""
    m = re.match(r"(.+?)\s*-\s*(\d{4})\s+Survey Report", heading)
    lake_name = _clean(m.group(1)) if m else heading
    year = int(m.group(2)) if m else None
    body: list[str] = []
    if h1 is not None:
        for el in h1.find_all_next(["p", "li", "h3"]):
            words = el.get_text(" ", strip=True)
            # A heading ends its own "sentence", so it isn't glued onto the
            # evidence quoted from the paragraph after it.
            body.append(f"{words}." if el.name == "h3" else words)
    text = _clean(" ".join(body))
    return ReportPage(
        report_id=report_id,
        url=f"{BASE}/publications/pwdpubs/lake_survey/{report_id}/",
        lake_name=lake_name,
        year=year,
        mentions=survey_mentions(text),
    )
