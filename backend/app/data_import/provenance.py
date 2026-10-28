"""Where every imported fact came from, and the one way evidence is written.

docs/data-sources.md is the register of sources and their terms; DATASETS
below is its machine-readable half for the sources the importers in this
package write species evidence or lake facts from. Each becomes one
SourceRecord row (found again by its key on every run) carrying the licence
class and the credit the source asks for (data-sourcing rules 1, 2, 6, 7).

`add_evidence` is how every importer records that a species is in a lake:
a SpeciesEvidence row (one per fact, keyed by the source's own id, so a
re-run never duplicates it) with FishEye's own sentence and a link, plus
the lake's one-line WaterbodySpecies summary when it has none yet.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_import.species_names import SPECIES
from app.data_import.tpwd_lake_survey_scraper import upsert_species
from app.models.waterbody import SourceRecord, Species, SpeciesEvidence, Waterbody, WaterbodySource, WaterbodySpecies

BIOS_CITE = "https://www.wildlife.ca.gov/Data/BIOS/Citing-BIOS"

# Data-sourcing rule 5: every fetch says who we are and how to reach us.
USER_AGENT = "FishEye/1.0 (+https://fisheyefishing.com; feedback.fisheyefishing@gmail.com)"


@dataclass(frozen=True)
class Dataset:
    key: str
    title: str
    publisher: str
    url: str
    licence_class: str  # PD | OPEN | RESTRICTED
    licence_name: str
    citation: str
    source_type: str


DATASETS: dict[str, Dataset] = {
    d.key: d
    for d in (
        Dataset(
            "cdfw_ca_lakes", "California Lakes", "California Department of Fish and Wildlife",
            "https://data-cdfw.opendata.arcgis.com/datasets/CDFW::california-lakes",
            "OPEN", "CC BY 4.0",
            "California Lakes. California Department of Fish and Wildlife, Biogeographic Data Branch. "
            "Accessed through CDFW's open data hub (ArcGIS). Licensed CC BY 4.0; cited as BIOS asks: " + BIOS_CITE,
            "cdfw_gis",
        ),
        Dataset(
            "cdfw_ds778", "Recent Stocked Waters - California [ds778]", "California Department of Fish and Wildlife",
            "https://filelib.wildlife.ca.gov/Public/BDB/GIS/BIOS/Public_Datasets/700_799/ds778.zip",
            "OPEN", "CC BY 4.0",
            "Recent Stocked Waters - California [ds778]. California Department of Fish and Wildlife, "
            "GIS Service Center. Published 2014-10-20, updated 2025. Accessed through BIOS. CC BY 4.0. " + BIOS_CITE,
            "cdfw_bios",
        ),
        Dataset(
            "cdfw_ds102", "Fish - High Mountain Lakes [ds102]", "California Department of Fish and Wildlife",
            "https://filelib.wildlife.ca.gov/Public/BDB/GIS/BIOS/Public_Datasets/100_199/ds102.zip",
            "OPEN", "CC BY 4.0",
            "Fish - High Mountain Lakes [ds102]. California Department of Fish and Wildlife (CDFW), "
            "High Mountain Lakes project. Published 2026-07-20. Accessed through BIOS. CC BY 4.0. " + BIOS_CITE,
            "cdfw_bios",
        ),
        Dataset(
            "cdfw_plants", "Fish Planting Schedule", "California Department of Fish and Wildlife",
            "https://nrm.dfg.ca.gov/FishPlants/PublicPlantSearch",
            "PD", "Public domain (CDFW Conditions of Use)",
            "Fish Planting Schedule, California Department of Fish and Wildlife. Exported with the page's own Export button.",
            "cdfw_stocking",
        ),
        Dataset(
            "cdfw_plan_2026", "2026 Provisional Stocking Document for Trout and Inland Salmon",
            "California Department of Fish and Wildlife",
            "https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=74004&inline",
            "PD", "Public domain (CDFW Conditions of Use)",
            "2026 Provisional Stocking Document for Trout and Inland Salmon, California Department of Fish and Wildlife.",
            "cdfw_stocking",
        ),
        Dataset(
            "ca_records", "California Freshwater Angling Records", "California Department of Fish and Wildlife",
            "https://wildlife.ca.gov/Fishing/Records",
            "PD", "Public domain (CDFW Conditions of Use); stored as facts + link",
            "California angling records, California Department of Fish and Wildlife.",
            "state_records",
        ),
        Dataset(
            "usgs_nas", "Nonindigenous Aquatic Species Database", "U.S. Geological Survey",
            "https://nas.er.usgs.gov/", "PD", "Public domain (U.S. federal data)",
            "U.S. Geological Survey. Nonindigenous Aquatic Species Database. Gainesville, Florida. https://nas.er.usgs.gov",
            "usgs_nas",
        ),
        Dataset(
            "padus_4_1", "PAD-US Public Access (Protected Areas Database of the United States)", "U.S. Geological Survey",
            "https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/PADUS_Public_Access/FeatureServer/0",
            "PD", "Public domain (U.S. federal data)",
            "U.S. Geological Survey (USGS) Gap Analysis Project (GAP), 2024, Protected Areas Database of the "
            "United States (PAD-US) 4.1: U.S. Geological Survey data release, https://doi.org/10.5066/P96WBCHS.",
            "padus",
        ),
        Dataset(
            "osm_shops", "OpenStreetMap: fishing and bait shops", "OpenStreetMap contributors",
            "https://download.geofabrik.de/north-america/us/",
            "OPEN", "ODbL 1.0",
            "© OpenStreetMap contributors. Data available under the Open Database License (ODbL 1.0), "
            "read from Geofabrik's state extracts.",
            "osm",
        ),
        Dataset(
            "tpwd_records", "Texas Fish Records: Water Body Records", "Texas Parks and Wildlife Department",
            "https://tpwd.texas.gov/fishboat/fish/programs/fishrecords/recordsearch.phtml",
            "RESTRICTED", "Facts + link (no licence stated)",
            "Data: Texas Parks and Wildlife Department.",
            "state_records",
        ),
        Dataset(
            "sharelunker", "Toyota ShareLunker Archives", "Texas Parks and Wildlife Department",
            "https://texassharelunker.com/archives/",
            "RESTRICTED", "Facts + link (no licence stated)",
            "Data: Texas Parks and Wildlife Department (Toyota ShareLunker program).",
            "state_records",
        ),
        Dataset(
            "ga_records", "State Record Freshwater Fish", "Georgia DNR Wildlife Resources Division",
            "https://georgiawildlife.com/fishing/recordprogram",
            "RESTRICTED", "Facts + link (no licence stated)",
            "Data: Georgia DNR Wildlife Resources Division.",
            "state_records",
        ),
    )
}


def source_record(db: Session, key: str, retrieved_at: datetime) -> SourceRecord:
    """The dataset's SourceRecord row, created or brought up to date."""
    d = DATASETS[key]
    row = db.scalar(select(SourceRecord).where(SourceRecord.source_key == key))
    if row is None:
        row = SourceRecord(source_key=key)
        db.add(row)
    row.source_type = d.source_type
    row.url = d.url
    row.publisher = d.publisher
    row.title = d.title
    row.licence_class = d.licence_class
    row.licence_name = d.licence_name
    row.citation = d.citation
    row.retrieved_at = retrieved_at
    db.flush()
    return row


def species_row(db: Session, name: str) -> Species:
    """The Species row for a canonical name (species_names.SPECIES). Guide
    species get the guide's profile (upsert_species); others their scientific
    name and a neutral profile."""
    species = upsert_species(db, name)
    if not species.scientific_name and name in SPECIES:
        species.scientific_name = SPECIES[name]
    return species


def link_dataset(db: Session, wb: Waterbody, record: SourceRecord, source_key: str | None = None, url: str | None = None) -> None:
    """Note that `record`'s dataset contributed facts about this lake."""
    row = db.get(WaterbodySource, (wb.id, record.id))
    if row is None:
        row = WaterbodySource(waterbody_id=wb.id, source_record_id=record.id)
        db.add(row)
    row.source_key = source_key
    row.url = url


def unlink_dataset(db: Session, record: SourceRecord, keep_lake_ids: set[int]) -> int:
    """Drop this dataset's links to lakes a re-run no longer credits it for."""
    stale = [
        r for r in db.scalars(select(WaterbodySource).where(WaterbodySource.source_record_id == record.id))
        if r.waterbody_id not in keep_lake_ids
    ]
    for r in stale:
        db.delete(r)
    db.flush()
    return len(stale)


_RANK = {"reported": 0, "likely": 1, "confirmed": 2}


def add_evidence(
    db: Session,
    wb: Waterbody,
    species_name: str,
    *,
    source: str,
    source_key: str,
    kind: str,
    year: int | None,
    evidence: str,
    source_url: str,
    record: SourceRecord | None,
    confidence: str,
    now: datetime,
) -> bool:
    """Record one fact that `species_name` is in `wb`. Returns True when the
    fact is new. The lake's WaterbodySpecies row is created if missing, and
    raised to `confidence` if that is stronger; a row another source wrote
    keeps its sentence and link."""
    species = species_row(db, species_name)
    row = db.scalar(
        select(SpeciesEvidence).where(SpeciesEvidence.source == source, SpeciesEvidence.source_key == source_key)
    )
    new = row is None
    if row is None:
        row = SpeciesEvidence(source=source, source_key=source_key)
        db.add(row)
    row.waterbody_id = wb.id
    row.species_id = species.id
    row.source_record_id = record.id if record is not None else None
    row.kind = kind
    row.year = year
    row.evidence = evidence
    row.source_url = source_url
    row.imported_at = now

    link = db.get(WaterbodySpecies, (wb.id, species.id))
    observed = datetime(year, 1, 1) if year else now
    if link is None:
        db.add(
            WaterbodySpecies(
                waterbody_id=wb.id, species_id=species.id, confidence=confidence,
                evidence=evidence, source_url=source_url, observed_at=observed,
            )
        )
    elif _RANK.get(confidence, 0) > _RANK.get(link.confidence, 0):
        link.confidence = confidence
        link.evidence = evidence
        link.source_url = source_url
        link.observed_at = observed
    elif link.source_url == source_url and link.evidence != evidence:
        link.evidence = evidence  # the same source, worded afresh by a later run
    db.flush()
    return new


def prune_evidence(db: Session, source: str, keep_keys: set[str]) -> int:
    """Remove this source's evidence that a re-import no longer produced
    (the source dropped it, or it now matches another lake), and any lake
    species summary that only that evidence stood for."""
    stale = [
        e for e in db.scalars(select(SpeciesEvidence).where(SpeciesEvidence.source == source))
        if e.source_key not in keep_keys
    ]
    for e in stale:
        link = db.get(WaterbodySpecies, (e.waterbody_id, e.species_id))
        db.delete(e)
        db.flush()
        if link is not None and link.source_url == e.source_url and link.evidence == e.evidence:
            others = db.scalars(
                select(SpeciesEvidence).where(
                    SpeciesEvidence.waterbody_id == e.waterbody_id, SpeciesEvidence.species_id == e.species_id
                )
            ).first()
            if others is None:
                db.delete(link)
            else:
                link.evidence, link.source_url = others.evidence, others.source_url
    db.flush()
    return len(stale)
