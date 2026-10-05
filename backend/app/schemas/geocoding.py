from pydantic import BaseModel


class GeocodeResultOut(BaseModel):
    query: str
    display_name: str
    latitude: float
    longitude: float
