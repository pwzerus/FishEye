"""Plain-Python geo helpers, used until/unless PostGIS is introduced
(see docs/adr/0001-defer-postgis.md). Fine at MVP scale (tens of lakes),
would need to move into the DB (ST_DWithin etc.) before hundreds of
thousands of rows."""
import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * r_km * math.asin(math.sqrt(a))
