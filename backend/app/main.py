import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (
    admin,
    admin_community,
    advisor,
    ask,
    auth,
    baits,
    feedback,
    gear,
    geocode,
    jurisdictions,
    lake_reports,
    pins,
    recommendations,
    shops,
    social,
    species,
    states,
    visits,
    waterbodies,
    weather,
)
from app.api.zh_hant import TraditionalChinese
from app.core.config import get_settings
from app.db.session import Base, UnstorableText, engine
from app.db.spatial import ensure_spatial_schema
from app.db.upgrades import ensure_waterbody_ranking_schema
from app.knowledge import error_text

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Creates tables added since the database was built (e.g.
    # species_occurrences) so an existing dev database keeps working without
    # a rebuild. create_all never alters or drops an existing table; there
    # are no migrations yet (see backend/README.md).
    import app.models  # noqa: F401  (register every model)

    Base.metadata.create_all(bind=engine)
    # create_all skips tables that already exist, so a database built before
    # a column or index was added to a model gets it here instead.
    ensure_waterbody_ranking_schema(engine)
    # On PostgreSQL this adds the PostGIS geography column and its GiST
    # index, and decides whether the map's viewport queries may use them.
    # A no-op on SQLite (app/db/spatial.py explains the two shapes).
    ensure_spatial_schema(engine)
    # Catches saved before counties existed get their state and county;
    # those not yet checked against the water shapes (ADR 0040), their
    # water; and those saved before ADR 0038, the point everyone else sees
    # them at.
    from app.db.session import SessionLocal
    from app.services.pins import fill_places, fill_public_points, fill_water

    with SessionLocal() as db:
        fill_places(db)
        fill_water(db)
        fill_public_points(db)
    # Load Ask's search now rather than on the first question: with
    # RAG_SEMANTIC=on (the default) a missing model stops the server here,
    # with instructions, instead of breaking Ask later; and the model and
    # passage vectors are warm before anyone asks (docs/adr/0029).
    if settings.rag_semantic != "off":
        from app.services.rag import question_library
        from app.services.rag.retriever import default_retriever

        retriever = default_retriever()
        question_library.library(getattr(retriever, "embedder", None))
    # New accounts can't share catches until they open the emailed link, so
    # with no mail server every new account is stuck. Said once, at start.
    if settings.email_verification == "on" and settings.mail_backend != "smtp":
        logger.warning(
            "EMAIL_VERIFICATION=on but MAIL_BACKEND=%s: confirmation links are only written to this log, "
            "never emailed. Set MAIL_BACKEND=smtp and the SMTP_* settings to send them.",
            settings.mail_backend,
        )
    yield

app = FastAPI(
    title=settings.app_name,
    description=(
        "Map-based fishing decision assistant. See /docs for the interactive "
        "API explorer. This backend intentionally treats the LLM as one "
        "component among several, not the source of truth — see "
        "app/services/ai_advisor.py once Day 3 lands."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Multipart bodies are parsed before any dependency runs — including
# require_user — so without a cap anyone could make the server buffer an
# arbitrarily large upload. A catch's photos go to /api/pins, and one photo
# to /api/fish-id (the photo check, as sent from a phone: full size);
# nothing else accepts bodies anywhere near these sizes.
MAX_UPLOAD_BODY = settings.max_photos_per_pin * settings.max_photo_bytes + 1024 * 1024
MAX_PHOTO_BODY = settings.max_photo_bytes + 1024 * 1024
MAX_OTHER_BODY = 256 * 1024


def body_limit(path: str, multipart: bool) -> int:
    """Photos come only as multipart uploads; a plain form or JSON sent to
    the same address is small, and gets no room to make the server parse
    megabytes of it (Starlette ignores its own form limits for those)."""
    if multipart and path.startswith(f"{settings.api_prefix}/pins"):
        return MAX_UPLOAD_BODY
    if multipart and path == f"{settings.api_prefix}/fish-id":
        return MAX_PHOTO_BODY
    return MAX_OTHER_BODY


# 繁體中文 ("zht"), answered from the Simplified (api/zh_hant.py). Added
# before the middleware below, so it runs inside them: after the size check.
app.add_middleware(TraditionalChinese)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):  # type: ignore[no-untyped-def]
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        length = request.headers.get("content-length")
        is_multipart = request.headers.get("content-type", "").startswith("multipart/")
        # The path the request is routed by: request.url.path is rebuilt with
        # the Host header, which a client can bend to look like /api/pins.
        limit = body_limit(request.scope["path"], is_multipart)
        # A chunked body has no length to check up front, and browsers never
        # send one for fetch/XHR; refusing it keeps the cap unbypassable.
        if length is None and (is_multipart or "transfer-encoding" in request.headers):
            return JSONResponse({"detail": "Requests need a Content-Length."}, status_code=411)
        if length is not None:
            try:
                too_big = int(length) > limit
            except ValueError:
                return JSONResponse({"detail": "Bad Content-Length."}, status_code=400)
            if too_big:
                detail = error_text.tr("That upload is too large.", request.cookies.get(error_text.LANG_COOKIE))
                return JSONResponse({"detail": detail}, status_code=413)
    return await call_next(request)


# On every API answer; the pages get theirs from frontend/next.config.ts.
# The API is never meant to be framed or sniffed as anything but what it
# says it is. HSTS only with HTTPS (a browser ignores it over HTTP anyway).
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
if settings.frontend_origin.startswith("https://"):
    SECURITY_HEADERS["Strict-Transport-Security"] = "max-age=31536000"


@app.middleware("http")
async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


@app.exception_handler(StarletteHTTPException)
async def refuse_in_their_language(request: Request, exc: StarletteHTTPException):  # type: ignore[no-untyped-def]
    """The site shows a refusal's message as it comes ("Email or password
    is incorrect."), so it is said in the language the visitor chose
    (knowledge/error_text.py); English when it has no translation."""
    lang = request.cookies.get(error_text.LANG_COOKIE)
    if lang and isinstance(exc.detail, str):
        detail = error_text.tr(exc.detail, lang)
        if detail != exc.detail:
            exc = StarletteHTTPException(exc.status_code, detail, exc.headers)
    return await http_exception_handler(request, exc)


UNREADABLE_TEXT = "That has characters FishEye can't read. Check what you typed and try again."


@app.exception_handler(UnstorableText)
async def refuse_unreadable_text(request: Request, _exc: UnstorableText):  # type: ignore[no-untyped-def]
    return await refuse_in_their_language(request, StarletteHTTPException(status_code=422, detail=UNREADABLE_TEXT))


app.add_middleware(
    CORSMiddleware,
    # Credentialed requests (the session cookie) need an explicit origin,
    # never "*".
    allow_origins=[settings.frontend_origin.rstrip("/")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Readable by the frontend's fetch: the re-auth prompt and rate-limit waits.
    expose_headers=["X-Reauth-Required", "Retry-After"],
)

app.include_router(states.router, prefix=settings.api_prefix)
app.include_router(waterbodies.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(weather.router, prefix=settings.api_prefix)
app.include_router(recommendations.router, prefix=settings.api_prefix)
app.include_router(advisor.router, prefix=settings.api_prefix)
app.include_router(geocode.router, prefix=settings.api_prefix)
app.include_router(species.router, prefix=settings.api_prefix)
app.include_router(baits.router, prefix=settings.api_prefix)
app.include_router(feedback.router, prefix=settings.api_prefix)
app.include_router(jurisdictions.router, prefix=settings.api_prefix)
app.include_router(ask.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(pins.router, prefix=settings.api_prefix)
app.include_router(social.router, prefix=settings.api_prefix)
app.include_router(admin_community.router, prefix=settings.api_prefix)
app.include_router(shops.router, prefix=settings.api_prefix)
app.include_router(lake_reports.router, prefix=settings.api_prefix)
app.include_router(visits.router, prefix=settings.api_prefix)
app.include_router(gear.router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
