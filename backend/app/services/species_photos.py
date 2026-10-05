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
courtesy. Two batched API calls cover all species (titles are pipe-joined).

A lead image is not always a photograph: many fish articles lead with a
drawing (US Fish & Wildlife Service plates, old lithographs). Those are
skipped — the page already has its own illustration — and Commons is
searched for a photo of the species instead, one request per species that
needs it. `PINNED_FILES` overrides both when a pick needs a human's eye.

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
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
SEARCH_LIMIT = 20
MIN_PHOTO_WIDTH = 600
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

# A file to use for a species instead of whatever the lookup finds — for when
# the automatic pick turns out to be a poor photo. slug -> Commons file name.
PINNED_FILES: dict[str, str] = {}

# Many fish articles lead with a drawing (the US Fish & Wildlife Service
# plates by Duane Raver, 19th-century lithographs), and pilicense=free lets
# those through. The guide promises a *photo* next to its own illustration,
# so anything whose name, description, categories or credit reads like
# artwork is skipped. Erring towards skipping is fine: there are plenty of
# photographs of every guide species on Commons.
_NOT_A_PHOTO_RE = re.compile(
    r"illustrat|drawing|drawn by|painting|painted|watercolou?r|\bplate\b|lithograph|engraving|etching"
    r"|sketch|clip ?art|diagram|cartoon|artwork|range map|distribution map|\bmap\b|raver|knepp"
    r"|cuvier|valenciennes|\bbloch\b|\bstamp\b|\blogo\b|skeleton|fossil",
    re.IGNORECASE,
)
_PHOTO_MIMES = ("image/jpeg", "image/webp")

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


# Hand-checked photographs, one per guide species, served without asking
# Wikipedia anything. Each was looked at (a real fish, not a drawing) and its
# licence and author read off its Commons page on 2026-10-01. Three differ
# from the article's lead image: two lead images are paintings (black
# crappie, hybrid striped bass) and one article has none (gizzard shad). A species listed here
# never depends on Wikipedia being reachable from the server; the live lookup
# below only runs for a species added to the guide later and not yet here.
CURATED_PHOTOS: dict[str, SpeciesPhoto] = {
    "largemouth-bass": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/Largemouth_Bass_%28Micropterus_salmoides%29_June_2023_%28cropped%29.jpg/960px-Largemouth_Bass_%28Micropterus_salmoides%29_June_2023_%28cropped%29.jpg",
        width=960,
        height=540,
        author='Sam Stukel, USFWS Mountain-Prairie',
        license='Public domain',
        license_url=None,
        file_page="https://commons.wikimedia.org/wiki/File:Largemouth_Bass_(Micropterus_salmoides)_June_2023_(cropped).jpg",
    ),
    "spotted-bass": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/e/e7/Micropterus_punctulatus.jpg",
        width=672,
        height=377,
        author='U.S. Geological Survey',
        license='Public domain',
        license_url=None,
        file_page="https://commons.wikimedia.org/wiki/File:Micropterus_punctulatus.jpg",
    ),
    "white-bass": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/White_Bass_%28Morone_chrysops%29.jpg/960px-White_Bass_%28Morone_chrysops%29.jpg",
        width=960,
        height=533,
        author='Sam Stukel, USFWS Mountain-Prairie',
        license='Public domain',
        license_url=None,
        file_page="https://commons.wikimedia.org/wiki/File:White_Bass_(Morone_chrysops).jpg",
    ),
    "striped-bass": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/7/74/Morone_saxatilis_SI2.jpg",
        width=640,
        height=366,
        author='D Ross Robertson',
        license='Public domain',
        license_url=None,
        file_page="https://commons.wikimedia.org/wiki/File:Morone_saxatilis_SI2.jpg",
    ),
    "hybrid-striped-bass": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Hybrid_white-striped_bass_%2850090643236%29.jpg/960px-Hybrid_white-striped_bass_%2850090643236%29.jpg",
        width=960,
        height=594,
        author='Oregon Department of Fish & Wildlife',
        license='CC BY-SA 2.0',
        license_url='https://creativecommons.org/licenses/by-sa/2.0',
        file_page="https://commons.wikimedia.org/wiki/File:Hybrid_white-striped_bass_(50090643236).jpg",
    ),
    "channel-catfish": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/thumb/3/38/Channel_Catfish_%28Ictalurus_punctatus%29_white_background.jpg/960px-Channel_Catfish_%28Ictalurus_punctatus%29_white_background.jpg",
        width=960,
        height=320,
        author='Sam Stukel, USFWS Mountain-Prairie',
        license='Public domain',
        license_url=None,
        file_page="https://commons.wikimedia.org/wiki/File:Channel_Catfish_(Ictalurus_punctatus)_white_background.jpg",
    ),
    "blue-catfish": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Blue_Catfish_%28Ictalurus_furcatus%29_%2853011311615%29.jpg/960px-Blue_Catfish_%28Ictalurus_furcatus%29_%2853011311615%29.jpg",
        width=960,
        height=314,
        author='Sam Stukel, USFWS Mountain-Prairie',
        license='Public domain',
        license_url=None,
        file_page="https://commons.wikimedia.org/wiki/File:Blue_Catfish_(Ictalurus_furcatus)_(53011311615).jpg",
    ),
    "white-crappie": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/9/9d/White_Crappie.jpg",
        width=787,
        height=599,
        author='U.S. Army Corps of Engineers',
        license='Public domain',
        license_url=None,
        file_page="https://commons.wikimedia.org/wiki/File:White_Crappie.jpg",
    ),
    "black-crappie": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Black_Crappie_%28Pomoxis_nigromaculatus%29_%2853084649608%29.jpg/960px-Black_Crappie_%28Pomoxis_nigromaculatus%29_%2853084649608%29.jpg",
        width=960,
        height=640,
        author='Sam Stukel, USFWS Mountain-Prairie',
        license='Public domain',
        license_url=None,
        file_page="https://commons.wikimedia.org/wiki/File:Black_Crappie_(Pomoxis_nigromaculatus)_(53084649608).jpg",
    ),
    "bluegill": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/d/d4/Bluegill_%28cropped%29.jpg",
        width=694,
        height=451,
        author='Paleo1954',
        license='CC BY-SA 4.0',
        license_url='https://creativecommons.org/licenses/by-sa/4.0',
        file_page="https://commons.wikimedia.org/wiki/File:Bluegill_(cropped).jpg",
    ),
    "gizzard-shad": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Dorosoma_cepedianum_%28S0095%29_%2812678953465%29.jpg/960px-Dorosoma_cepedianum_%28S0095%29_%2812678953465%29.jpg",
        width=960,
        height=312,
        author='Smithsonian Environmental Research Center',
        license='CC BY 2.0',
        license_url='https://creativecommons.org/licenses/by/2.0',
        file_page="https://commons.wikimedia.org/wiki/File:Dorosoma_cepedianum_(S0095)_(12678953465).jpg",
    ),
    "threadfin-shad": SpeciesPhoto(
        url="https://upload.wikimedia.org/wikipedia/commons/d/d8/Dorosoma_petenense.jpeg",
        width=768,
        height=323,
        author='Bill Stagnaro',
        license='CC BY-SA 3.0',
        license_url='https://creativecommons.org/licenses/by-sa/3.0',
        file_page="https://commons.wikimedia.org/wiki/File:Dorosoma_petenense.jpeg",
    ),
}


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


def _get(params: dict[str, str], url: str = API_URL) -> dict:
    headers = {"User-Agent": get_settings().wikimedia_user_agent}
    last: Exception | None = None
    for attempt in range(2):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
                resp = client.get(url, params={**params, "format": "json", "formatversion": "2"})
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


_IMAGEINFO_PARAMS = {
    "prop": "imageinfo",
    "iiprop": "url|size|mime|extmetadata",
    "iiurlwidth": str(THUMB_WIDTH),
    "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|ImageDescription|Categories",
}


def _looks_like_photo(file_name: str, info: dict) -> bool:
    mime = info.get("mime")
    if mime and mime not in _PHOTO_MIMES:
        return False
    if int(info.get("width") or MIN_PHOTO_WIDTH) < MIN_PHOTO_WIDTH:
        return False
    meta = info.get("extmetadata", {})
    text = " ".join(
        [
            file_name,
            _plain(meta.get("ImageDescription", {}).get("value")),
            _plain(meta.get("Categories", {}).get("value")),
            _plain(meta.get("Artist", {}).get("value")),
        ]
    )
    return not _NOT_A_PHOTO_RE.search(text)


def _photo_from(file_name: str, info: dict | None) -> SpeciesPhoto | None:
    if not info or not _looks_like_photo(file_name, info):
        return None
    return _to_photo(info)


def _imageinfo(files: list[str]) -> dict[str, dict]:
    if not files:
        return {}
    info_q = _get({"action": "query", **_IMAGEINFO_PARAMS, "titles": "|".join(f"File:{f}" for f in files)})["query"]
    out: dict[str, dict] = {}
    for page in info_q.get("pages", []):
        infos = page.get("imageinfo") or []
        if infos:
            out[_file_key(page["title"])] = infos[0]
    return out


def _search_commons(scientific_name: str) -> SpeciesPhoto | None:
    """The first freely licensed photograph on Commons that names the
    species — used when the article's lead image is a drawing or missing."""
    q = _get(
        {
            "action": "query",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrsearch": f'"{scientific_name}" filetype:bitmap',
            "gsrlimit": str(SEARCH_LIMIT),
            **_IMAGEINFO_PARAMS,
        },
        url=COMMONS_API_URL,
    ).get("query", {})
    pages = sorted(q.get("pages", []), key=lambda p: p.get("index", 0))
    for page in pages:
        infos = page.get("imageinfo") or []
        photo = _photo_from(page.get("title", ""), infos[0] if infos else None)
        if photo is not None:
            return photo
    return None


def _scientific_name(slug: str) -> str | None:
    from app.knowledge.species_guides import get_guide

    guide = get_guide(slug)
    return guide.scientific_name if guide else None


def _fetch(slugs: list[str]) -> dict[str, SpeciesPhoto | None]:
    """Photo per slug. A slug missing from the result couldn't be looked up
    this time (its fallback search failed) and should be retried, not cached."""
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
    file_by_slug = {s: PINNED_FILES.get(s) or image_by_page.get(final[WIKIPEDIA_TITLES[s]]) for s in slugs}

    info_by_file = _imageinfo(sorted({_file_key(f) for f in file_by_slug.values() if f}))

    out: dict[str, SpeciesPhoto | None] = {}
    for slug, file in file_by_slug.items():
        if file and slug in PINNED_FILES:
            # A pinned file was chosen by a person; only the licence is checked.
            info = info_by_file.get(_file_key(file))
            out[slug] = _to_photo(info) if info else None
            continue
        photo = _photo_from(file, info_by_file.get(_file_key(file))) if file else None
        if photo is None:
            sci = _scientific_name(slug)
            if sci:
                try:
                    photo = _search_commons(sci)
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    print(f"species_photos: Commons search failed for {slug}: {exc!r}")
                    continue
        out[slug] = photo
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
            if slug in CURATED_PHOTOS:
                result[slug] = CURATED_PHOTOS[slug]
                continue
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
    return {**{s: None for s in missing}, **fetched, **result}
