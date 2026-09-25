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


REGION_SUFFIXES = (" viloyati", " shahri", " respublikasi")


def region_q(field, city):
    """`field` shu viloyatga tegishli yozuvlar uchun Q.

    Profil select'idan kelgan to'liq nom ("Samarqand viloyati") bilan birga,
    avval qo'lda yozilgan qisqa nomlar ("Samarqand") ham mos deb hisoblanadi.
    """
    from django.db.models import Q

    city = (city or "").strip()
    q = Q(**{f"{field}__iexact": city})
    core = city
    for suffix in REGION_SUFFIXES:
        if core.lower().endswith(suffix):
            core = core[: -len(suffix)].strip()
            break
    if core and core != city:
        q |= Q(**{f"{field}__iexact": core})
    return q
