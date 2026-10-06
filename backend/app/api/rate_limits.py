"""Request limits for the endpoints anyone can call without an account.

Each `Budget` is one allowance, shared by every endpoint that spends it, and
is attached to a route as a dependency (`dependencies=[Depends(LLM)]`). A
request over budget gets 429 with `Retry-After`, before the endpoint does
any work. See docs/adr/0021-rate-limits-on-anonymous-endpoints.md for the
numbers and why each group exists.

The client is identified by IP address. Behind the production proxy that is
only correct when uvicorn trusts the proxy's X-Forwarded-For header
(FORWARDED_ALLOW_IPS in docker-compose.prod.yml); otherwise every visitor
arrives from the proxy's address and shares one allowance.

Same scope caveat as RateLimiter itself: counts live in this process. One
server process is what this project runs; several would each count alone.
"""
# No `from __future__ import annotations` here: FastAPI reads the type of
# Budget.__call__'s `request` parameter at run time, and can't resolve a
# string annotation on a callable instance.
from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.core.security import RateLimiter

# The key for an allowance shared by everyone.
EVERYONE = "*"


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class Budget:
    """Per-client limits, plus optional limits on everyone combined.

    Every limit is checked before any is counted, so a refused request uses
    up nothing: a client that is over its own limit can't drain the shared
    one by retrying.
    """

    def __init__(
        self,
        name: str,
        per_client: list[RateLimiter],
        everyone: list[RateLimiter] | None = None,
        busy_message: str = "That's a lot of requests in a short time. Please wait a moment and try again.",
        exhausted_message: str = "This feature is at its limit for now. Please try again later.",
    ) -> None:
        self.name = name
        self.per_client = per_client
        self.everyone = everyone or []
        self.busy_message = busy_message
        self.exhausted_message = exhausted_message

    def __call__(self, request: Request) -> None:
        if not get_settings().rate_limits_enabled:
            return
        key = client_ip(request)
        own_wait = max((lim.blocked_for(key) for lim in self.per_client), default=0.0)
        shared_wait = max((lim.blocked_for(EVERYONE) for lim in self.everyone), default=0.0)
        if own_wait > 0 or shared_wait > 0:
            message = self.busy_message if own_wait > 0 else self.exhausted_message
            raise HTTPException(
                status_code=429,
                detail=message,
                headers={"Retry-After": str(int(max(own_wait, shared_wait)) + 1)},
            )
        for lim in self.per_client:
            lim.hit(key)
        for lim in self.everyone:
            lim.hit(EVERYONE)

    def reset(self) -> None:
        for lim in (*self.per_client, *self.everyone):
            lim.reset()


MINUTE = 60.0
DAY = 24 * 60 * 60.0

# Guide Q&A and the advisor: the endpoints that call a language model, so
# the ones that will cost money once a real model is switched on. The daily
# total across everyone bounds that cost whatever the number of clients.
LLM = Budget(
    "llm",
    per_client=[RateLimiter(10, MINUTE), RateLimiter(100, DAY)],
    everyone=[RateLimiter(2000, DAY)],
    exhausted_message=(
        "The AI features have reached today's limit for everyone. "
        "The fish guides and the map still work; please try again tomorrow."
    ),
)

# Location search. Nominatim allows this app one request a second in total,
# and the service queues to respect that, so one client's flood would make
# everyone else's search wait.
GEOCODE = Budget("geocode", per_client=[RateLimiter(20, MINUTE)])

# Weather and spot recommendations: both may call the National Weather
# Service (cached per place for 15 minutes, so a flood of new places is what
# reaches it).
WEATHER = Budget("weather", per_client=[RateLimiter(60, MINUTE)])

# The map's lake queries: database only, and the map asks again on every pan
# and zoom, so the allowance is generous. It is here so that one client
# can't keep the database busy for everyone.
MAP = Budget("map", per_client=[RateLimiter(300, MINUTE)])

ALL = (LLM, GEOCODE, WEATHER, MAP)


def reset_all() -> None:
    for budget in ALL:
        budget.reset()
