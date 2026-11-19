from pydantic import BaseModel


class CoastalSpotOut(BaseModel):
    id: int
    name: str | None
    kind: str  # "pier" | "jetty" | "fishing_spot" | "boat_ramp"
    coast: str  # "atlantic" | "gulf" | "pacific" | "alaska" | "hawaii"
    latitude: float
    longitude: float
    state_code: str
    fishing_tagged: bool
    fee: str | None
    opening_hours: str | None
    lit: bool
    operator: str | None
    website: str | None
    # California public piers: no fishing license needed on them; the note
    # says where next to one it is ("shore_wall", "shore_wall_and_inner_jetty",
    # "breakwater", "footbridge").
    no_license: bool
    license_note: str | None
    source: str  # "osm" | "cdfw"
    source_url: str  # the source's own page for this spot or its dataset
    osm_url: str | None  # the OpenStreetMap element, when it is mapped there
