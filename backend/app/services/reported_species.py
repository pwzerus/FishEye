"""What outside records say about a lake's fish: the "reported" tier.

Reads SpeciesOccurrence (GBIF records, see
app/data_import/gbif_occurrence_import.py) and summarises it per species:
how many records, the most recent year, and who recorded them. Nothing here
feeds scoring or the AI advisor; those read only official, confirmed species
(WaterbodySpecies). See docs/adr/0012-gbif-reported-species.md.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.waterbody import SpeciesOccurrence
from app.schemas.waterbody import ReportedSourceOut, ReportedSpeciesOut

# Licences that allow commercial use. See docs/commercialization.md.
COMMERCIAL_LICENSES = ("CC0", "CC BY")

# One record from before this year (or undated) is shown, but flagged as weak
# evidence: a single 1960s museum specimen says little about the lake today.
WEAK_BEFORE_YEAR = 2000

SOURCE_LABELS = {
    "fishes_of_texas": "Fishes of Texas (UT Austin)",
    "inaturalist": "iNaturalist",
    "tpwd": "Texas Parks & Wildlife",
    "other": "Other museums and surveys",
}


def _licensed(stmt: Select) -> Select:  # type: ignore[type-arg]
    if get_settings().gbif_exclude_noncommercial:
        return stmt.where(SpeciesOccurrence.license.in_(COMMERCIAL_LICENSES))
    return stmt


def _record_url(source: str, record_id: str) -> str | None:
    if source == "gbif":
        return f"https://www.gbif.org/occurrence/{record_id}"
    return None


def reported_species(db: Session, waterbody_id: int, confirmed: Iterable[str] = ()) -> list[ReportedSpeciesOut]:
    """Per-species summary for one lake, most-recorded first. `confirmed`
    names the species an official source confirms here, so the UI can tell
    "also confirmed" apart from "only reported"."""
    confirmed_set = set(confirmed)
    rows = db.execute(
        _licensed(
            select(
                SpeciesOccurrence.species_name,
                SpeciesOccurrence.year,
                SpeciesOccurrence.source_group,
                SpeciesOccurrence.source,
                SpeciesOccurrence.source_record_id,
            ).where(SpeciesOccurrence.waterbody_id == waterbody_id)
        )
    ).all()

    by_species: dict[str, list] = defaultdict(list)  # type: ignore[type-arg]
    for row in rows:
        by_species[row.species_name].append(row)

    out: list[ReportedSpeciesOut] = []
    for name, recs in by_species.items():
        years = [r.year for r in recs if r.year is not None]
        last_year = max(years) if years else None
        latest = max(recs, key=lambda r: (r.year is not None, r.year or 0))
        groups = Counter(r.source_group for r in recs)
        out.append(
            ReportedSpeciesOut(
                common_name=name,
                records=len(recs),
                last_year=last_year,
                sources=[
                    ReportedSourceOut(name=SOURCE_LABELS.get(g, g), records=n) for g, n in groups.most_common()
                ],
                latest_record_url=_record_url(latest.source, latest.source_record_id),
                weak=len(recs) == 1 and (last_year is None or last_year < WEAK_BEFORE_YEAR),
                also_confirmed=name in confirmed_set,
            )
        )
    out.sort(key=lambda s: (-s.records, s.common_name))
    return out


def reported_species_counts(db: Session, waterbody_ids: Iterable[int]) -> dict[int, int]:
    """Number of distinct reported species per lake, for map markers."""
    ids = list(waterbody_ids)
    if not ids:
        return {}
    stmt = _licensed(
        select(SpeciesOccurrence.waterbody_id, func.count(func.distinct(SpeciesOccurrence.species_name)))
        .where(SpeciesOccurrence.waterbody_id.in_(ids))
        .group_by(SpeciesOccurrence.waterbody_id)
    )
    return {wb_id: int(n) for wb_id, n in db.execute(stmt).all()}
