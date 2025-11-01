# import requests
# from typing import Optional, Tuple


# OVERPASS_URL = "https://overpass-api.de/api/interpreter"


# def _query_overpass(lat: float, lon: float, radius_m: int = 2000) -> Optional[dict]:
# 	query = f"""
# 	[out:json][timeout:15];
# 	(
# 	  node["natural"="water"](around:{radius_m},{lat},{lon});
# 	  way["natural"="water"](around:{radius_m},{lat},{lon});
# 	  relation["natural"="water"](around:{radius_m},{lat},{lon});
# 	  node["waterway"="river"](around:{radius_m},{lat},{lon});
# 	  way["waterway"="river"](around:{radius_m},{lat},{lon});
# 	);
# 	out center 10;
# 	"""
# 	try:
# 		resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=5)
# 		resp.raise_for_status()
# 		return resp.json()
# 	except Exception:
# 		return None


# def estimate_water_proximity_score(latitude: float, longitude: float) -> Tuple[Optional[float], Optional[float]]:
# 	"""Estimate distance (km) to nearest water body and map to a suitability score.

# 	Returns (score_0_100, distance_km). Closer than ~100m is riskier for construction.
# 	"""
# 	data = _query_overpass(latitude, longitude)
# 	if not data or not data.get("elements"):
# 		return None, None

# 	# Use haversine formula approximately; we will avoid external deps.
# 	from math import radians, sin, cos, sqrt, atan2

# 	def haversine_km(lat1, lon1, lat2, lon2):
# 		R = 6371.0
# 		phi1, phi2 = radians(lat1), radians(lat2)
# 		dphi = radians(lat2 - lat1)
# 		dlambda = radians(lon2 - lon1)
# 		a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
# 		c = 2 * atan2(sqrt(a), sqrt(1-a))
# 		return R * c

# 	min_km = None
# 	for el in data["elements"]:
# 		if "lat" in el and "lon" in el:
# 			d = haversine_km(latitude, longitude, el["lat"], el["lon"])
# 			min_km = d if min_km is None else min(min_km, d)
# 		elif "center" in el and "lat" in el["center"] and "lon" in el["center"]:
# 			d = haversine_km(latitude, longitude, el["center"]["lat"], el["center"]["lon"])
# 			min_km = d if min_km is None else min(min_km, d)

# 	if min_km is None:
# 		return None, None

# 	# Map distance to score (further is safer for construction)
# 	# <0.1km => 20; 0.1-0.5 => 50; 0.5-2 => 80; >2 => 60 neutral-good
# 	if min_km < 0.1:
# 		score = 20.0
# 	elif min_km < 0.5:
# 		score = 50.0
# 	elif min_km < 2.0:
# 		score = 80.0
# 	else:
# 		score = 60.0

# 	return score, round(min_km, 3)


import time
import requests
from typing import Optional, Tuple

# Prefer multiple Overpass mirrors to reduce rate-limit/availability issues
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

_DEFAULT_HEADERS = {
    "User-Agent": "GeoAI/1.0 (contact: support@example.com)",
    "Accept": "application/json",
}

NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

def _build_overpass_query(lat: float, lon: float, radius_m: int) -> str:
    # Capture a broader set of water features commonly used in OSM tagging
    return f"""
    [out:json][timeout:50];
    (
      node["natural"="water"](around:{radius_m},{lat},{lon});
      way["natural"="water"](around:{radius_m},{lat},{lon});
      relation["natural"="water"](around:{radius_m},{lat},{lon});

      node["natural"="wetland"](around:{radius_m},{lat},{lon});
      way["natural"="wetland"](around:{radius_m},{lat},{lon});

      node["landuse"="reservoir"](around:{radius_m},{lat},{lon});
      way["landuse"="reservoir"](around:{radius_m},{lat},{lon});

      node["water"](around:{radius_m},{lat},{lon});
      way["water"](around:{radius_m},{lat},{lon});

      node["waterway"~"^(river|stream|canal|drain|ditch)$"](around:{radius_m},{lat},{lon});
      way["waterway"~"^(river|stream|canal|drain|ditch)$"](around:{radius_m},{lat},{lon});
    );
    out center 60;
    """

def _query_overpass(lat: float, lon: float, radius_m: int) -> Optional[dict]:
    """
    Query Overpass with retries across mirrors and backoff.
    """
    query = _build_overpass_query(lat, lon, radius_m)
    last_err: Optional[Exception] = None
    for attempt in range(3):  # up to 3 rounds
        for base_url in OVERPASS_URLS:
            try:
                resp = requests.post(
                    base_url,
                    data={"data": query},
                    headers=_DEFAULT_HEADERS,
                    timeout=15,
                )
                if resp.status_code == 429:  # rate limited, try next mirror
                    last_err = Exception("429 Too Many Requests")
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_err = e
                # Try the next mirror
                continue
        # Backoff between rounds
        time.sleep(0.8 * (attempt + 1))
    print(f"Overpass query failed after retries: {last_err}")
    return None

def _reverse_check_on_water(lat: float, lon: float) -> bool:
    """
    Fallback: use Nominatim reverse geocoding to see if point lies on water.
    Returns True if strong indication of water feature at the point.
    """
    try:
        params = {
            "format": "jsonv2",
            "lat": lat,
            "lon": lon,
            "zoom": 0,  # Lower zoom to get broader feature context for oceans
            "addressdetails": 1,
            "extratags": 1,
        }
        resp = requests.get(NOMINATIM_REVERSE_URL, params=params, headers=_DEFAULT_HEADERS, timeout=12)
        resp.raise_for_status()
        data = resp.json() or {}
        extra = data.get("extratags") or {}
        cls = data.get("class") or ""
        typ = data.get("type") or ""
        addr = data.get("address", {})

        # Heuristics: treat as water if any of these indicate water/wetlands
        waterish_values = {
            str(extra.get("natural", "")).lower(),
            str(extra.get("water", "")).lower(),
            str(extra.get("waterway", "")).lower(),
            str(extra.get("wetland", "")).lower(),
            str(extra.get("landuse", "")).lower(),
            str(extra.get("place", "")).lower(),  # Add place for ocean/sea
        }
        # Expanded to include ocean/sea/bay
        water_types = {"water", "river", "stream", "reservoir", "pond", "lake", "lagoon", "basin", "canal", "riverbank", "wetland", "ocean", "sea", "bay"}
        if any(v in water_types for v in waterish_values):
            return True
        if cls in ("waterway", "natural", "place") and typ in water_types:
            return True
        # Also check the display name for ocean/sea keywords
        display_name = str(data.get("display_name", "")).lower()
        if any(word in display_name for word in ["ocean", "sea", "bay", "gulf", "sound", "strait"]):
            return True
        # Check address components too (ocean/seas are often in address)
        if addr:
            for key, value in addr.items():
                val_lower = str(value).lower()
                if any(word in val_lower for word in ["ocean", "sea", "bay", "gulf", "sound", "strait"]):
                    return True
    except Exception:
        return False
    return False

def estimate_water_proximity_score(latitude: float, longitude: float) -> Tuple[float, Optional[float]]:
    """
    Estimate distance (km) to nearest water body and map to a suitability score.
    Returns (score_0_100, distance_km). Closer to water is riskier for construction.
    Uses adaptive radius so we find water features if they are reasonably close.
    """
    # Try increasing radii to improve hit rate without over-querying
    elements = None
    detection_source = None
    for radius_m in (1000, 3000, 7000, 12000):
        data = _query_overpass(latitude, longitude, radius_m)
        if data and data.get("elements"):
            elements = data["elements"]
            detection_source = f"overpass_{radius_m}m"
            break
    # If no water data returned, treat neutrally and report unknown distance
    if not elements:
        # Fallback: direct reverse check; if on water, mark as distance 0
        if _reverse_check_on_water(latitude, longitude):
            # Use a side-channel global var for debug if needed
            return 5.0, 0.0
        return 50.0, None

    # Haversine formula to compute distance in km (corrected)
    from math import radians, sin, cos, sqrt, atan2
    def haversine_km(lat1, lon1, lat2, lon2):
        R = 6371.0
        phi1, phi2 = radians(lat1), radians(lat2)
        dphi = radians(lat2 - lat1)
        dlambda = radians(lon2 - lon1)
        a = (sin(dphi / 2) ** 2) + cos(phi1) * cos(phi2) * (sin(dlambda / 2) ** 2)
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    min_km = None
    for el in elements:
        if "lat" in el and "lon" in el:
            d = haversine_km(latitude, longitude, el["lat"], el["lon"])
        elif "center" in el and "lat" in el["center"] and "lon" in el["center"]:
            d = haversine_km(latitude, longitude, el["center"]["lat"], el["center"]["lon"])
        else:
            continue
        min_km = d if min_km is None else min(min_km, d)

    # If no distance could be calculated, treat as neutral and unknown distance
    if min_km is None:
        return 50.0, None

    # Map distance to score (closer = more risk)
    if min_km < 0.02:         # ~20m: effectively on water
        score = 5.0           # Block-level risk
    elif min_km < 0.05:       # 20–50m: extremely close
        score = 15.0
    elif min_km < 0.2:        # 50–200m: very close
        score = 30.0
    elif min_km < 0.5:        # 200–500m: moderate proximity
        score = 50.0
    elif min_km < 1.5:        # 0.5–1.5km: generally safe
        score = 70.0
    elif min_km < 3.0:        # 1.5–3km: safe distance
        score = 85.0
    else:                      # Far away
        score = 92.0

    return score, round(min_km, 3)