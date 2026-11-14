"""Mumbai (BMC) wards: boundaries, centre points and point-in-ward lookup.

Boundaries: DataMeet India community, CC BY-SA 2.5 IN, simplified to ~40 m.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

WARDS_PATH = Path(__file__).parent / "data" / "bmc_wards.geojson"


@lru_cache
def geojson() -> dict:
    return json.loads(WARDS_PATH.read_text())


@lru_cache
def wards() -> list[dict]:
    return [f["properties"] for f in geojson()["features"]]


def _in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def ward_at(lat: float, lon: float) -> dict | None:
    """The ward containing a point, or None outside the BMC area."""
    for feature in geojson()["features"]:
        geom = feature["geometry"]
        polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for polygon in polygons:
            if _in_ring(lon, lat, polygon[0]) and not any(_in_ring(lon, lat, hole) for hole in polygon[1:]):
                return feature["properties"]
    return None


def search(query: str) -> list[dict]:
    """Match a ward code or one of its area names (case-insensitive)."""
    q = query.strip().lower()
    if not q:
        return []
    hits = []
    for w in wards():
        areas = [a.strip() for a in w["areas"].split(",")]
        for area in areas:
            if q in area.lower():
                hits.append({"label": f"{area}, Mumbai ({w['ward']} ward)", "lat": w["lat"], "lon": w["lon"]})
        if q == w["ward"].lower() or q == f"{w['ward'].lower()} ward":
            hits.append({"label": f"{w['ward']} ward, Mumbai ({w['areas']})", "lat": w["lat"], "lon": w["lon"]})
    return hits
