import datetime as _dt
from typing import Optional, Tuple
import requests

_HEADERS = {
    "User-Agent": "GeoAI/1.0 (contact: support@example.com)",
    "Accept": "application/json",
}

def _daterange_days(days: int) -> Tuple[str, str]:
    end = _dt.date.today()
    start = end - _dt.timedelta(days=days)
    return start.isoformat(), end.isoformat()

def _fetch_open_meteo_sum(lat: float, lon: float, days: int = 60) -> Optional[float]:
    start, end = _daterange_days(days)
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}"
        "&daily=precipitation_sum&timezone=auto"
    )
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json() or {}
        daily = (data.get("daily") or {})
        values = daily.get("precipitation_sum") or []
        if not values:
            return None
        total_mm = float(sum(v for v in values if v is not None))
        return total_mm
    except Exception:
        return None

def estimate_rainfall_score(latitude: float, longitude: float) -> Tuple[float, Optional[float]]:
    """
    Returns (score_0_100, total_mm_60d).
    Scoring heuristic (lower rainfall is generally safer for construction/flooding):
      - > 800 mm in 60 days => 20
      - 400–800 mm => 40
      - 100–400 mm => 70
      - < 100 mm => 85
    """
    total_mm = _fetch_open_meteo_sum(latitude, longitude, 60)
    if total_mm is None:
        return 50.0, None
    if total_mm > 800:
        score = 20.0
    elif total_mm > 400:
        score = 40.0
    elif total_mm > 100:
        score = 70.0
    else:
        score = 85.0
    return score, round(total_mm, 1)

