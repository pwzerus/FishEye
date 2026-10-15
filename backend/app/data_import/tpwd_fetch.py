"""Download TPWD's lake pages once, politely, into a local cache.

The statewide TPWD import works in two steps so that only this one needs
the network, and everything that interprets the pages can be re-run, tested
and changed offline against exactly the same input:

    1. fetch (this module): save the raw pages to a folder
    2. import: read that folder and write the database

WHAT IT FETCHES
---------------
- The Fishery Management Survey Reports index, and every reservoir report
  it links to (about 175 large reservoirs, plus the small-reservoir and
  river reports listed on the same page).
- TPWD's alphabetical lake list, and each lake's overview page and access
  page.

All of these are static pages. Nothing with a query string is requested:
TPWD's robots.txt disallows those, which is why the stocking-history pages
are not used at all (docs/adr/0002-tpwd-data-ingestion.md). On top of that
fixed rule, every URL is checked against the live robots.txt before it is
requested, so a future change on TPWD's side stops the fetch rather than
being ignored.

Requests are spaced REQUEST_DELAY_SECONDS apart and carry an identifying
User-Agent. A re-run skips pages already in the cache, so an interrupted
fetch can simply be started again; --refresh downloads everything anew.

Run (on a machine with network access; takes about 15 minutes):
    python -m app.data_import.tpwd_fetch
    python -m app.data_import.tpwd_fetch --out tpwd_cache --limit 5   # quick trial
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import get_settings

BASE = "https://tpwd.texas.gov"
ROBOTS_URL = f"{BASE}/robots.txt"
SURVEY_INDEX_URL = f"{BASE}/publications/pwdpubs/lake_survey/index.phtml"
LAKE_LIST_URL = f"{BASE}/fishboat/fish/recreational/lakes/lakelist.phtml"

REQUEST_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 30.0
DEFAULT_OUT = Path("tpwd_cache")

# A survey report's own page: /publications/pwdpubs/lake_survey/pwd_rp_t3200_1374/
_REPORT_HREF = re.compile(r"/publications/pwdpubs/lake_survey/(pwd_rp_t3200_\d+)/?(?:index\.phtml)?$")
# A lake's page: /fishboat/fish/recreational/lakes/somerville/ (or .../index.phtml)
_LAKE_HREF = re.compile(r"/fishboat/fish/recreational/lakes/([a-z0-9_-]+)/?(?:index\.phtml)?$")
_HREF = re.compile(r"""href\s*=\s*["']([^"'#]+)["']""", re.IGNORECASE)


class FetchRefused(Exception):
    """A URL this fetcher must not request."""


@dataclass(frozen=True)
class Page:
    kind: str  # robots | survey_index | report | lake_list | lake | lake_access
    key: str  # report id or lake slug; the page's own name for the singletons
    url: str

    @property
    def filename(self) -> str:
        return f"{self.kind}__{self.key}.html"


def report_links(html: str) -> list[str]:
    """Report ids (pwd_rp_t3200_NNNN) linked from the survey index, in page
    order, each once."""
    return _unique(m.group(1) for m in _matches(html, SURVEY_INDEX_URL, _REPORT_HREF))


def lake_links(html: str) -> list[str]:
    """Lake slugs linked from the lake list, in page order, each once."""
    return _unique(m.group(1) for m in _matches(html, LAKE_LIST_URL, _LAKE_HREF))


def _matches(html: str, page_url: str, pattern: re.Pattern[str]):
    for href in _HREF.findall(html):
        absolute = urljoin(page_url, href.strip())
        parts = urlsplit(absolute)
        if parts.netloc != urlsplit(BASE).netloc or parts.query:
            continue
        m = pattern.search(parts.path)
        if m:
            yield m


def _unique(items) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return list(seen)


def report_page(report_id: str) -> Page:
    return Page("report", report_id, f"{BASE}/publications/pwdpubs/lake_survey/{report_id}/")


def lake_pages(slug: str) -> list[Page]:
    root = f"{BASE}/fishboat/fish/recreational/lakes/{slug}/"
    return [Page("lake", slug, root), Page("lake_access", slug, root + "access.phtml")]


class Fetcher:
    """One polite HTTP client: robots-checked, spaced, identified."""

    def __init__(
        self,
        client: httpx.Client,
        robots: RobotFileParser,
        user_agent: str,
        delay: float = REQUEST_DELAY_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.client = client
        self.robots = robots
        self.user_agent = user_agent
        self.delay = delay
        self.sleep = sleep
        self._last = 0.0

    def get(self, url: str) -> httpx.Response:
        if urlsplit(url).query or "$" in url:
            raise FetchRefused(f"query-string URLs are disallowed by TPWD's robots.txt: {url}")
        if not self.robots.can_fetch(self.user_agent, url):
            raise FetchRefused(f"robots.txt disallows {url}")
        wait = self._last + self.delay - time.monotonic()
        if wait > 0:
            self.sleep(wait)
        try:
            return self.client.get(url)
        finally:
            self._last = time.monotonic()


@dataclass
class FetchSummary:
    fetched: int = 0
    cached: int = 0
    missing: int = 0  # 404 and the like: recorded, not fatal
    failed: int = 0


def run(out: Path, fetcher: Fetcher, refresh: bool = False, limit: int | None = None) -> FetchSummary:
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    manifest: dict[str, dict] = {}
    if manifest_path.exists() and not refresh:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = FetchSummary()

    def save_manifest() -> None:
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")

    def get(page: Page) -> str | None:
        path = out / page.filename
        entry = manifest.get(page.filename)
        if not refresh and entry and entry.get("status") == 200 and path.exists():
            summary.cached += 1
            return path.read_text(encoding="utf-8")
        if not refresh and entry and entry.get("status") == 404:
            summary.cached += 1
            return None
        try:
            resp = fetcher.get(page.url)
        except FetchRefused:
            raise
        except httpx.HTTPError as exc:
            summary.failed += 1
            print(f"  failed  {page.url}: {exc}")
            return None
        record = {
            "kind": page.kind,
            "key": page.key,
            "url": page.url,
            "status": resp.status_code,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        if resp.status_code == 200:
            path.write_text(resp.text, encoding="utf-8")
            record["sha256"] = hashlib.sha256(resp.content).hexdigest()
            summary.fetched += 1
        elif resp.status_code == 404:
            summary.missing += 1
        else:
            summary.failed += 1
            print(f"  HTTP {resp.status_code}  {page.url}")
        manifest[page.filename] = record
        save_manifest()
        return resp.text if resp.status_code == 200 else None

    index = get(Page("survey_index", "index", SURVEY_INDEX_URL))
    reports = report_links(index or "")
    lake_list = get(Page("lake_list", "lakelist", LAKE_LIST_URL))
    slugs = lake_links(lake_list or "")
    print(f"{len(reports)} survey reports and {len(slugs)} lakes listed")
    if limit is not None:
        reports, slugs = reports[:limit], slugs[:limit]

    for i, report_id in enumerate(reports, 1):
        get(report_page(report_id))
        if i % 25 == 0:
            print(f"  reports {i}/{len(reports)}")
    for i, slug in enumerate(slugs, 1):
        for page in lake_pages(slug):
            get(page)
        if i % 25 == 0:
            print(f"  lakes {i}/{len(slugs)}")
    return summary


def load_robots(client: httpx.Client, out: Path) -> RobotFileParser:
    """Fetch robots.txt (always fresh) and keep a copy next to the pages,
    so the cache records the rules it was fetched under."""
    resp = client.get(ROBOTS_URL)
    resp.raise_for_status()
    out.mkdir(parents=True, exist_ok=True)
    (out / "robots.txt").write_text(resp.text, encoding="utf-8")
    parser = RobotFileParser()
    parser.parse(resp.text.splitlines())
    return parser


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"cache folder (default: {DEFAULT_OUT})")
    ap.add_argument("--refresh", action="store_true", help="download every page again")
    ap.add_argument("--limit", type=int, help="only the first N reports and N lakes (a quick trial)")
    args = ap.parse_args(argv)

    user_agent = get_settings().tpwd_user_agent
    headers = {"User-Agent": user_agent}
    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, headers=headers, follow_redirects=True) as client:
        robots = load_robots(client, args.out)
        fetcher = Fetcher(client, robots, user_agent)
        try:
            summary = run(args.out, fetcher, refresh=args.refresh, limit=args.limit)
        except FetchRefused as exc:
            print(f"Stopped: {exc}", file=sys.stderr)
            return 2
    print(
        f"done: {summary.fetched} downloaded, {summary.cached} already cached, "
        f"{summary.missing} not found, {summary.failed} failed -> {args.out}/"
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    sys.exit(main())
