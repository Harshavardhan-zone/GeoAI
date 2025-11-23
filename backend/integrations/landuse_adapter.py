import requests
from typing import Optional


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def infer_landuse_score(latitude: float, longitude: float) -> Optional[float]:
	"""Infer dominant nearby landuse via OSM and score suitability.
	Returns higher score for residential/commercial/industrial; lower for conservation/wetland.
	"""
	query = f"""
	[out:json][timeout:15];
	(
	  way["landuse"](around:500,{latitude},{longitude});
	  relation["landuse"](around:500,{latitude},{longitude});
	);
	out tags 5;
	"""
	try:
		resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=5)
		resp.raise_for_status()
		js = resp.json()
		if not js.get("elements"):
			return None
		best = None
		for el in js["elements"]:
			landuse = (el.get("tags") or {}).get("landuse")
			if not landuse:
				continue
			lu = landuse.lower()
			if lu in ("residential", "commercial", "industrial", "retail"):
				best = max(best or 0, 80)
			elif lu in ("farmland", "farmyard", "orchard"):
				best = max(best or 0, 60)
			elif lu in ("forest", "conservation", "meadow", "wetland"):
				best = max(best or 0, 30)
			else:
				best = max(best or 0, 50)
		return float(best) if best is not None else None
	except Exception:
		return None


