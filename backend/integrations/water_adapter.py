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


import requests
from typing import Optional, Tuple

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def _query_overpass(lat: float, lon: float, radius_m: int = 2000) -> Optional[dict]:
    """
    Query OpenStreetMap Overpass API for nearby water bodies.
    """
    query = f"""
    [out:json][timeout:15];
    (
      node["natural"="water"](around:{radius_m},{lat},{lon});
      way["natural"="water"](around:{radius_m},{lat},{lon});
      relation["natural"="water"](around:{radius_m},{lat},{lon});
      node["waterway"="river"](around:{radius_m},{lat},{lon});
      way["waterway"="river"](around:{radius_m},{lat},{lon});
    );
    out center 10;
    """
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Overpass query failed: {e}")
        return None

def estimate_water_proximity_score(latitude: float, longitude: float) -> Tuple[float, Optional[float]]:
    """
    Estimate distance (km) to nearest water body and map to a suitability score.
    Returns (score_0_100, distance_km). Closer to water is riskier for construction.
    """
    data = _query_overpass(latitude, longitude)
    
    # If no water data returned, treat neutrally and report unknown distance
    if not data or not data.get("elements"):
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
    for el in data["elements"]:
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