import requests
from typing import Optional


OPENAQ_URL = "https://api.openaq.org/v2/latest"


def estimate_pollution_score(latitude: float, longitude: float) -> Optional[float]:
	"""Query OpenAQ for PM2.5 near the coordinate and map to a 0-100 score.
	If API fails, return None.
	"""
	try:
		params = {
			"coordinates": f"{latitude},{longitude}",
			"radius": 10000,
			"limit": 1,
		}
		resp = requests.get(OPENAQ_URL, params=params, timeout=5)
		resp.raise_for_status()
		js = resp.json()
		if not js.get("results"):
			return None
		meas = js["results"][0].get("measurements", [])
		pm25 = None
		for m in meas:
			if m.get("parameter") in ("pm25", "pm2.5", "pm_25"):
				pm25 = m.get("value")
				break
		if pm25 is None:
			return None
		# Map PM2.5 ug/m3 to score: lower better
		# <10 => 90, 10-25 => 70, 25-50 => 50, >50 => 30
		v = float(pm25)
		if v < 10:
			return 90.0
		elif v < 25:
			return 70.0
		elif v < 50:
			return 50.0
		else:
			return 30.0
	except Exception:
		return None


