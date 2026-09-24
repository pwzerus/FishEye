from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, advisor, geocode, recommendations, species, states, waterbodies, weather
from app.core.config import get_settings
from app.db.session import Base, engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Creates tables added since the database was built (e.g.
    # species_occurrences) so an existing dev database keeps working without
    # a rebuild. create_all never alters or drops an existing table; there
    # are no migrations yet (see backend/README.md).
    import app.models  # noqa: F401  (register every model)

    Base.metadata.create_all(bind=engine)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(states.router, prefix=settings.api_prefix)
app.include_router(waterbodies.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(weather.router, prefix=settings.api_prefix)
app.include_router(recommendations.router, prefix=settings.api_prefix)
app.include_router(advisor.router, prefix=settings.api_prefix)
app.include_router(geocode.router, prefix=settings.api_prefix)
app.include_router(species.router, prefix=settings.api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
