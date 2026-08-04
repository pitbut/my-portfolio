"""Геовычисления без PostGIS — чистый Python, работает и на SQLite, и на
PostgreSQL без расширений. Для объёма данных этой платформы (тысячи
исполнителей, не миллионы) точности и скорости достаточно."""
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Расстояние по большому кругу между двумя точками (км)."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))
