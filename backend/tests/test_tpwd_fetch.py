"""The TPWD page fetcher (app/data_import/tpwd_fetch.py). No network: an
httpx MockTransport plays TPWD's server."""
import json
from urllib.robotparser import RobotFileParser

import httpx
import pytest

from app.data_import import tpwd_fetch as tf

ROBOTS = """User-agent: *
Disallow: /*?
Disallow: /private/
"""

INDEX = """<html><body>
<a href="/publications/pwdpubs/lake_survey/pwd_rp_t3200_1374/">Somerville</a>
<a href="pwd_rp_t3200_1257/index.phtml">Bryan</a>
<a href="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1374/">Somerville again</a>
<a href="/publications/pwdpubs/lake_survey/pwd_rp_t3200_9999/?year=2019">query string</a>
<a href="https://example.com/publications/pwdpubs/lake_survey/pwd_rp_t3200_5555/">other site</a>
<a href="/publications/pwdpubs/media/lake_survey/pwd_rp_t3200_1374_2022.pdf">pdf</a>
</body></html>"""

LAKE_LIST = """<html><body>
<a href="/fishboat/fish/recreational/lakes/somerville/">Somerville</a>
<a href="bryan/index.phtml">Bryan</a>
<a href="/fishboat/fish/recreational/lakes/lakelist.phtml">this page</a>
<a href="/fishboat/fish/recreational/lakes/somerville/access.phtml">access</a>
</body></html>"""


def test_report_links_are_static_tpwd_report_pages_each_once():
    assert tf.report_links(INDEX) == ["pwd_rp_t3200_1374", "pwd_rp_t3200_1257"]


def test_lake_links_are_lake_folders_each_once():
    assert tf.lake_links(LAKE_LIST) == ["somerville", "bryan"]


def _robots(text: str = ROBOTS) -> RobotFileParser:
    parser = RobotFileParser()
    parser.parse(text.splitlines())
    return parser


class Server:
    """Counts requests; serves the pages above, 404 for anything else."""

    def __init__(self) -> None:
        self.requested: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requested.append(url)
        if url == tf.SURVEY_INDEX_URL:
            return httpx.Response(200, text=INDEX)
        if url == tf.LAKE_LIST_URL:
            return httpx.Response(200, text=LAKE_LIST)
        if "pwd_rp_t3200_" in url or url.endswith("/somerville/") or url.endswith("/somerville/access.phtml"):
            return httpx.Response(200, text=f"<p>{url}</p>")
        return httpx.Response(404, text="not found")


def _fetcher(server: Server, robots: RobotFileParser | None = None) -> tf.Fetcher:
    client = httpx.Client(transport=httpx.MockTransport(server))
    return tf.Fetcher(client, robots or _robots(), "fisheye-test", delay=0, sleep=lambda s: None)


def test_fetches_every_listed_page_into_the_cache(tmp_path):
    server = Server()
    summary = tf.run(tmp_path, _fetcher(server))

    names = sorted(p.name for p in tmp_path.glob("*.html"))
    assert names == sorted([
        "survey_index__index.html",
        "lake_list__lakelist.html",
        "report__pwd_rp_t3200_1374.html",
        "report__pwd_rp_t3200_1257.html",
        "lake__somerville.html",
        "lake_access__somerville.html",
    ])
    # bryan's two pages are 404s: recorded, not saved, not fatal.
    assert (summary.fetched, summary.missing, summary.failed) == (6, 2, 0)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["lake__bryan.html"]["status"] == 404
    assert manifest["report__pwd_rp_t3200_1374.html"]["url"].endswith("/pwd_rp_t3200_1374/")
    assert all("?" not in url for url in server.requested)


def test_a_rerun_uses_the_cache_and_requests_nothing(tmp_path):
    tf.run(tmp_path, _fetcher(Server()))
    server = Server()
    summary = tf.run(tmp_path, _fetcher(server))
    assert server.requested == []
    assert summary.cached == 8 and summary.fetched == 0


def test_refresh_downloads_again(tmp_path):
    tf.run(tmp_path, _fetcher(Server()))
    server = Server()
    tf.run(tmp_path, _fetcher(server), refresh=True)
    assert len(server.requested) == 8


def test_limit_takes_the_first_few(tmp_path):
    server = Server()
    tf.run(tmp_path, _fetcher(server), limit=1)
    assert sum("pwd_rp_t3200_" in u for u in server.requested) == 1
    assert not any("/bryan/" in u for u in server.requested)


def test_query_string_urls_are_refused_before_any_request():
    server = Server()
    with pytest.raises(tf.FetchRefused):
        _fetcher(server).get("https://tpwd.texas.gov/fishboat/x.php?WB_code=1")
    assert server.requested == []


def test_robots_txt_is_obeyed(tmp_path):
    """If TPWD disallowed the report pages, the fetch stops instead of
    carrying on."""
    server = Server()
    strict = _robots("User-agent: *\nDisallow: /publications/\n")
    with pytest.raises(tf.FetchRefused):
        tf.run(tmp_path, _fetcher(server, strict))
    assert server.requested == []


def test_requests_are_spaced_out():
    waits: list[float] = []
    client = httpx.Client(transport=httpx.MockTransport(Server()))
    fetcher = tf.Fetcher(client, _robots(), "fisheye-test", delay=2.0, sleep=waits.append)
    fetcher.get(tf.SURVEY_INDEX_URL)
    fetcher.get(tf.LAKE_LIST_URL)
    assert len(waits) == 1 and 1.5 < waits[0] <= 2.0
