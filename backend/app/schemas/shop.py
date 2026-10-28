from pydantic import BaseModel


class ShopOut(BaseModel):
    id: int
    name: str
    kind: str  # "bait" | "tackle" | "store"
    latitude: float
    longitude: float
    address: str | None
    phone: str | None
    website: str | None
    opening_hours: str | None
    osm_url: str
    # Straight-line, from the point asked about (/api/shops/near only).
    distance_km: float | None = None
