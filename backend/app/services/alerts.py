"""An email when someone confirms a fish near you (docs/adr/0054).

Someone picks a fish, a place and how far from it they care about. When a public
catch of that fish goes up inside that distance and its photo check backs it,
they get one email. What the email says is what the catch's page says to
anyone: the water or county, never the spot and never who caught it. Distance
is measured to the same public point, so alerts can't be used to pin down a
spot its angler kept to themselves.

Only to confirmed addresses: otherwise anyone could sign up with someone
else's address and send them mail. At most one email per alert per
COOLDOWN, and every email has its own unsubscribe link.
"""
from __future__ import annotations

import logging
import math
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.types import utcnow
from app.models.community import PIN_PUBLISHED, USER_ACTIVE, VISIBILITY_PUBLIC, CatchPin, SpeciesAlert, User
from app.models.water import River
from app.models.waterbody import Waterbody
from app.services import fish_id, mail
from app.services.geo import haversine_km
from app.services.pins import SPECIES_LABELS, PinError, _text
from app.services.rag.retriever import ZH_SPECIES_ALIASES

MAX_PER_USER = 10
MIN_RADIUS, MAX_RADIUS = 1, 500
COOLDOWN = timedelta(hours=12)
# One catch can't start an unbounded run of sends.
MAX_NOTICES = 200
KM_PER_MILE = 1.609344
LANGS = ("en", "zh", "es", "ko", "ja")

logger = logging.getLogger(__name__)


def can_be_emailed(user: User) -> bool:
    return user.email_verified_at is not None


def sending() -> bool:
    """Whether mail really leaves the server (services/mail.py)."""
    return get_settings().mail_backend == "smtp"


def alerts_of(db: Session, user: User) -> list[SpeciesAlert]:
    return list(db.scalars(select(SpeciesAlert).where(SpeciesAlert.user_id == user.id).order_by(SpeciesAlert.created_at, SpeciesAlert.id)))


def create(
    db: Session, user: User, species_slug: str, latitude: float, longitude: float, place: str, radius_miles: int, lang: str | None
) -> SpeciesAlert:
    if species_slug not in SPECIES_LABELS:
        raise PinError(422, "Pick a fish.")
    if not (math.isfinite(latitude) and math.isfinite(longitude) and -90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise PinError(422, "That location isn't valid.")
    if not MIN_RADIUS <= radius_miles <= MAX_RADIUS:
        raise PinError(422, f"Pick a distance from {MIN_RADIUS} to {MAX_RADIUS} miles.")
    label = _text(place, 120)
    if not label:
        raise PinError(422, "Pick a place.")
    if len(alerts_of(db, user)) >= MAX_PER_USER:
        raise PinError(409, f"You can have up to {MAX_PER_USER} alerts. Delete one first.")
    alert = SpeciesAlert(
        user_id=user.id,
        species_slug=species_slug,
        # About a kilometre: enough for "within 30 miles", and not someone's front door.
        latitude=round(latitude, 2),
        longitude=round(longitude, 2),
        place=label,
        radius_miles=radius_miles,
        lang=lang if lang in LANGS else "en",
        token=secrets.token_urlsafe(32),
    )
    db.add(alert)
    db.flush()
    return alert


def delete(db: Session, user: User, alert_id: int) -> None:
    alert = db.get(SpeciesAlert, alert_id)
    if alert is None or alert.user_id != user.id:
        raise PinError(404, "No such alert.")
    db.delete(alert)


def unsubscribe(db: Session, token: str) -> SpeciesAlert:
    """From the link in an email, with no sign-in: the token is the proof."""
    alert = db.scalar(select(SpeciesAlert).where(SpeciesAlert.token == token))
    if alert is None:
        raise PinError(404, "That link has already been used, or the alert is gone.")
    db.delete(alert)
    return alert


# ---------------------------------------------------------------- notices


@dataclass(frozen=True)
class Notice:
    to: str
    subject: str
    text: str


def _fish_name(slug: str, lang: str) -> str:
    english = SPECIES_LABELS.get(slug, slug)
    if lang == "zh":
        return next((alias for alias, slugs in ZH_SPECIES_ALIASES.items() if slugs == (slug,)), english)
    return english


def _where(db: Session, pin: CatchPin) -> str:
    """The name its page gives everyone: the water, else the county."""
    if pin.waterbody_id and (lake := db.get(Waterbody, pin.waterbody_id)):
        return lake.name
    if pin.river_id and (river := db.get(River, pin.river_id)):
        return river.name
    if pin.county_name:
        return f"{pin.county_name}, {pin.state_code}" if pin.state_code else pin.county_name
    return pin.state_code or ""


_WORDS = {
    "en": (
        lambda fish, where: f"A {fish} was caught near you: {where}",
        lambda fish, where, miles, url, off: (
            f"Someone shared a {fish} at {where}, and the photo check backs it. That's about {miles} miles from the place in your alert.\n\n"
            f"See the catch: {url}\n\nYou get this because you set a catch alert on FishEye. To stop this alert: {off}\n"
        ),
    ),
    "zh": (
        lambda fish, where: f"附近有人钓到了{fish}：{where}",
        lambda fish, where, miles, url, off: (
            f"有人在{where}分享了一条{fish}，照片也核对过了。距离你设的提醒地点大约 {miles} 英里。\n\n"
            f"查看这条渔获：{url}\n\n你收到这封邮件，是因为你在 FishEye 设置了鱼讯提醒。不想再收到这条提醒：{off}\n"
        ),
    ),
    "es": (
        lambda fish, where: f"Captura cerca de ti: {fish} en {where}",
        lambda fish, where, miles, url, off: (
            f"Alguien compartió un {fish} en {where}, y la revisión de la foto lo confirma. Está a unas {miles} millas del lugar de tu alerta.\n\n"
            f"Ver la captura: {url}\n\nRecibes esto porque creaste una alerta de capturas en FishEye. Para cancelarla: {off}\n"
        ),
    ),
    "ko": (
        lambda fish, where: f"근처 조과 알림: {where}에서 {fish}",
        lambda fish, where, miles, url, off: (
            f"누군가 {where}에서 잡은 {fish}를 공유했고 사진 확인도 통과했어요. 알림에 설정한 장소에서 약 {miles}마일 떨어져 있어요.\n\n"
            f"조과 보기: {url}\n\nFishEye에서 조과 알림을 설정해서 이 메일을 받았어요. 이 알림 그만 받기: {off}\n"
        ),
    ),
    "ja": (
        lambda fish, where: f"近くの釣果：{where}で{fish}",
        lambda fish, where, miles, url, off: (
            f"{where}で釣れた{fish}が投稿され、写真の確認も通りました。アラートの場所から約{miles}マイルです。\n\n"
            f"釣果を見る：{url}\n\nFishEyeで釣果アラートを設定しているため、このメールが届いています。このアラートを止める：{off}\n"
        ),
    ),
}


def notices_for(db: Session, pin: CatchPin) -> list[Notice]:
    """Who to tell about this catch, marking them told. Sending is separate
    (`send`), after the response: a mail server shouldn't hold up a post."""
    if (
        pin.visibility != VISIBILITY_PUBLIC
        or pin.status != PIN_PUBLISHED
        or not pin.species_slug
        or pin.species_check not in (fish_id.CONFIRMED, fish_id.GROUP)
        or pin.public_latitude is None
        or pin.public_longitude is None
    ):
        return []
    now = utcnow()
    site = get_settings().frontend_origin.rstrip("/")
    where = _where(db, pin)
    found: list[Notice] = []
    alerts = db.scalars(
        select(SpeciesAlert)
        .options(selectinload(SpeciesAlert.user))
        .where(SpeciesAlert.species_slug == pin.species_slug, SpeciesAlert.user_id != pin.user_id)
    )
    for alert in alerts:
        if len(found) >= MAX_NOTICES:
            logger.warning("Catch %s reached the limit of %s alert emails.", pin.id, MAX_NOTICES)
            break
        user = alert.user
        if user.status != USER_ACTIVE or not can_be_emailed(user):
            continue
        if alert.last_sent_at is not None and now - alert.last_sent_at < COOLDOWN:
            continue
        km = haversine_km(alert.latitude, alert.longitude, pin.public_latitude, pin.public_longitude)
        miles = km / KM_PER_MILE
        if miles > alert.radius_miles:
            continue
        subject, body = _WORDS[alert.lang if alert.lang in _WORDS else "en"]
        fish = _fish_name(pin.species_slug, alert.lang)
        found.append(
            Notice(
                user.email,
                subject(fish, where),
                body(fish, where, max(1, round(miles)), f"{site}/community/{pin.id}", f"{site}/unsubscribe?token={alert.token}"),
            )
        )
        alert.last_sent_at = now
    return found


def send(notices: list[Notice]) -> None:
    for notice in notices:
        try:
            mail.send(notice.to, notice.subject, notice.text)
        except mail.MailError:
            # Logged by mail.send. The rest still go.
            continue
