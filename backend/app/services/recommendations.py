"""Assembles scored spot candidates for a waterbody (PRD §9's
POST /api/recommendations, built on the §5.2 scoring engine).

Design note — why candidates are computed per request rather than stored:
the PRD's data-model table lists `SpotCandidate` as a table with
`score`/`confidence` columns, but two of the five scoring factors (weather,
freshness) change on their own without anything in this database changing.
A persisted score would be wrong within the hour and there's nothing to
invalidate it against. So a candidate is computed on demand from the one
thing that *is* stable — a confirmed-public AccessPoint — combined with
live weather. If a later phase needs candidates that outlive a request
(precomputed rankings, A/B-testing weight changes, "why did it rank this
way last Tuesday"), the table earns its place then, and would need to store
the weather snapshot each score was computed from.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.waterbody import AccessPoint, Species, Waterbody, WaterbodySpecies
from app.services import scoring
from app.services.weather_adapter import WeatherSnapshot, get_weather


class WaterbodyNotFound(Exception):
    pass


def _species_confidence_tier(
    db: Session, waterbody_id: int, target_species: str | None
) -> str | None:
    """Returns the per-lake evidence tier for the target species, '' when a
    species was requested but has no record in this lake, or None when no
    species was requested at all.

    The empty-string-vs-None distinction is load-bearing: no request means
    the signal is absent (drop the factor), while a requested species with
    no local evidence is a real, scoreable negative.
    """
    if target_species is None:
        return None

    link = db.execute(
        select(WaterbodySpecies)
        .join(Species, WaterbodySpecies.species_id == Species.id)
        .where(
            WaterbodySpecies.waterbody_id == waterbody_id,
            Species.common_name == target_species,
        )
    ).scalar_one_or_none()

    return link.confidence if link is not None else ""


def _freshness_date(
    db: Session, waterbody: Waterbody, target_species: str | None
) -> datetime | None:
    """Freshness follows the most specific evidence backing this
    recommendation: the species record when one was requested, otherwise the
    lake's own last source update."""
    if target_species is not None:
        link = db.execute(
            select(WaterbodySpecies)
            .join(Species, WaterbodySpecies.species_id == Species.id)
            .where(
                WaterbodySpecies.waterbody_id == waterbody.id,
                Species.common_name == target_species,
            )
        ).scalar_one_or_none()
        if link is not None:
            return link.observed_at
    return waterbody.source_updated_at


def build_recommendations(
    db: Session,
    waterbody_id: int,
    target_species: str | None = None,
    limit: int = 5,
    weather: WeatherSnapshot | None = None,
) -> dict:
    """Scores every confirmed-public access point on a waterbody and returns
    them ranked. `weather` is injectable so tests (and any future caller
    with a snapshot already in hand) don't have to go through the adapter."""
    waterbody = db.get(Waterbody, waterbody_id)
    if waterbody is None:
        raise WaterbodyNotFound(f"no waterbody with id {waterbody_id}")

    snapshot = weather or get_weather(waterbody.latitude, waterbody.longitude)

    # PRD §12 acceptance criterion: never present an unconfirmed private
    # area as a public access point. Filtering here (rather than relying on
    # the access factor scoring it 0) means such a point can never appear in
    # a recommendation at all, however the weights are later tuned.
    access_points = list(
        db.execute(
            select(AccessPoint).where(
                AccessPoint.waterbody_id == waterbody_id,
                AccessPoint.public_status == "confirmed_public",
            )
        ).scalars()
    )

    species_tier = _species_confidence_tier(db, waterbody_id, target_species)
    freshness_date = _freshness_date(db, waterbody, target_species)

    weather_factor = scoring.score_weather(snapshot)
    species_factor = scoring.score_species_match(species_tier)
    freshness_factor = scoring.score_freshness(freshness_date)

    candidates = []
    for point in access_points:
        factors = [
            scoring.score_access(point.public_status, point.access_type, point.parking),
            weather_factor,
            species_factor,
            freshness_factor,
        ]
        scored = scoring.combine_factors(factors)
        candidates.append(
            {
                "access_point_id": point.id,
                "name": point.name,
                "latitude": point.latitude,
                "longitude": point.longitude,
                "access_type": point.access_type,
                "public_access_status": point.public_status,
                "score": scored.score,
                "confidence": scored.confidence,
                "factors": [
                    {
                        "name": f.name,
                        "weight": f.weight,
                        "value": f.value,
                        "reason": f.reason,
                    }
                    for f in scored.factors
                ],
                "missing_signals": scored.missing_signals,
            }
        )

    # Ties on score fall back to confidence, so a fully-evidenced spot ranks
    # above an equally-scoring one we know less about.
    candidates.sort(key=lambda c: (c["score"], c["confidence"]), reverse=True)

    window = scoring.best_time_window(snapshot)
    bites = scoring.bite_windows(snapshot)

    return {
        "waterbody_id": waterbody.id,
        "waterbody_name": waterbody.name,
        "target_species": target_species,
        "candidates": candidates[:limit],
        "best_time_window": (
            {
                "start_time": window.start_time,
                "end_time": window.end_time,
                "reason": window.reason,
            }
            if window
            else None
        ),
        # The morning and evening bite, each its own best block (see
        # scoring.bite_windows); what the UI shows.
        "bite_windows": [
            {
                "start_time": w.start_time,
                "end_time": w.end_time,
                "reason": w.reason,
                "label": w.label,
                "score": w.score,
            }
            for w in bites
        ],
        "safety_warnings": [
            {"event": a.event, "severity": a.severity, "headline": a.headline}
            for a in snapshot.alerts
        ],
        "weather_source": snapshot.source,
        "generated_at": datetime.now(timezone.utc),
    }
