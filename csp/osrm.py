"""
OSRM route fetching with polyline decoding and synthetic fallback.
"""

import requests
import math
import random
from typing import List, Tuple, Optional
from csp.variables import RouteOption

OSRM_BASE = "http://router.project-osrm.org"
TIMEOUT    = 15


def _decode_polyline(encoded: str) -> List[List[float]]:
    result = []
    idx, lat, lng = 0, 0, 0
    while idx < len(encoded):
        shift, result_val = 0, 0
        while True:
            b = ord(encoded[idx]) - 63
            idx += 1
            result_val |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result_val >> 1) if result_val & 1 else result_val >> 1
        lat += dlat
        shift, result_val = 0, 0
        while True:
            b = ord(encoded[idx]) - 63
            idx += 1
            result_val |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result_val >> 1) if result_val & 1 else result_val >> 1
        lng += dlng
        result.append([lat / 1e5, lng / 1e5])
    return result


def _haversine_km(a, b):
    R = 6371.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(h), math.sqrt(1-h))


def fetch_routes(start, end, alternatives=3):
    coords = f"{start[1]},{start[0]};{end[1]},{end[0]}"
    url = (f"{OSRM_BASE}/route/v1/driving/{coords}"
           f"?alternatives={alternatives}&geometries=polyline&overview=full&steps=false")
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        return _synthetic_routes(start, end, alternatives), str(exc)

    if data.get("code") != "Ok" or not data.get("routes"):
        return _synthetic_routes(start, end, alternatives), "OSRM returned no routes"

    routes = []
    for i, r in enumerate(data["routes"][:alternatives]):
        geometry = _decode_polyline(r["geometry"])
        traffic_factor = round(random.uniform(1.0, 1.9), 3)
        routes.append(RouteOption(
            index=i,
            distance_m=r["distance"],
            duration_s=r["duration"],
            geometry=geometry,
            waypoints=[{"lat": p[0], "lng": p[1]} for p in geometry[::max(1, len(geometry)//8)]],
            traffic_factor=traffic_factor,
        ))
    return routes, None


def _interpolate(points, steps):
    result = []
    segs = len(points) - 1
    per  = max(1, steps // segs)
    for i in range(segs):
        a, b = points[i], points[i+1]
        for t in range(per):
            frac = t / per
            result.append([a[0]+(b[0]-a[0])*frac, a[1]+(b[1]-a[1])*frac])
    result.append(points[-1])
    return result


def _synthetic_routes(start, end, n):
    routes = []
    base_dist = _haversine_km(start, end) * 1000
    base_dur  = base_dist / 13.88
    for i in range(n):
        factor = 1.0 + i * 0.18
        offset = (i - 1) * 0.008
        mid_lat = (start[0]+end[0])/2 + offset
        mid_lng = (start[1]+end[1])/2 + offset
        geom = _interpolate([[start[0],start[1]],[mid_lat,mid_lng],[end[0],end[1]]], 30)
        routes.append(RouteOption(
            index=i,
            distance_m=base_dist*factor,
            duration_s=base_dur*factor,
            geometry=geom,
            waypoints=[{"lat":p[0],"lng":p[1]} for p in geom[::5]],
            traffic_factor=round(random.uniform(1.0, 1.9), 3),
        ))
    return routes
