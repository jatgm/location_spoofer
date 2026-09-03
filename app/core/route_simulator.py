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
    tick_interval_sec: float = 1.0
) -> List[Tuple[float, float]]:
    """
    Takes coarse route waypoints and slices them into exact sub-second steps
    matching the travel speed (km/h) for fluid, natural GPS updates.
    """
    if len(raw_waypoints) < 2:
        return raw_waypoints

    speed_mps = (speed_kmh * 1000.0) / 3600.0  # meters per second
    step_distance = speed_mps * tick_interval_sec  # meters to advance per tick

    timeline: List[Tuple[float, float]] = [raw_waypoints[0]]

    curr_lat, curr_lon = raw_waypoints[0]

    for next_lat, next_lon in raw_waypoints[1:]:
        segment_dist = haversine_distance(curr_lat, curr_lon, next_lat, next_lon)
        if segment_dist <= step_distance:
            timeline.append((next_lat, next_lon))
            curr_lat, curr_lon = next_lat, next_lon
        else:
            num_steps = max(1, int(segment_dist / step_distance))
            interpolated = interpolate_points(curr_lat, curr_lon, next_lat, next_lon, num_steps)
            timeline.extend(interpolated)
            curr_lat, curr_lon = next_lat, next_lon

    return timeline
