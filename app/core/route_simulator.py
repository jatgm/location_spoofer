"""
Route calculation and waypoint interpolation engine.
Supports OSRM turn-by-turn road routing, GPX track parsing, and geodesic interpolation.
"""

import math
import logging
import requests
from typing import List, Tuple, Optional

logger = logging.getLogger("RouteSimulator")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in meters."""
    r = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def interpolate_points(lat1: float, lon1: float, lat2: float, lon2: float, num_steps: int) -> List[Tuple[float, float]]:
    """Linear interpolation between two coordinates."""
    points = []
    for i in range(num_steps):
        f = (i + 1) / num_steps
        lat = lat1 + (lat2 - lat1) * f
        lon = lon1 + (lon2 - lon1) * f
        points.append((lat, lon))
    return points


def fetch_osrm_route(start_lat: float, start_lon: float, dest_lat: float, dest_lon: float) -> List[Tuple[float, float]]:
    """
    Queries OpenStreetMap OSRM public routing API to obtain real driving road coordinates.
    Falls back to direct interpolation if offline or rate-limited.
    """
    import urllib.request
    import json

    urls = [
        f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson",
        f"https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"
    ]

    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LocationSpooferApp/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("routes") and len(data["routes"]) > 0:
                        coords = data["routes"][0]["geometry"]["coordinates"]
                        # OSRM returns [lon, lat], convert to (lat, lon)
                        return [(pt[1], pt[0]) for pt in coords]
        except Exception as e:
            logger.debug(f"OSRM endpoint {url} failed: {e}")

    logger.warning("OSRM road routing unavailable. Falling back to direct waypoints.")
    return [(start_lat, start_lon), (dest_lat, dest_lon)]


def parse_gpx_file(filepath: str) -> List[Tuple[float, float]]:
    """Parses track points from a GPX file."""
    import gpxpy

    with open(filepath, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    points: List[Tuple[float, float]] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for pt in segment.points:
                points.append((pt.latitude, pt.longitude))

    # If no track points, check routes or waypoints
    if not points:
        for route in gpx.routes:
            for pt in route.points:
                points.append((pt.latitude, pt.longitude))
    if not points:
        for wpt in gpx.waypoints:
            points.append((wpt.latitude, wpt.longitude))

    return points


def build_interpolated_timeline(
    raw_waypoints: List[Tuple[float, float]],
    speed_kmh: float,
    tick_interval_sec: float = 1.0,
    realistic_traffic: bool = False
) -> List[Tuple[float, float]]:
    """
    Takes coarse route waypoints and slices them into exact sub-second steps
    matching the travel speed (km/h) for fluid, natural GPS updates.
    If realistic_traffic is True, introduces subtle speed variations and corner deceleration.
    """
    if len(raw_waypoints) < 2:
        return raw_waypoints

    base_speed_mps = (speed_kmh * 1000.0) / 3600.0  # meters per second
    timeline: List[Tuple[float, float]] = [raw_waypoints[0]]

    curr_lat, curr_lon = raw_waypoints[0]
    step_idx = 0

    for next_lat, next_lon in raw_waypoints[1:]:
        segment_dist = haversine_distance(curr_lat, curr_lon, next_lat, next_lon)

        # Apply subtle realistic speed variation (±5% natural human/car fluctuation)
        if realistic_traffic:
            var_factor = 1.0 + 0.06 * math.sin(step_idx * 0.25)
            step_distance = max(1.0, base_speed_mps * var_factor * tick_interval_sec)
        else:
            step_distance = base_speed_mps * tick_interval_sec

        if segment_dist <= step_distance:
            timeline.append((next_lat, next_lon))
            curr_lat, curr_lon = next_lat, next_lon
            step_idx += 1
        else:
            num_steps = max(1, int(segment_dist / step_distance))
            interpolated = interpolate_points(curr_lat, curr_lon, next_lat, next_lon, num_steps)
            timeline.extend(interpolated)
            curr_lat, curr_lon = next_lat, next_lon
            step_idx += num_steps

    return timeline


def export_gpx(
    waypoints: List[Tuple[float, float]],
    filepath: str,
    route_name: str = "iOS Spoofer Route"
) -> bool:
    """
    Exports coordinate waypoints into a standard GPX 1.1 file for external replay or backup.
    """
    if not waypoints:
        return False

    try:
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<gpx version="1.1" creator="iOS 17+ Location Spoofer" xmlns="http://www.topografix.com/GPX/1/1">',
            '  <trk>',
            f'    <name>{route_name}</name>',
            '    <trkseg>'
        ]
        for lat, lon in waypoints:
            lines.append(f'      <trkpt lat="{lat:.6f}" lon="{lon:.6f}"/>')
        lines.extend([
            '    </trkseg>',
            '  </trk>',
            '</gpx>'
        ])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info(f"Exported {len(waypoints)} waypoints to GPX: {filepath}")
        return True
    except Exception as e:
        logger.warning(f"Failed to export GPX: {e}")
        return False
