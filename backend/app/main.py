from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    admin,
    admin_community,
    advisor,
    ask,
    auth,
    geocode,
    pins,
    recommendations,
    species,
    states,
    waterbodies,
    weather,
)
from app.core.config import get_settings
from app.db.session import Base, engine
from app.db.spatial import ensure_spatial_schema

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Creates tables added since the database was built (e.g.
    # species_occurrences) so an existing dev database keeps working without
    # a rebuild. create_all never alters or drops an existing table; there
    # are no migrations yet (see backend/README.md).
    import app.models  # noqa: F401  (register every model)

    Base.metadata.create_all(bind=engine)
    # On PostgreSQL this adds the PostGIS geography column and its GiST
    # index, and decides whether the map's viewport queries may use them.
    # A no-op on SQLite (app/db/spatial.py explains the two shapes).
    ensure_spatial_schema(engine)
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
# arbitrarily large upload. Uploads go only to /api/pins; nothing else
# accepts bodies anywhere near this size.
MAX_UPLOAD_BODY = settings.max_photos_per_pin * settings.max_photo_bytes + 1024 * 1024
MAX_OTHER_BODY = 256 * 1024


@app.middleware("http")
async def limit_body_size(request: Request, call_next):  # type: ignore[no-untyped-def]
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        limit = MAX_UPLOAD_BODY if request.url.path.startswith(f"{settings.api_prefix}/pins") else MAX_OTHER_BODY
        length = request.headers.get("content-length")
        is_multipart = request.headers.get("content-type", "").startswith("multipart/")
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
                return JSONResponse({"detail": "That upload is too large."}, status_code=413)
    return await call_next(request)


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
app.include_router(ask.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(pins.router, prefix=settings.api_prefix)
app.include_router(admin_community.router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
