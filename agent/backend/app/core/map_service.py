"""Map service: geocoding, timezone lookup, and travel time estimation.

Uses free APIs that require no key:
- Nominatim (OpenStreetMap) for geocoding
- timezonefinder for offline timezone lookup
- OSRM demo server for routing (driving / walking / cycling)
- Haversine formula for flight distance estimation
"""

from __future__ import annotations

import math
from datetime import datetime, timezone as tz_module
from typing import Any

import httpx
from timezonefinder import TimezoneFinder


class MapError(Exception):
    """Raised when a map operation fails."""


# Singleton timezone finder (loads data once)
_tf = TimezoneFinder()


# --------------------------------------------------------------------------- #
#  Geocoding
# --------------------------------------------------------------------------- #

async def geocode_location(place_name: str) -> dict[str, Any]:
    """Geocode a place name to coordinates using Nominatim.

    Uses httpx directly for async behavior and full timeout control.
    Returns dict with: lat, lon, display_name
    """
    url = "https://nominatim.osm.org/search"
    params = {
        "q": place_name,
        "format": "json",
        "limit": 1,
        "accept-language": "zh",
    }
    headers = {"User-Agent": "smart-agent-ai"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            raise MapError(f"Nominatim 返回错误状态码: {resp.status_code}")
        data = resp.json()
        if not data:
            raise MapError(f"未找到地点: {place_name}")
        result = data[0]
        return {
            "lat": float(result["lat"]),
            "lon": float(result["lon"]),
            "display_name": result.get("display_name") or place_name,
        }
    except MapError:
        raise
    except httpx.TimeoutException:
        raise MapError(f"地理编码超时，请稍后重试: {place_name}")
    except httpx.HTTPError as e:
        raise MapError(f"地理编码请求失败: {e}")
    except (KeyError, ValueError, IndexError) as e:
        raise MapError(f"解析地理编码结果失败: {e}")


# --------------------------------------------------------------------------- #
#  Timezone & current time
# --------------------------------------------------------------------------- #

def get_location_time(lat: float, lon: float) -> dict[str, Any]:
    """Get the timezone and current local time at the given coordinates."""
    tz_name = _tf.timezone_at(lat=lat, lng=lon)
    if tz_name is None:
        # Fallback: use UTC
        tz_name = "UTC"

    from zoneinfo import ZoneInfo
    tz = ZoneInfo(tz_name)
    now_local = datetime.now(tz)

    return {
        "timezone": tz_name,
        "local_time": now_local.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now_local.weekday()],
    }


# --------------------------------------------------------------------------- #
#  Travel time estimation
# --------------------------------------------------------------------------- #

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance in km between two points."""
    R = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


async def _osrm_route(
    profile: str, lon1: float, lat1: float, lon2: float, lat2: float
) -> dict[str, float] | None:
    """Query OSRM demo server for route distance (km) and duration (hours)."""
    url = (
        f"https://router.project-osrm.org/route/v1/{profile}/"
        f"{lon1},{lat1};{lon2},{lat2}"
        f"?overview=false"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return None
        data = resp.json()
        routes = data.get("routes", [])
        if not routes:
            return None
        route = routes[0]
        return {
            "distance_km": round(route["distance"] / 1000, 1),
            "duration_hours": round(route["duration"] / 3600, 1),
        }
    except Exception:
        return None


async def get_travel_info(
    from_lat: float, from_lon: float, to_lat: float, to_lon: float
) -> list[dict[str, Any]]:
    """Estimate travel time by different transport modes.

    Returns a list of dicts: [{mode, distance_km, duration_hours, duration_text}, ...]
    """
    results: list[dict[str, Any]] = []

    # Straight-line distance for fallback
    straight_km = _haversine_km(from_lat, from_lon, to_lat, to_lon)

    # Driving
    drive = await _osrm_route("driving", from_lon, from_lat, to_lon, to_lat)
    if drive:
        results.append({
            "mode": "驾车",
            "icon": "car",
            "distance_km": drive["distance_km"],
            "duration_hours": drive["duration_hours"],
            "duration_text": _format_duration(drive["duration_hours"]),
        })
    else:
        est_hours = straight_km / 60  # assume 60 km/h average
        results.append({
            "mode": "驾车",
            "icon": "car",
            "distance_km": round(straight_km, 1),
            "duration_hours": round(est_hours, 1),
            "duration_text": _format_duration(est_hours),
        })

    # Walking
    walk = await _osrm_route("foot", from_lon, from_lat, to_lon, to_lat)
    if walk:
        results.append({
            "mode": "步行",
            "icon": "walk",
            "distance_km": walk["distance_km"],
            "duration_hours": walk["duration_hours"],
            "duration_text": _format_duration(walk["duration_hours"]),
        })
    else:
        est_hours = straight_km / 5  # assume 5 km/h average
        results.append({
            "mode": "步行",
            "icon": "walk",
            "distance_km": round(straight_km, 1),
            "duration_hours": round(est_hours, 1),
            "duration_text": _format_duration(est_hours),
        })

    # Cycling
    bike = await _osrm_route("bike", from_lon, from_lat, to_lon, to_lat)
    if bike:
        results.append({
            "mode": "骑行",
            "icon": "bike",
            "distance_km": bike["distance_km"],
            "duration_hours": bike["duration_hours"],
            "duration_text": _format_duration(bike["duration_hours"]),
        })

    # Flight (haversine estimate)
    if straight_km > 100:
        flight_hours = straight_km / 800  # assume 800 km/h average
        results.append({
            "mode": "飞机",
            "icon": "plane",
            "distance_km": round(straight_km, 1),
            "duration_hours": round(flight_hours, 1),
            "duration_text": _format_duration(flight_hours),
        })

    return results


def _format_duration(hours: float) -> str:
    """Format duration in hours to a readable string."""
    if hours < 1:
        return f"{int(hours * 60)}分钟"
    elif hours < 24:
        h = int(hours)
        m = int((hours - h) * 60)
        return f"{h}小时{m}分钟" if m > 0 else f"{h}小时"
    else:
        d = int(hours / 24)
        h = int(hours % 24)
        return f"{d}天{h}小时" if h > 0 else f"{d}天"


# --------------------------------------------------------------------------- #
#  Main map search function (used as LLM tool)
# --------------------------------------------------------------------------- #

async def map_search(
    place: str,
    user_lat: float | None = None,
    user_lon: float | None = None,
) -> dict[str, Any]:
    """Search for a location and return map data.

    Returns dict with: place, lat, lon, display_name, timezone, local_time,
    weekday, travel_info (if user location provided).
    """
    # 1. Geocode
    geo = await geocode_location(place)
    lat = geo["lat"]
    lon = geo["lon"]

    # 2. Get timezone and current time
    time_info = get_location_time(lat, lon)

    # 3. Get travel info if user location is available
    travel_info: list[dict[str, Any]] = []
    if user_lat is not None and user_lon is not None:
        travel_info = await get_travel_info(user_lat, user_lon, lat, lon)

    return {
        "place": place,
        "lat": lat,
        "lon": lon,
        "display_name": geo["display_name"],
        "timezone": time_info["timezone"],
        "local_time": time_info["local_time"],
        "weekday": time_info["weekday"],
        "travel_info": travel_info,
    }


def map_result_to_text(data: dict[str, Any]) -> str:
    """Convert map search result to a text summary for the LLM context."""
    parts = [
        f"地点: {data['display_name']}",
        f"坐标: {data['lat']:.4f}, {data['lon']:.4f}",
        f"时区: {data['timezone']}",
        f"当地时间: {data['local_time']} ({data['weekday']})",
    ]
    if data.get("travel_info"):
        parts.append("出行方式:")
        for t in data["travel_info"]:
            parts.append(f"  - {t['mode']}: 距离{t['distance_km']}km, 约{t['duration_text']}")
    return "\n".join(parts)
