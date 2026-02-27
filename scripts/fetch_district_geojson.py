#!/usr/bin/env python3
"""Fetch Madrid district boundaries from OpenStreetMap and output simplified GeoJSON.

Queries Overpass API for admin_level=9 boundaries within Madrid,
simplifies geometry with topology-preserving Douglas-Peucker (shared edges
simplified once so adjacent districts fit without gaps or overlaps),
and writes docs/districts.geojson.

Usage:
    python scripts/fetch_district_geojson.py
"""

import json
import math
from pathlib import Path

import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass query: all admin_level=9 boundaries within Madrid city (relation 5326784)
OVERPASS_QUERY = """
[out:json][timeout:120];
relation(5326784);
map_to_area->.madrid;
relation["boundary"="administrative"]["admin_level"="9"](area.madrid);
out body;
>;
out skel qt;
"""

# Map OSM district names to names used in MADRID_DISTRICTS in index.html
NAME_MAP = {
    "Arganzuela": "Arganzuela",
    "Barajas": "Barajas",
    "Carabanchel": "Carabanchel",
    "Centro": "Centro",
    "Chamartín": "Chamartín",
    "Chamberí": "Chamberí",
    "Ciudad Lineal": "Ciudad Lineal",
    "Fuencarral-El Pardo": "Fuencarral-El Pardo",
    "Hortaleza": "Hortaleza",
    "Latina": "Latina",
    "Moncloa-Aravaca": "Moncloa-Aravaca",
    "Moratalaz": "Moratalaz",
    "Puente de Vallecas": "Puente de Vallecas",
    "Retiro": "Retiro",
    "Salamanca": "Salamanca",
    "San Blas-Canillejas": "San Blas-Canillejas",
    "San Blas - Canillejas": "San Blas-Canillejas",
    "Tetuán": "Tetuán",
    "Usera": "Usera",
    "Vicálvaro": "Vicálvaro",
    "Villa de Vallecas": "Villa de Vallecas",
    "Villaverde": "Villaverde",
}

TOLERANCE = 0.001  # ~111m at Madrid's latitude


def perpendicular_distance(point, line_start, line_end):
    """Calculate perpendicular distance from point to line segment."""
    dx = line_end[0] - line_start[0]
    dy = line_end[1] - line_start[1]
    if dx == 0 and dy == 0:
        return math.hypot(point[0] - line_start[0], point[1] - line_start[1])
    t = ((point[0] - line_start[0]) * dx + (point[1] - line_start[1]) * dy) / (
        dx * dx + dy * dy
    )
    t = max(0, min(1, t))
    proj_x = line_start[0] + t * dx
    proj_y = line_start[1] + t * dy
    return math.hypot(point[0] - proj_x, point[1] - proj_y)


def douglas_peucker(coords, tolerance):
    """Simplify a line using Douglas-Peucker algorithm."""
    if len(coords) <= 2:
        return coords

    max_dist = 0
    max_idx = 0
    for i in range(1, len(coords) - 1):
        d = perpendicular_distance(coords[i], coords[0], coords[-1])
        if d > max_dist:
            max_dist = d
            max_idx = i

    if max_dist > tolerance:
        left = douglas_peucker(coords[: max_idx + 1], tolerance)
        right = douglas_peucker(coords[max_idx:], tolerance)
        return left[:-1] + right
    else:
        return [coords[0], coords[-1]]


def fetch_overpass():
    """Fetch district data from Overpass API."""
    print("Fetching district boundaries from Overpass API...")
    resp = httpx.post(
        OVERPASS_URL,
        data={"data": OVERPASS_QUERY},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()


def parse_data(data):
    """Parse Overpass response into nodes, ways, and district relation info."""
    nodes = {}
    for el in data["elements"]:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])

    ways = {}
    for el in data["elements"]:
        if el["type"] == "way":
            coords = [nodes[nid] for nid in el["nodes"] if nid in nodes]
            ways[el["id"]] = coords

    districts = []
    for el in data["elements"]:
        if el["type"] != "relation":
            continue
        tags = el.get("tags", {})
        name = tags.get("name", "")
        if not name:
            continue

        mapped_name = NAME_MAP.get(name)
        if not mapped_name:
            for osm_name, app_name in NAME_MAP.items():
                if osm_name.lower() == name.lower():
                    mapped_name = app_name
                    break
        if not mapped_name:
            print(f"  Skipping unmapped district: {name}")
            continue

        # Collect outer way IDs (preserving order and direction)
        outer_members = []
        for member in el.get("members", []):
            if member["type"] == "way" and member.get("role") in ("outer", ""):
                wid = member["ref"]
                if wid in ways:
                    outer_members.append(wid)

        if not outer_members:
            print(f"  No outer ways for: {name}")
            continue

        districts.append({"name": mapped_name, "way_ids": outer_members})

    return ways, districts


def simplify_ways(ways, tolerance):
    """Simplify each way ONCE, preserving endpoints.

    Because adjacent districts share the same OSM way, simplifying at the
    way level guarantees shared borders get identical simplified geometry.
    """
    simplified = {}
    for wid, coords in ways.items():
        if len(coords) <= 2:
            simplified[wid] = coords
            continue
        # Keep endpoints fixed, simplify interior
        interior = douglas_peucker(coords, tolerance)
        if len(interior) < 2:
            interior = [coords[0], coords[-1]]
        simplified[wid] = interior
    return simplified


def merge_ways_from_ids(way_ids, ways):
    """Merge ordered way segments into closed rings using way IDs."""
    segments = []
    for wid in way_ids:
        coords = ways.get(wid, [])
        if coords:
            segments.append(list(coords))

    if not segments:
        return []

    rings = []
    remaining = list(segments)

    while remaining:
        current = remaining.pop(0)
        changed = True
        while changed:
            changed = False
            for i, w in enumerate(remaining):
                if current[-1] == w[0]:
                    current.extend(w[1:])
                    remaining.pop(i)
                    changed = True
                    break
                elif current[-1] == w[-1]:
                    current.extend(list(reversed(w))[1:])
                    remaining.pop(i)
                    changed = True
                    break
                elif current[0] == w[-1]:
                    current = w[:-1] + current
                    remaining.pop(i)
                    changed = True
                    break
                elif current[0] == w[0]:
                    current = list(reversed(w))[:-1] + current
                    remaining.pop(i)
                    changed = True
                    break

        # Close ring
        if len(current) >= 3 and current[0] != current[-1]:
            current.append(current[0])
        if len(current) >= 4:
            rings.append(current)

    return rings


def build_geojson(districts, simplified_ways):
    """Build GeoJSON FeatureCollection using pre-simplified ways."""
    features = []
    for d in districts:
        rings = merge_ways_from_ids(d["way_ids"], simplified_ways)
        if not rings:
            print(f"  WARNING: no rings for {d['name']}")
            continue

        if len(rings) == 1:
            geometry = {"type": "Polygon", "coordinates": [rings[0]]}
        else:
            geometry = {
                "type": "MultiPolygon",
                "coordinates": [[r] for r in rings],
            }

        features.append(
            {
                "type": "Feature",
                "properties": {"name": d["name"]},
                "geometry": geometry,
            }
        )

    return {"type": "FeatureCollection", "features": features}


def count_points(geojson):
    """Count total coordinate points in a GeoJSON FeatureCollection."""
    total = 0
    for f in geojson["features"]:
        geom = f["geometry"]
        if geom["type"] == "Polygon":
            total += sum(len(r) for r in geom["coordinates"])
        else:
            for poly in geom["coordinates"]:
                total += sum(len(r) for r in poly)
    return total


def main():
    data = fetch_overpass()

    ways, districts = parse_data(data)
    print(f"Parsed {len(districts)} districts, {len(ways)} ways")

    if len(districts) < 20:
        print(f"WARNING: Only found {len(districts)}/21 districts")

    # Count original points
    original_points = sum(len(c) for c in ways.values())

    # Simplify at the way level (topology-preserving)
    simplified_ways = simplify_ways(ways, TOLERANCE)
    simplified_points = sum(len(c) for c in simplified_ways.values())

    # Build GeoJSON from simplified ways
    geojson = build_geojson(districts, simplified_ways)

    geojson_points = count_points(geojson)
    reduction = (1 - simplified_points / original_points) * 100 if original_points else 0
    print(
        f"Ways: {original_points} points -> {simplified_points} points "
        f"({reduction:.0f}% reduction)"
    )
    print(f"GeoJSON total: {geojson_points} points")

    out_path = Path(__file__).parent.parent / "docs" / "districts.geojson"
    out_path.write_text(
        json.dumps(geojson, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size_kb = out_path.stat().st_size / 1024
    print(f"Wrote {out_path} ({size_kb:.0f} KB)")

    for f in sorted(geojson["features"], key=lambda f: f["properties"]["name"]):
        print(f"  ✓ {f['properties']['name']}")


if __name__ == "__main__":
    main()
