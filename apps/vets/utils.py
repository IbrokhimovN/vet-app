"""Geo yordamchilari — oddiy Haversine masofa (ARCHITECTURE.md 8-bo'lim)."""
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lng1, lat2, lng2):
    """Ikki nuqta orasidagi masofa (km). Biror koordinata yo'q bo'lsa None."""
    if None in (lat1, lng1, lat2, lng2):
        return None
    rlat1, rlng1, rlat2, rlng2 = map(radians, (lat1, lng1, lat2, lng2))
    dlat = rlat2 - rlat1
    dlng = rlng2 - rlng1
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlng / 2) ** 2
    return round(2 * EARTH_RADIUS_KM * asin(sqrt(a)), 2)
