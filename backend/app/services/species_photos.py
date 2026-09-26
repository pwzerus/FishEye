"""A real photo of each guide species, from Wikipedia / Wikimedia Commons.

The fish guide pairs an illustration (drawn in the frontend) with a real
photograph, because a beginner holding a fish needs to match it against
what the fish actually looks like, not a cartoon of it.

Where the photos come from, and why at runtime
----------------------------------------------
Each species' Wikipedia article has a lead image. With `pilicense=free`,
Wikipedia only returns lead images that are freely licensed, and
Commons' `extmetadata` then gives the author and licence, which the UI
shows under every photo — attribution is what CC BY / BY-SA require, not a
courtesy. Two batched API calls cover all species (titles are pipe-joined),
so a cold cache costs two requests, not two per fish.

Nothing is downloaded into the repo: no licence review to redo when an
article's image changes, and no binary files in git.

Same reliability shape as the other adapters (timeout, one retry, circuit
breaker, cache), and the same honesty rule as geocoding.py: when Wikipedia
can't be reached there is no placeholder photo. The species simply has
`photo: null`, and the UI shows the illustration alone.
"""
from __future__ import annotations

import html
import re
import threading
import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

API_URL = "https://en.wikipedia.org/w/api.php"
REQUEST_TIMEOUT_SECONDS = 6.0
RETRY_DELAY_SECONDS = 0.5
THUMB_WIDTH = 960
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # lead images change rarely
NO_PHOTO_TTL_SECONDS = 24 * 60 * 60  # "article has no free image" is re-checked daily
CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_COOLDOWN_SECONDS = 5 * 60

# slug -> Wikipedia article. Redirects are followed, so the common name is enough.
WIKIPEDIA_TITLES: dict[str, str] = {
    "largemouth-bass": "Largemouth bass",
    "spotted-bass": "Spotted bass",
    "white-bass": "White bass",
    "striped-bass": "Striped bass",
    "hybrid-striped-bass": "Hybrid striped bass",
    "channel-catfish": "Channel catfish",
    "blue-catfish": "Blue catfish",
    "white-crappie": "White crappie",
    "black-crappie": "Black crappie",
    "bluegill": "Bluegill",
    "gizzard-shad": "Gizzard shad",
    "threadfin-shad": "Threadfin shad",
}

_FREE_LICENSE_RE = re.compile(
    r"^(cc0|public domain|pd\b.*|cc[ -]by([ -]sa)?([ -][\d.]+)?)", re.IGNORECASE
)


@dataclass(frozen=True)
class SpeciesPhoto:
    url: str  # a Wikimedia thumbnail, THUMB_WIDTH wide
    width: int
    height: int
    author: str  # plain text
    license: str  # "CC BY-SA 3.0", "Public domain", ...
    license_url: str | None
    file_page: str  # the Commons/Wikipedia file page: full credit and licence
    source: str = "wikimedia"


class _CircuitBreaker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at: float | None = None

    def is_open(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return False
            if time.monotonic() - self._opened_at >= CIRCUIT_COOLDOWN_SECONDS:
                self._opened_at, self._failures = None, 0
                return False
            return True

    def record(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self._failures, self._opened_at = 0, None
                return
            self._failures += 1
            if self._failures >= CIRCUIT_FAILURE_THRESHOLD:
                self._opened_at = time.monotonic()


_circuit = _CircuitBreaker()
_cache: dict[str, tuple[float, SpeciesPhoto | None]] = {}
_lock = threading.Lock()


def reset_state() -> None:
    global _circuit
    with _lock:
        _cache.clear()
    _circuit = _CircuitBreaker()


def _get(params: dict[str, str]) -> dict:
    headers = {"User-Agent": get_settings().wikimedia_user_agent}
    last: Exception | None = None
    for attempt in range(2):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
                resp = client.get(API_URL, params={**params, "format": "json", "formatversion": "2"})
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            last = exc
            if attempt == 0:
                time.sleep(RETRY_DELAY_SECONDS)
    assert last is not None
    raise last


def _plain(value: str | None) -> str:
    """Commons' Artist field is HTML (often a user-page link)."""
    text = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(html.unescape(text).split())


def _file_key(name: str) -> str:
    name = name.removeprefix("File:").replace("_", " ")
    return name[:1].upper() + name[1:]


def _resolve_titles(query: dict) -> dict[str, str]:
    """requested title -> final page title, through normalisation and redirects."""
    mapping: dict[str, str] = {}
    for step in ("normalized", "redirects"):
        for entry in query.get(step, []):
            mapping[entry["from"]] = entry["to"]

    def follow(title: str) -> str:
        seen = set()
        while title in mapping and title not in seen:
            seen.add(title)
            title = mapping[title]
        return title

    return {t: follow(t) for t in WIKIPEDIA_TITLES.values()}


def _fetch(slugs: list[str]) -> dict[str, SpeciesPhoto | None]:
    titles = [WIKIPEDIA_TITLES[s] for s in slugs]
    pages_q = _get(
        {
            "action": "query",
            "redirects": "1",
            "prop": "pageimages",
            "piprop": "name",
            "pilicense": "free",
            "titles": "|".join(titles),
        }
    )["query"]
    final = _resolve_titles(pages_q)
    image_by_page = {p["title"]: p.get("pageimage") for p in pages_q.get("pages", [])}
    file_by_slug = {
        s: image_by_page.get(final[WIKIPEDIA_TITLES[s]]) for s in slugs
    }

    files = sorted({_file_key(f) for f in file_by_slug.values() if f})
    info_by_file: dict[str, dict] = {}
    if files:
        info_q = _get(
            {
                "action": "query",
                "prop": "imageinfo",
                "iiprop": "url|size|extmetadata",
                "iiurlwidth": str(THUMB_WIDTH),
                "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl",
                "titles": "|".join(f"File:{f}" for f in files),
            }
        )["query"]
        for page in info_q.get("pages", []):
            infos = page.get("imageinfo") or []
            if infos:
                info_by_file[_file_key(page["title"])] = infos[0]

    out: dict[str, SpeciesPhoto | None] = {}
    for slug, file in file_by_slug.items():
        info = info_by_file.get(_file_key(file)) if file else None
        out[slug] = _to_photo(info) if info else None
    return out


def _to_photo(info: dict) -> SpeciesPhoto | None:
    meta = info.get("extmetadata", {})
    license_name = _plain(meta.get("LicenseShortName", {}).get("value"))
    if not _FREE_LICENSE_RE.match(license_name):
        # pilicense=free should already guarantee this; checked again
        # because showing a non-free photo is the one mistake here that
        # isn't just cosmetic.
        return None
    url = info.get("thumburl") or info.get("url")
    if not url:
        return None
    return SpeciesPhoto(
        url=url,
        width=int(info.get("thumbwidth") or info.get("width") or 0),
        height=int(info.get("thumbheight") or info.get("height") or 0),
        author=_plain(meta.get("Artist", {}).get("value")) or "Unknown author",
        license=license_name,
        license_url=_plain(meta.get("LicenseUrl", {}).get("value")) or None,
        file_page=info.get("descriptionurl", ""),
    )


def get_photos() -> dict[str, SpeciesPhoto | None]:
    """Photo (or None) for every guide species. Never raises."""
    now = time.monotonic()
    result: dict[str, SpeciesPhoto | None] = {}
    missing: list[str] = []
    with _lock:
        for slug in WIKIPEDIA_TITLES:
            entry = _cache.get(slug)
            ttl = CACHE_TTL_SECONDS if entry and entry[1] else NO_PHOTO_TTL_SECONDS
            if entry is not None and now - entry[0] < ttl:
                result[slug] = entry[1]
            else:
                missing.append(slug)

    if not missing or not get_settings().species_photos_enabled:
        return {**{s: None for s in missing}, **result}
    if _circuit.is_open():
        return {**{s: None for s in missing}, **result}

    try:
        fetched = _fetch(missing)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        _circuit.record(ok=False)
        print(f"species_photos: Wikipedia lookup failed: {exc!r}")
        return {**{s: None for s in missing}, **result}

    _circuit.record(ok=True)
    with _lock:
        for slug, photo in fetched.items():
            _cache[slug] = (now, photo)
    return {**fetched, **result}
