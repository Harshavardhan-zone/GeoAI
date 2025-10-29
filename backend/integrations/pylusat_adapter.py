from typing import Optional
import time
import requests

_MIRRORS = [
	"https://overpass-api.de/api/interpreter",
	"https://overpass.kumi.systems/api/interpreter",
	"https://overpass.openstreetmap.ru/api/interpreter",
]

_HEADERS = {
	"User-Agent": "GeoAI/1.0 (contact: support@example.com)",
	"Accept": "application/json",
}

def _build_roads_query(lat: float, lon: float, radius_m: int) -> str:
	# Focus on major roads for accessibility signal
	return f"""
	[out:json][timeout:25];
	(
	  way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"](around:{radius_m},{lat},{lon});
	  node["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"](around:{radius_m},{lat},{lon});
	);
	out center 20;
	"""

def _query_roads(lat: float, lon: float, radius_m: int) -> Optional[dict]:
	q = _build_roads_query(lat, lon, radius_m)
	last_err: Optional[Exception] = None
	for attempt in range(3):
		for base in _MIRRORS:
			try:
				resp = requests.post(base, data={"data": q}, headers=_HEADERS, timeout=15)
				if resp.status_code == 429:
					last_err = Exception("429 Too Many Requests")
					continue
				resp.raise_for_status()
				return resp.json()
			except Exception as e:
				last_err = e
				continue
		time.sleep(0.8 * (attempt + 1))
	return None

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
	from math import radians, sin, cos, sqrt, atan2
	R = 6371.0
	phi1, phi2 = radians(lat1), radians(lat2)
	dphi = radians(lat2 - lat1)
	dlambda = radians(lon2 - lon1)
	a = (sin(dphi / 2) ** 2) + cos(phi1) * cos(phi2) * (sin(dlambda / 2) ** 2)
	c = 2 * atan2(sqrt(a), sqrt(1 - a))
	return R * c

def compute_proximity_score(latitude: float, longitude: float) -> Optional[float]:
	"""Estimate access proximity to major roads.

	Closer to major roads is considered better for access/markets.
	Returns a score in [0, 100].
	"""
	# Try expanding search radii
	elements = None
	for radius in (1000, 3000, 6000):
		data = _query_roads(latitude, longitude, radius)
		if data and data.get("elements"):
			elements = data["elements"]
			break
	if not elements:
		return None

	min_km = None
	for el in elements:
		if "lat" in el and "lon" in el:
			d = _haversine_km(latitude, longitude, el["lat"], el["lon"])
		elif "center" in el and "lat" in el["center"] and "lon" in el["center"]:
			d = _haversine_km(latitude, longitude, el["center"]["lat"], el["center"]["lon"])
		else:
			continue
		min_km = d if min_km is None else min(min_km, d)
	if min_km is None:
		return None

	# Map distance to score (closer = better access)
	if min_km < 0.1:
		score = 92.0
	elif min_km < 0.3:
		score = 85.0
	elif min_km < 0.8:
		score = 70.0
	elif min_km < 2.0:
		score = 55.0
	else:
		score = 45.0
	return score


