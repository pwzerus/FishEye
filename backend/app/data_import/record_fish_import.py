"""State fish records and ShareLunker entries, as evidence a fish is in a lake.

docs/adr/0034-california-official-data.md. A state record, a lake record or
a ShareLunker entry is a fish an agency weighed and verified, from a named
lake. Here it is used for one thing only: evidence that the species lives
in that lake. Stored per lake and species: the year and a link to the
agency's page (provenance.add_evidence), in FishEye's own sentence. Never
stored: angler names, weights, baits, photos or the agency's text (rules 3
and 8; the fetchers drop them before anything is written to disk). The app
shows these as a species row with its source link, and nothing else: no
"big fish" or record feature.

Sources (docs/data-sources.md):
- Texas: TPWD's Water Body Records, one page per lake, reached from the
  seven region lists of TPWD's record search (RESTRICTED: facts + link);
  Toyota ShareLunker entries, from the archive's own "Download CSV" (all
  largemouth bass; RESTRICTED: facts + link).
- Georgia: WRD's State Record Freshwater Fish list (RESTRICTED: facts + link).
- California: CDFW's angling records, freshwater rows (CDFW site terms:
  public domain; stored as facts + link all the same).

Matching a record's water to a lake: the same name (lake_key, any word
order) among the state's lakes, verified lakes first; in California a name
plus county from CDFW's lake layer. Rivers, "private pond", and names more
than one lake share are not guessed: they are listed as unmatched.

    python -m app.data_import.record_fish_import --fetch-tpwd      # network, ~10 min
    python -m app.data_import.record_fish_import --state TX
    python -m app.data_import.record_fish_import --state GA
    python -m app.data_import.record_fish_import --state CA
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_import.ga_wrd_import import lake_key
from app.data_import.provenance import USER_AGENT, add_evidence, prune_evidence, source_record
from app.data_import.species_names import canonical
from app.data_import.tpwd_statewide_import import NAME_ALIASES
from app.data_import.untyped_water import QUALIFIERS
from app.models.waterbody import State, Waterbody

DEFAULT_CACHE = Path("records_cache")
TPWD_BASE = "https://tpwd.texas.gov/fishboat/fish"
TPWD_REGIONS = range(1, 8)
TPWD_DELAY_S = 5.0  # a small agency site (data-sourcing rule 5)
SHARELUNKER_URL = "https://texassharelunker.com/archives/"
GA_URL = "https://georgiawildlife.com/fishing/recordprogram"
CA_URL = "https://wildlife.ca.gov/Fishing/Records"
# A record from before this year is shown as "reported", not "confirmed": a
# 1932 fish says the species was there then.
CONFIRMED_SINCE = 2000

_NOT_A_LAKE = re.compile(r"\b(river|creek|bayou|canal|slough|branch|spillway|tailrace|bay|gulf)\b", re.I)
_NO_SPECIFIC_LAKE = re.compile(r"\b(private|pond in|county pond)\b|^\w+ county pond$", re.I)


# --------------------------------------------------------------------------
# Fetch: TPWD water body records (facts only)
# --------------------------------------------------------------------------


def parse_region_page(text: str) -> list[tuple[str, str]]:
    """(WB_code, lake name) for every water body link on a region list."""
    return [
        (code, html.unescape(re.sub(r"\s+", " ", name)).strip())
        for code, name in re.findall(r'waterecords\.php\?WB_code=(\d+)"[^>]*>([^<]+)<', text)
    ]


def parse_water_records(text: str) -> tuple[str, list[tuple[str, int | None]]]:
    """(lake name, [(species, year)]) from one Water Body Records page. Only
    the Species and Date cells are read; nothing else on the page is kept."""
    title = re.search(r"Water Body Records for\s*([^<]+)", text)
    lake = html.unescape(title.group(1)).strip() if title else ""
    out: list[tuple[str, int | None]] = []
    for table in re.findall(r"<table.*?</table>", text, re.S | re.I):
        rows = re.findall(r"<tr.*?</tr>", table, re.S | re.I)
        if not rows:
            continue
        head = [re.sub(r"<[^>]+>", "", c).strip().lower() for c in re.findall(r"<t[dh].*?</t[dh]>", rows[0], re.S | re.I)]
        if "species" not in head or "date" not in head:
            continue
        si, di = head.index("species"), head.index("date")
        for row in rows[1:]:
            cells = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c))).strip()
                     for c in re.findall(r"<t[dh].*?</t[dh]>", row, re.S | re.I)]
            if len(cells) <= max(si, di) or not cells[si]:
                continue
            y = re.search(r"(19|20)\d\d", cells[di])
            out.append((cells[si], int(y.group(0)) if y else None))
    return lake, out


def fetch_tpwd(cache: Path) -> Path:
    """Every TPWD water body record page, reduced to facts, saved as it goes
    (an interrupted fetch resumes)."""
    import httpx

    path = cache / "tpwd_water_records.json"
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"lakes": {}}
    cache.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60, headers={"User-Agent": USER_AGENT}) as client:
        codes: dict[str, str] = {}
        for region in TPWD_REGIONS:
            resp = client.get(f"{TPWD_BASE}/programs/fishrecords/watersearch.php", params={"travregion": region})
            resp.raise_for_status()
            codes.update(dict(parse_region_page(resp.text)))
            time.sleep(TPWD_DELAY_S)
        todo = [c for c in sorted(codes) if c not in data["lakes"]]
        print(f"{len(codes)} TPWD water bodies with records; {len(todo)} to fetch")
        for i, code in enumerate(todo, 1):
            url = f"{TPWD_BASE}/action/waterecords.php?WB_code={code}"
            resp = client.get(url)
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(60)
                resp = client.get(url)
            resp.raise_for_status()
            lake, records = parse_water_records(resp.text)
            data["lakes"][code] = {"water": lake or codes[code], "url": url,
                                   "records": [{"species": s, "year": y} for s, y in records]}
            data["fetched_at"] = datetime.now(timezone.utc).isoformat()
            if i % 20 == 0 or i == len(todo):
                path.write_text(json.dumps(data), encoding="utf-8")
                print(f"  {i}/{len(todo)}")
            time.sleep(TPWD_DELAY_S)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# Matching a record's water to a lake
# --------------------------------------------------------------------------


def _words(name: str) -> tuple[str, ...]:
    # TPWD's lists write an apostrophe as a backtick ("Bois d`Arc Lake").
    return tuple(sorted(lake_key(name.replace("`", "")).split()))


class LakeNames:
    """The state's lakes by name: own name, official name, agency name."""

    def __init__(self, lakes: list[Waterbody]) -> None:
        self.by_words: dict[tuple[str, ...], list[Waterbody]] = defaultdict(list)
        for wb in lakes:
            names = {wb.name, wb.official_name or "", wb.agency_profile.agency_name if wb.agency_profile else ""}
            # A verified Texas lake goes by TPWD's name; records may use the
            # other one ("Lake LBJ" / "Lyndon B. Johnson").
            names |= {osm_name for tpwd_name, osm_name in NAME_ALIASES.items() if tpwd_name in names}
            for n in names:
                if n:
                    words = _words(n)
                    if words and wb not in self.by_words[words]:
                        self.by_words[words].append(wb)

    def find(self, water: str) -> tuple[Waterbody | None, str]:
        name = re.sub(r"\s+at\s+.*$", "", water).strip()  # "Castaic Lake at the main boat ramp"
        # "Spring Lake Park" is a park named after its lake: match "Spring
        # Lake", not "Spring Park Lake" (same words, another water). "Alvarado
        # Park", with no lake word, still matches "Alvarado Park Lake".
        if m := re.match(r"^(.*\b(?:lake|pond|reservoir))\s+(?:state\s+|city\s+|county\s+)?park$", name, re.I):
            name = m.group(1)
        if _NO_SPECIFIC_LAKE.search(name):
            return None, "no specific lake named"
        candidates = [name] + re.findall(r"\(([^)]+)\)", name) + [re.sub(r"\(.*?\)", " ", name)]
        for cand in candidates:
            words = _words(cand)
            if not words:
                continue
            # "Upper Lake", "North Pond": with no county or place, such a name
            # could be any of many waters; one lake of that name in the state
            # is not enough to say it is the record's.
            if set(words) <= QUALIFIERS:
                return None, "name too general"
            hits = self.by_words.get(words, [])
            verified = [wb for wb in hits if wb.data_tier == "verified"]
            pick = verified if verified else hits
            if len(pick) == 1:
                return pick[0], "name"
            if len(pick) > 1:
                return None, f"ambiguous: {len(pick)} lakes named {cand.strip()}"
        if _NOT_A_LAKE.search(name):
            return None, "a river, creek or bay, not a lake"
        return None, "no lake of that name"


@dataclass
class ImportSummary:
    read: int = 0
    matched: int = 0
    evidence_new: int = 0
    evidence_total: int = 0
    species_skipped: int = 0
    unmatched: list[str] = field(default_factory=list)


def _confidence(year: int | None) -> str:
    return "confirmed" if year and year >= CONFIRMED_SINCE else "reported"


def _record(db: Session, wb: Waterbody, sp: str, *, source: str, key: str, year: int | None, sentence: str,
            url: str, rec: Any, now: datetime, summary: ImportSummary, kept: set[str]) -> None:
    kept.add(key)
    summary.evidence_total += 1
    if add_evidence(db, wb, sp, source=source, source_key=key, kind="record", year=year, evidence=sentence,
                    source_url=url, record=rec, confidence=_confidence(year), now=now):
        summary.evidence_new += 1


def _fetched(payload: dict[str, Any], now: datetime) -> datetime:
    stamp = payload.get("fetched_at")
    try:
        return datetime.fromisoformat(stamp).astimezone(timezone.utc).replace(tzinfo=None) if stamp else now
    except ValueError:
        return now


def import_texas(db: Session, names: LakeNames, cache: Path, now: datetime) -> dict[str, ImportSummary]:
    out: dict[str, ImportSummary] = {}
    path = cache / "tpwd_water_records.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        rec = source_record(db, "tpwd_records", _fetched(data, now))
        s, kept = ImportSummary(), set()
        # (lake, species) -> (year, code, url): TPWD can list one lake under
        # two water-body codes; the newest record is the one kept.
        best: dict[tuple[int, str], tuple[int | None, str, str]] = {}
        lakes_by_id: dict[int, Waterbody] = {}
        for code, lake in sorted(data["lakes"].items()):
            wb, why = names.find(lake["water"])
            latest: dict[str, int | None] = {}
            for r in lake["records"]:
                s.read += 1
                hit = canonical(r["species"])
                if hit is None:
                    s.species_skipped += 1
                    continue
                y = r.get("year")
                if hit[0] not in latest or (y or 0) > (latest[hit[0]] or 0):
                    latest[hit[0]] = y
            if wb is None:
                if latest:
                    s.unmatched.append(f"{lake['water']} (TPWD water body {code}): {why}")
                continue
            s.matched += 1
            lakes_by_id[wb.id] = wb
            for sp, y in latest.items():
                prev = best.get((wb.id, sp))
                if prev is None or (y or 0) > (prev[0] or 0):
                    best[(wb.id, sp)] = (y, code, lake["url"])
        for (wb_id, sp), (y, code, url) in sorted(best.items()):
            when = f" from {y}" if y else ""
            _record(db, lakes_by_id[wb_id], sp, source="tpwd_records", key=f"{code}:{sp}", year=y,
                    sentence=f"TPWD's water body records for this lake include a {sp}{when}.",
                    url=url, rec=rec, now=now, summary=s, kept=kept)
        prune_evidence(db, "tpwd_records", kept)
        out["tpwd_records"] = s
    path = cache / "sharelunker.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        rec = source_record(db, "sharelunker", _fetched(data, now))
        s, kept = ImportSummary(), set()
        by_lake: dict[str, list[int | None]] = defaultdict(list)
        for r in data["rows"]:
            s.read += 1
            water = r.get("lake_name") or ""
            if not water or water == "NULL":
                water = r.get("water_other") or ""
            by_lake[water].append(r.get("year"))
        # Several names can be one lake ("Ivie", "O. H. Ivie"): one fact per
        # lake, with the newest year, keyed by the first name.
        per_lake: dict[int, tuple[Waterbody, int | None, str]] = {}
        for water, years in sorted(by_lake.items()):
            wb, why = names.find(water) if water else (None, "no lake named")
            if wb is None:
                s.unmatched.append(f"{water or '(no lake given)'} ({len(years)} entries): {why}")
                continue
            s.matched += len(years)
            y = max((v for v in years if v), default=None)
            prev = per_lake.get(wb.id)
            key = prev[2] if prev else f"{lake_key(water)}:Largemouth Bass"
            per_lake[wb.id] = (wb, max(y or 0, prev[1] or 0) if prev else y, key)
        for wb, y, key in per_lake.values():
            _record(db, wb, "Largemouth Bass", source="sharelunker", key=key, year=y or None,
                    sentence="TPWD's Toyota ShareLunker program has entries of Largemouth Bass from this lake"
                             + (f" (most recent {y})." if y else "."),
                    url=SHARELUNKER_URL, rec=rec, now=now, summary=s, kept=kept)
        prune_evidence(db, "sharelunker", kept)
        out["sharelunker"] = s
    return out


def import_list(db: Session, names: LakeNames, rows: list[dict[str, Any]], *, source: str, url: str,
                sentence: str, rec: Any, now: datetime, county_lookup: Any = None) -> ImportSummary:
    s, kept = ImportSummary(), set()
    for r in rows:
        s.read += 1
        hit = canonical(r["species"])
        if hit is None:
            s.species_skipped += 1
            s.unmatched.append(f"{r['species']} at {r['water']}: species not mapped")
            continue
        wb, why = (county_lookup(r) if county_lookup else (None, "")) or (None, "")
        if wb is None:
            wb, why = names.find(r["water"])
        if wb is None:
            s.unmatched.append(f"{hit[0]} at {r['water']}{' (' + r['county'] + ' County)' if r.get('county') else ''}: {why}")
            continue
        s.matched += 1
        y = r.get("year")
        _record(db, wb, hit[0], source=source, key=f"{lake_key(r['water'])}:{hit[0]}", year=y,
                sentence=sentence.format(species=hit[0], when=f" ({y})" if y else ""),
                url=url, rec=rec, now=now, summary=s, kept=kept)
    prune_evidence(db, source, kept)
    return s


def _ca_county_lookup(db: Session, state: State, cdfw_cache: Path) -> Any:
    """California: a record's water and county, through CDFW's lake layer, to
    the lake carrying that DFGWATERID."""
    path = cdfw_cache / "ca_lakes.json"
    if not path.exists():
        return None
    by_name_county: dict[tuple[tuple[str, ...], str], set[int]] = defaultdict(set)
    for r in json.loads(path.read_text(encoding="utf-8")):
        if r.get("name"):
            for county in (r.get("county") or "").split(","):
                by_name_county[(_words(r["name"]), county.strip().lower())].add(r["id"])
    by_dfg = {wb.dfg_water_id: wb for wb in db.scalars(select(Waterbody).where(
        Waterbody.state_id == state.id, Waterbody.dfg_water_id.is_not(None)))}

    def lookup(row: dict[str, Any]) -> tuple[Waterbody | None, str] | None:
        water = re.sub(r"\s+at\s+.*$", "", row["water"]).strip()
        ids = by_name_county.get((_words(water), (row.get("county") or "").lower()), set())
        # CDFW maps some lakes as several polygons (Clear Lake's basins);
        # they count as one when they all became the same lake here.
        lakes = {by_dfg[i].id: by_dfg[i] for i in ids if i in by_dfg}
        if ids and len(lakes) == 1 and len(ids) == len([i for i in ids if i in by_dfg]):
            return next(iter(lakes.values())), "name and county"
        return None

    return lookup


def run(db: Session, state_code: str, cache: Path, now: datetime | None = None, cdfw_cache: Path = Path("cdfw_cache")) -> dict[str, ImportSummary]:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    state = db.scalar(select(State).where(State.code == state_code))
    if state is None:
        raise ValueError(f"No {state_code} lakes in the database.")
    names = LakeNames(list(db.scalars(select(Waterbody).where(Waterbody.state_id == state.id))))
    if state_code == "TX":
        return import_texas(db, names, cache, now)
    if state_code == "GA":
        data = json.loads((cache / "ga_records.json").read_text(encoding="utf-8"))
        rec = source_record(db, "ga_records", _fetched(data, now))
        return {"ga_records": import_list(
            db, names, data["rows"], source="ga_records", url=GA_URL, rec=rec, now=now,
            sentence="Georgia WRD's state record list includes a {species} from this lake{when}.")}
    if state_code == "CA":
        data = json.loads((cache / "ca_records.json").read_text(encoding="utf-8"))
        rows = [r for r in data["rows"] if "fresh" in (r.get("fishing_type") or "").lower()]
        rec = source_record(db, "ca_records", _fetched(data, now))
        return {"ca_records": import_list(
            db, names, rows, source="ca_records", url=CA_URL, rec=rec, now=now,
            county_lookup=_ca_county_lookup(db, state, cdfw_cache),
            sentence="CDFW's angling records include a {species} from this lake{when}.")}
    raise ValueError(f"No record list wired for {state_code}")


def main(argv: list[str] | None = None) -> int:
    from app.db.session import SessionLocal, engine
    from app.db.upgrades import prepare_database

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", help="TX, GA or CA")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--fetch-tpwd", action="store_true", help="fetch TPWD's water body record pages (facts only)")
    ap.add_argument("--cdfw-cache", type=Path, default=Path("cdfw_cache"),
                    help="California: CDFW's lake layer, to match a record by name and county")
    args = ap.parse_args(argv)
    if args.fetch_tpwd:
        fetch_tpwd(args.cache)
    if not args.state:
        return 0
    prepare_database(engine)
    with SessionLocal() as db:
        results = run(db, args.state.upper(), args.cache, cdfw_cache=args.cdfw_cache)
        db.commit()
    for source, s in results.items():
        print(f"{source}: {s.read} records read, {s.matched} matched to a lake, "
              f"{s.evidence_total} species evidence ({s.evidence_new} new), "
              f"{s.species_skipped} with a fish not mapped, {len(s.unmatched)} unmatched:")
        for line in s.unmatched:
            print(f"  - {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
