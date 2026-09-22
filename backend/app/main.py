from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, states, waterbodies
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Map-based fishing decision assistant. See /docs for the interactive "
        "API explorer. This backend intentionally treats the LLM as one "
        "component among several, not the source of truth — see "
        "app/services/ai_advisor.py once Day 3 lands."
    ),
    version="0.1.0",
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
