"""Seed data for the 3 friend-field-test lakes (PRD §12.1) plus enough
species/gear data to exercise the whole pipeline end to end.

IMPORTANT — this is hand-curated demo data, not a live scrape. Coordinates
and general species reputations are real and easy to verify publicly, but
`source_url` / `source_updated_at` here are placeholders for where a real
TPWD import job would point. Treat every row as "needs verification before
being shown as fact to a real angler" — which is exactly the distinction
the app is supposed to make between AI-confident and source-confirmed.
See docs/PRD.md §6 and the "政府数据格式不统一" risk in §13.

Run:
    python -m app.data_import.seed_tx_lakes
"""
from datetime import datetime, timezone

from app.db.session import Base, SessionLocal, engine
from app.models.waterbody import (
    AccessPoint,
    Species,
    SpeciesCondition,
    State,
    Waterbody,
    WaterbodySpecies,
)

NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(State).first():
            print("Seed data already present — skipping. Drop the DB to re-seed.")
            return

        tx = State(
            name="Texas",
            code="TX",
            official_source_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/",
        )
        db.add(tx)
        db.flush()

        bass = Species(
            common_name="Largemouth Bass",
            scientific_name="Micropterus salmoides",
            difficulty="beginner",
            profile=(
                "The default beginner target in Texas freshwater. Ambush predator; "
                "holds near cover (vegetation, laydowns, rock) rather than open water."
            ),
        )
        catfish = Species(
            common_name="Channel Catfish",
            scientific_name="Ictalurus punctatus",
            difficulty="beginner",
            profile=(
                "Bottom-oriented, scent-driven feeder. Forgiving for beginners — "
                "wide bait tolerance, active day or night."
            ),
        )
        striper = Species(
            common_name="Striped Bass",
            scientific_name="Morone saxatilis",
            difficulty="intermediate",
            profile=(
                "Open-water schooling predator that follows shad. Rewarding but "
                "less forgiving for a first-timer than bass or catfish."
            ),
        )
        db.add_all([bass, catfish, striper])
        db.flush()

        db.add_all(
            [
                SpeciesCondition(
                    species_id=bass.id,
                    season="spring",
                    temperature_range="60-75F",
                    weather_preferences="stable pressure, light wind, overcast favors shallow feeding",
                    habitat_rules="shallow vegetation and laydowns during pre-spawn/spawn",
                ),
                SpeciesCondition(
                    species_id=bass.id,
                    season="summer",
                    temperature_range="75-90F",
                    weather_preferences="early morning/late evening, wind-blown banks push baitfish in",
                    habitat_rules="deeper structure midday, shallow cover at low light",
                ),
                SpeciesCondition(
                    species_id=catfish.id,
                    season="summer",
                    temperature_range="70-90F",
                    weather_preferences="active regardless of pressure; post-rain runoff often triggers feeding",
                    habitat_rules="channel edges, flats near deep water, current breaks below dams",
                ),
                SpeciesCondition(
                    species_id=striper.id,
                    season="fall",
                    temperature_range="55-70F",
                    weather_preferences="watch for surfacing/schooling activity, especially early morning",
                    habitat_rules="open water over creek channels, follows shad schools",
                ),
            ]
        )

        lakes = [
            dict(
                name="Lake Fork",
                latitude=32.8065,
                longitude=-95.5931,
                access_summary=(
                    "Reservoir in Wood/Rains/Hopkins counties, widely known as Texas's "
                    "premier trophy largemouth bass lake. Multiple public boat ramps and "
                    "bank-access parks around the shoreline."
                ),
                field_tested=True,
                species=[(bass, "confirmed"), (catfish, "reported")],
                access_points=[
                    ("Lake Fork Dam Bank Access", 32.8330, -95.5670, "bank", True),
                    ("Oak Ridge Park", 32.8110, -95.5460, "park", True),
                ],
            ),
            dict(
                name="Lake Travis",
                latitude=30.4183,
                longitude=-97.9192,
                access_summary=(
                    "Highland Lake near Austin on the Colorado River. Deep, clear, "
                    "rocky-shored reservoir; several county/city parks with bank and "
                    "pier access near the dam."
                ),
                field_tested=True,
                species=[(striper, "confirmed"), (bass, "confirmed"), (catfish, "reported")],
                access_points=[
                    ("Mansfield Dam Park", 30.3924, -97.9048, "park", True),
                    ("Windy Point Park", 30.3841, -97.9364, "park", True),
                ],
            ),
            dict(
                name="Richland-Chambers Reservoir",
                latitude=31.9280,
                longitude=-96.2530,
                access_summary=(
                    "Large reservoir southeast of Corsicana. Extensive flats and "
                    "creek-channel structure; multiple public marinas with bank access."
                ),
                field_tested=True,
                species=[(catfish, "confirmed"), (bass, "reported")],
                access_points=[
                    ("Fiesta Marina Access", 31.9700, -96.2200, "bank", True),
                    ("Wildlife Trace Park", 31.9050, -96.2700, "park", True),
                ],
            ),
        ]

        for lake in lakes:
            wb = Waterbody(
                state_id=tx.id,
                name=lake["name"],
                latitude=lake["latitude"],
                longitude=lake["longitude"],
                access_summary=lake["access_summary"],
                source_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/",
                source_updated_at=NOW,
                field_tested=lake["field_tested"],
            )
            db.add(wb)
            db.flush()

            for species_obj, confidence in lake["species"]:
                db.add(
                    WaterbodySpecies(
                        waterbody_id=wb.id,
                        species_id=species_obj.id,
                        confidence=confidence,
                        evidence="TPWD lake page species listing (seed placeholder — verify before production use)",
                        source_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/",
                        observed_at=NOW,
                    )
                )

            for name, lat, lng, atype, parking in lake["access_points"]:
                db.add(
                    AccessPoint(
                        waterbody_id=wb.id,
                        name=name,
                        latitude=lat,
                        longitude=lng,
                        access_type=atype,
                        public_status="confirmed_public",
                        parking=parking,
                    )
                )

        db.commit()
        print(f"Seeded {len(lakes)} waterbodies, {len([bass, catfish, striper])} species.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
