# services/weather_client.py
# Lightweight weather reader for Ingenious Irrigation
# ---------------------------------------------------
# - Primary output is WeatherSnapshot (rain in/next 24h, inches; today's max temp °F).
# - Reads optional local cache: storage/weather_cache.json with keys:
#     {"rain_mm_48h": 1.5, "forecast_high_f": 96, "raining_now": false}
# - Optionally queries Open-Meteo (no API key) if USE_NETWORK is true.
# - Always fails safe to local cache or conservative defaults.

from _future_ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import json
import os

# -----------------------------
# Configuration
# -----------------------------
# You can disable network lookups by setting env var: II_WEATHER_USE_NETWORK=0
USE_NETWORK = os.getenv("II_WEATHER_USE_NETWORK", "1").strip() not in ("0", "false", "False", "")

# Default location (Houston, TX) can be overridden by env
DEFAULT_LAT = float(os.getenv("II_LAT", "29.7604"))
DEFAULT_LON = float(os.getenv("II_LON", "-95.3698"))

# Paths
CACHE_PATH = Path("storage") / "weather_cache.json"


@dataclass
class WeatherSnapshot:
    """Canonical weather summary for the scheduler/logic."""
    rain_last_24h_in: float      # inches
    rain_next_24h_in: float      # inches (forecast)
    max_temp_today_f: float      # °F


# -----------------------------
# Public API
# -----------------------------
def get_snapshot(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> WeatherSnapshot:
    """
    Try network (Open-Meteo) if enabled; otherwise use cache; otherwise defaults.
    Never raises; always returns a safe WeatherSnapshot.
    """
    # 1) Try network
    if USE_NETWORK:
        snap = _try_open_meteo(lat, lon)
        if snap:
            return snap

    # 2) Try cache
    snap = _from_cache()
    if snap:
        return snap

    # 3) Conservative defaults (dry-ish, warm-ish)
    return WeatherSnapshot(
        rain_last_24h_in=0.0,
        rain_next_24h_in=0.0,
        max_temp_today_f=88.0,
    )


def get_weather_summary() -> Dict[str, Any]:
    """
    Back-compat helper matching your earlier signature.
    Returns dict with:
      - rain_mm_48h: float
      - forecast_high_f: float
      - raining_now: bool
    Reads storage/weather_cache.json if present, else safe defaults.
    """
    data = _read_cache_dict()
    return {
        "rain_mm_48h": float(data.get("rain_mm_48h", 0.0) or 0.0),
        "forecast_high_f": float(data.get("forecast_high_f", 85.0) or 85.0),
        "raining_now": bool(data.get("raining_now", False)),
    }


# -----------------------------
# Internals
# -----------------------------
def _from_cache() -> Optional[WeatherSnapshot]:
    """
    Build WeatherSnapshot from local cache (48h rain -> split approx across
    last/next 24h conservatively). If keys are missing, fill with defaults.
    """
    data = _read_cache_dict()
    try:
        rain_mm_48h = float(data.get("rain_mm_48h", 0.0) or 0.0)
        forecast_high_f = float(data.get("forecast_high_f", 85.0) or 85.0)
        raining_now = bool(data.get("raining_now", False))

        # Heuristics:
        # - Approximate last_24h as half of 48h bucket if we don't have per-day split.
        # - Keep next_24h at 0 unless it's currently raining, in which case we assign a small floor.
        last_24_in = _mm_to_inches(rain_mm_48h) / 2.0
        next_24_in = 0.05 if raining_now else 0.0

        return WeatherSnapshot(
            rain_last_24h_in=max(0.0, round(last_24_in, 3)),
            rain_next_24h_in=max(0.0, round(next_24_in, 3)),
            max_temp_today_f=float(forecast_high_f),
        )
    except Exception:
        return None


def _try_open_meteo(lat: float, lon: float) -> Optional[WeatherSnapshot]:
    """
    Best-effort call to Open-Meteo (no API key).
    We keep it intentionally simple and conservative:
      - Use 'hourly=precipitation,temperature_2m' for upcoming/ongoing precip.
      - Use 'daily=temperature_2m_max,precipitation_sum' for today’s totals.
    If anything goes wrong, return None to fall back cleanly.
    """
    try:
        import requests  # lazy import to avoid hard dep if offline
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat:.4f}&longitude={lon:.4f}"
            "&hourly=precipitation,temperature_2m"
            "&daily=temperature_2m_max,precipitation_sum"
            "&forecast_days=2"
            "&timezone=auto"
        )
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        j = r.json()

        # Daily block for max temp today (°C -> °F)
        daily = j.get("daily", {}) or {}
        tmax_list = daily.get("temperature_2m_max") or []
        # pick today's tmax if present
        if tmax_list:
            max_temp_today_c = float(tmax_list[0])
        else:
            max_temp_today_c = 29.0  # ~84°F fallback

        max_temp_today_f = _c_to_f(max_temp_today_c)

        # Hourly precip (mm). We'll estimate:
        # - next_24h from the first 24 hourly values (including current)
        # - last_24h from cache if available; if not, use daily precip_sum[0] as a proxy
        hourly = j.get("hourly", {}) or {}
        precip_hourly = hourly.get("precipitation") or []
        next_24_mm = sum(_safe_float(x) for x in precip_hourly[:24]) if precip_hourly else 0.0

        # daily precip_sum gives per-day total (mm). Use today's as last_24h proxy if no cache.
        precip_sum = daily.get("precipitation_sum") or []
        last_24_mm = float(precip_sum[0]) if precip_sum else 0.0

        # Merge with cache if present (cache wins for last_24 approximation if it has a value)
        cache = _read_cache_dict()
        cache_mm_48h = _safe_float(cache.get("rain_mm_48h"))
        if cache_mm_48h > 0:
            # Prefer cache for "recent rain" (split half as last_24)
            last_24_mm = cache_mm_48h / 2.0

        return WeatherSnapshot(
            rain_last_24h_in=round(_mm_to_inches(last_24_mm), 3),
            rain_next_24h_in=round(_mm_to_inches(next_24_mm), 3),
            max_temp_today_f=round(max_temp_today_f, 1),
        )

    except Exception:
        return None


def _read_cache_dict() -> Dict[str, Any]:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _mm_to_inches(mm: float) -> float:
    try:
        return float(mm) / 25.4
    except Exception:
        return 0.0


def _c_to_f(c: float) -> float:
    try:
        return (float(c) * 9.0 / 5.0) + 32.0
    except Exception:
        return 86.0  # safe warm-ish default


def _safe_float(x: Any) -> float:
    try:
        return float(x or 0.0)
    except Exception:
        return 0.0
