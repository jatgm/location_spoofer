"""
Physical Geolocation Provider.
Detects user's actual physical location via high-accuracy IP geolocation.
"""

import json
import logging
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("Geolocation")

CONFIG_DIR = Path.home() / ".config" / "location_spoofer"
CONFIG_FILE = CONFIG_DIR / "default_location.json"


def get_saved_default_location() -> Optional[Tuple[float, float, str]]:
    """Returns the user's saved real-life default location if one has been set."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text("utf-8"))
            lat = float(data["lat"])
            lon = float(data["lon"])
            name = data.get("name", "My Default Location")
            return lat, lon, name
        except Exception as e:
            logger.debug(f"Could not load saved location: {e}")
    return None


def save_default_location(lat: float, lon: float, name: str = "My Default Location") -> bool:
    """Saves user's actual real-life coordinates as the permanent default."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps({
            "lat": lat,
            "lon": lon,
            "name": name
        }, indent=2), "utf-8")
        logger.info(f"Saved real-life default location: {name} ({lat}, {lon})")
        return True
    except Exception as e:
        logger.warning(f"Could not save default location: {e}")
        return False


def get_actual_location() -> Optional[Tuple[float, float, str]]:
    """
    Queries user's saved location first, then falls back to IP geolocation.
    Returns: (latitude, longitude, description) or None on failure.
    """
    # 1. First priority: Check if user saved their exact real-life location
    saved = get_saved_default_location()
    if saved:
        logger.info(f"Using saved real-life default location: {saved[2]} ({saved[0]}, {saved[1]})")
        return saved
    providers = [
        (
            "https://ipapi.co/json/",
            lambda d: (
                float(d["latitude"]),
                float(d["longitude"]),
                f"{d.get('city', '')}, {d.get('region', '')}, {d.get('country_name', '')}".strip(", ")
            )
        ),
        (
            "http://ip-api.com/json/",
            lambda d: (
                float(d["lat"]),
                float(d["lon"]),
                f"{d.get('city', '')}, {d.get('regionName', '')}, {d.get('country', '')}".strip(", ")
            )
        ),
    ]

    for url, extractor in providers:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "LocationSpoofer/1.0 (macOS; en-US)"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                lat, lon, desc = extractor(data)
                logger.info(f"Detected physical location: {desc} ({lat}, {lon})")
                return lat, lon, desc
        except Exception as e:
            logger.debug(f"Geolocation provider {url} failed: {e}")

    return None


def search_addresses(query: str, limit: int = 5):
    """
    Geocodes an address or landmark string into matching candidates.
    Returns: [{'name': '...', 'full_name': '...', 'lat': float, 'lon': float}, ...]
    """
    import urllib.parse
    if not query or len(query.strip()) < 2:
        return []

    encoded = urllib.parse.quote(query.strip())
    # 1. Try Nominatim
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={encoded}&limit={limit}&addressdetails=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LocationSpooferApp/1.0"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = []
            for item in data:
                display = item.get("display_name", "")
                parts = [p.strip() for p in display.split(",") if p.strip()]
                short_name = ", ".join(parts[:3]) if len(parts) >= 3 else display
                results.append({
                    "name": short_name,
                    "full_name": display,
                    "lat": float(item["lat"]),
                    "lon": float(item["lon"])
                })
            if results:
                return results
    except Exception as e:
        logger.debug(f"Nominatim search failed: {e}")

    # 2. Fallback to Photon
    url_photon = f"https://photon.komoot.io/api/?q={encoded}&limit={limit}"
    try:
        req = urllib.request.Request(url_photon, headers={"User-Agent": "LocationSpooferApp/1.0"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = []
            for f in data.get("features", []):
                p = f.get("properties", {})
                coords = f.get("geometry", {}).get("coordinates", [0, 0])
                name = p.get("name") or p.get("street") or query
                city = p.get("city") or p.get("state") or ""
                country = p.get("country") or ""
                label = ", ".join([x for x in [name, city, country] if x])
                results.append({
                    "name": label,
                    "full_name": label,
                    "lat": float(coords[1]),
                    "lon": float(coords[0])
                })
            return results
    except Exception as e:
        logger.debug(f"Photon search failed: {e}")

    return []
