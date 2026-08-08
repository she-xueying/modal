"""Weather service: current weather + detailed forecast via Open-Meteo.

Open-Meteo (https://open-meteo.com) is free and requires no API key.
Flow:
  1. Resolve coordinates: geocode a place name (Nominatim) or use user location
  2. Query Open-Meteo forecast endpoint (current + 7-day daily + 24h hourly)
  3. Format result for the LLM context / frontend weather panel
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.map_service import geocode_location, MapError


class WeatherError(Exception):
    """Raised when a weather operation fails."""


# WMO weather code -> Chinese description
WEATHER_CODE_MAP: dict[int, str] = {
    0: "晴",
    1: "晴间多云",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "大毛毛雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "强阵雪",
    95: "雷阵雨",
    96: "雷阵雨伴冰雹",
    99: "强雷阵雨伴冰雹",
}

_WIND_DIRS = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]


def _condition(code: int | None) -> str:
    return WEATHER_CODE_MAP.get(int(code or 0), "未知")


def _wind_direction(deg: float | None) -> str:
    if deg is None:
        return ""
    idx = int(((deg % 360) + 22.5) // 45) % 8
    return _WIND_DIRS[idx]


def _fmt_time(iso: str | None) -> str | None:
    """'2026-08-08T15:00' -> '15:00'"""
    if not iso:
        return None
    try:
        return iso.split("T")[1][:5]
    except (IndexError, AttributeError):
        return iso


# --------------------------------------------------------------------------- #
#  Open-Meteo query
# --------------------------------------------------------------------------- #

async def _fetch_weather(lat: float, lon: float) -> dict[str, Any]:
    """Query Open-Meteo: current weather + 7-day daily + 24h hourly."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "is_day,precipitation,weather_code,wind_speed_10m,wind_direction_10m,"
            "uv_index,cloud_cover,surface_pressure,visibility,precipitation_probability"
        ),
        "hourly": "temperature_2m,weather_code,precipitation_probability",
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,sunrise,sunset"
        ),
        "timezone": "auto",
        "forecast_days": 7,
        "forecast_hours": 24,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params=params)
        if resp.status_code != 200:
            raise WeatherError(f"Open-Meteo 返回错误状态码: {resp.status_code}")
        data = resp.json()
        if data.get("error"):
            raise WeatherError(f"Open-Meteo 服务异常: {data.get('reason', 'unknown')}")
    except httpx.TimeoutException:
        raise WeatherError("天气服务请求超时，请稍后重试")
    except httpx.HTTPError as e:
        raise WeatherError(f"天气服务请求失败: {e}")
    except (KeyError, ValueError) as e:
        raise WeatherError(f"解析天气数据失败: {e}")

    current = data.get("current") or {}
    code = current.get("weather_code")
    return {
        "current": {
            "temperature": current.get("temperature_2m"),
            "apparent_temperature": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_direction": current.get("wind_direction_10m"),
            "wind_dir_text": _wind_direction(current.get("wind_direction_10m")),
            "weather_code": code,
            "condition": _condition(code),
            "is_day": bool(current.get("is_day")),
            "uv_index": current.get("uv_index"),
            "cloud_cover": current.get("cloud_cover"),
            "pressure": current.get("surface_pressure"),
            "visibility": current.get("visibility"),
            "precipitation_probability": current.get("precipitation_probability"),
        },
        "daily": _build_daily(data.get("daily") or {}),
        "hourly": _build_hourly(data.get("hourly") or {}),
    }


def _build_daily(daily: dict[str, Any]) -> list[dict[str, Any]]:
    times = daily.get("time") or []
    codes = daily.get("weather_code") or []
    maxs = daily.get("temperature_2m_max") or []
    mins = daily.get("temperature_2m_min") or []
    probs = daily.get("precipitation_probability_max") or []
    sunrises = daily.get("sunrise") or []
    sunsets = daily.get("sunset") or []
    result: list[dict[str, Any]] = []
    for i, t in enumerate(times):
        c = codes[i] if i < len(codes) else None
        result.append({
            "date": t,
            "weather_code": c,
            "condition": _condition(c),
            "temp_max": maxs[i] if i < len(maxs) else None,
            "temp_min": mins[i] if i < len(mins) else None,
            "precip_prob": probs[i] if i < len(probs) else None,
            "sunrise": _fmt_time(sunrises[i]) if i < len(sunrises) else None,
            "sunset": _fmt_time(sunsets[i]) if i < len(sunsets) else None,
        })
    return result


def _build_hourly(hourly: dict[str, Any]) -> list[dict[str, Any]]:
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    codes = hourly.get("weather_code") or []
    probs = hourly.get("precipitation_probability") or []
    result: list[dict[str, Any]] = []
    # Sample every 3rd hour (3-hour steps) for the next 24 hours
    for i in range(0, len(times), 3):
        c = codes[i] if i < len(codes) else None
        result.append({
            "time": _fmt_time(times[i]) if i < len(times) else None,
            "temperature": temps[i] if i < len(temps) else None,
            "weather_code": c,
            "condition": _condition(c),
            "precip_prob": probs[i] if i < len(probs) else None,
        })
    return result


# --------------------------------------------------------------------------- #
#  Main weather search function (used as LLM tool)
# --------------------------------------------------------------------------- #

async def weather_search(
    place: str = "",
    user_lat: float | None = None,
    user_lon: float | None = None,
    default_lat: float | None = None,
    default_lon: float | None = None,
    default_name: str | None = None,
) -> dict[str, Any]:
    """Query weather for a place, the user's location, or the saved default.

    Resolution priority: explicit place -> user location -> saved default.
    Returns dict with: place, display_name, lat, lon, current, daily, hourly.
    """
    lat: float | None = None
    lon: float | None = None
    display_name = place or "我的位置"

    if place:
        try:
            geo = await geocode_location(place)
            lat, lon = geo["lat"], geo["lon"]
            display_name = geo["display_name"]
        except MapError as e:
            raise WeatherError(f"无法定位地点: {e}")
    elif user_lat is not None and user_lon is not None:
        lat, lon = user_lat, user_lon
        display_name = "我的位置"
    elif default_lat is not None and default_lon is not None:
        lat, lon = default_lat, default_lon
        display_name = default_name or "默认地点"
    else:
        raise WeatherError("缺少地点信息，无法查询天气")

    weather = await _fetch_weather(lat, lon)

    return {
        "place": place or "我的位置",
        "display_name": display_name,
        "lat": lat,
        "lon": lon,
        "current": weather["current"],
        "daily": weather["daily"],
        "hourly": weather["hourly"],
    }


def weather_result_to_text(data: dict[str, Any]) -> str:
    """Convert weather result to a text summary for the LLM context."""
    c = data["current"]
    daily = data.get("daily") or []
    lines = [
        f"地点: {data['display_name']}",
        f"当前天气: {c['condition']}, {c['temperature']}°C (体感 {c['apparent_temperature']}°C)",
    ]
    parts = []
    if c.get("humidity") is not None:
        parts.append(f"湿度{c['humidity']}%")
    if c.get("wind_speed") is not None:
        parts.append(f"{c['wind_dir_text']} {c['wind_speed']}km/h")
    if c.get("precipitation") is not None:
        parts.append(f"降水{c['precipitation']}mm")
    if c.get("uv_index") is not None:
        parts.append(f"紫外线{c['uv_index']}")
    if c.get("precipitation_probability") is not None:
        parts.append(f"降雨概率{c['precipitation_probability']}%")
    if parts:
        lines.append("当前详情: " + " | ".join(parts))

    if daily:
        today = daily[0]
        lines.append(
            f"今日: {today['condition']}, 最高 {today['temp_max']}°C / 最低 {today['temp_min']}°C"
            + (f", 降雨概率{today['precip_prob']}%" if today.get("precip_prob") is not None else "")
        )
        # Next 3 days brief
        upcoming = []
        for d in daily[1:4]:
            upcoming.append(f"{d['date'][5:]}{d['condition']}{d['temp_min']}~{d['temp_max']}°")
        if upcoming:
            lines.append("未来3天: " + "、".join(upcoming))

    return "\n".join(lines)