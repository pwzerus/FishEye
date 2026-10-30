"""Lake reports: "something's wrong with this lake" and "a lake is
missing" (ADR 0039). Anyone may send one; an admin checks it against a
source and fixes the data by hand, or dismisses it. Nothing here edits a
lake: a report is a person's claim, and the map's facts come from sources.
"""
from __future__ import annotations

import math

from sqlalchemy.orm import Session

from app.db.types import utcnow
from app.models.community import REPORT_OPEN, REPORT_RESOLVED, LakeReport, User
from app.models.waterbody import State, Waterbody
from app.services import counties

REASONS: dict[str, str] = {
    "wrong_location": "It's in the wrong place",
    "not_public": "It isn't open to the public",
    "wrong_fish": "The fish listed are wrong",
    "wrong_name": "The name is wrong",
    "gone": "There's no water here",
    "other": "Something else",
}
MISSING = "missing"
MISSING_LABEL = "A lake that's missing from the map"
RESOLUTIONS = ("fixed", "dismissed")


class LakeReportError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def reason_label(reason: str) -> str:
    return MISSING_LABEL if reason == MISSING else REASONS.get(reason, reason)


def _text(value: str | None, max_len: int) -> str | None:
    value = " ".join((value or "").split())
    if len(value) > max_len:
        raise LakeReportError(422, f"Keep it under {max_len} characters.")
    return value or None


def create(
    db: Session,
    reporter: User | None,
    *,
    reason: str,
    waterbody_id: int | None = None,
    name: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    detail: str | None = None,
) -> LakeReport:
    detail = _text(detail, 1000)
    if reason == MISSING:
        name = _text(name, 120)
        if not name or len(name) < 2:
            raise LakeReportError(422, "Give the lake's name.")
        if latitude is None or longitude is None or not (math.isfinite(latitude) and math.isfinite(longitude)):
            raise LakeReportError(422, "Put the map on the lake first.")
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise LakeReportError(422, "That location isn't valid.")
        county = counties.county_at(latitude, longitude)
        report = LakeReport(
            reason=MISSING, name=name, latitude=round(latitude, 5), longitude=round(longitude, 5),
            state_code=county.state if county else None, detail=detail,
        )
    else:
        if reason not in REASONS:
            raise LakeReportError(422, "Pick what's wrong.")
        lake = db.get(Waterbody, waterbody_id) if waterbody_id else None
        if lake is None:
            raise LakeReportError(404, "No such lake.")
        if reason == "other" and not detail:
            raise LakeReportError(422, "Say what's wrong.")
        state = db.get(State, lake.state_id)
        report = LakeReport(reason=reason, waterbody_id=lake.id, state_code=state.code if state else None, detail=detail)
    report.reporter_id = reporter.id if reporter else None
    report.status = REPORT_OPEN
    db.add(report)
    db.flush()
    return report


def resolve(report: LakeReport, admin: User, resolution: str) -> None:
    if resolution not in RESOLUTIONS:
        raise LakeReportError(422, "Resolve as fixed or dismissed.")
    if report.status == REPORT_RESOLVED:
        raise LakeReportError(409, "This report is already resolved.")
    report.status = REPORT_RESOLVED
    report.resolution = resolution
    report.resolved_by_id = admin.id
    report.resolved_at = utcnow()
