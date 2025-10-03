from typing import Dict, Optional


def _normalize_optional(value: Optional[float], default: float) -> float:
	if value is None:
		return default
	try:
		v = float(value)
		if v < 0:
			return 0.0
		if v > 100:
			return 100.0
		return v
	except Exception:
		return default


def compute_suitability_score(
	*,
	rainfall_score: Optional[float],
	flood_risk_score: Optional[float],
	landslide_risk_score: Optional[float],
	soil_quality_score: Optional[float],
	proximity_score: Optional[float],
	water_proximity_score: Optional[float] = None,
	pollution_score: Optional[float] = None,
	landuse_score: Optional[float] = None,
) -> Dict[str, float]:
	"""Combine factors into a single suitability score in [0, 100].

	Assumptions:
	- Higher rainfall_score means better suitability (0-100).
	- Higher flood_risk_score means safer (invert if needed externally).
	- Higher landslide_risk_score means safer.
	- Higher soil_quality_score is better.
	- Higher proximity_score (to roads/markets/water) is better.

	Missing values are replaced with neutral 50.
	Weights can be tuned later or made configurable.
	"""

	# Replace None with neutral values
	rainfall = _normalize_optional(rainfall_score, 50.0)
	flood = _normalize_optional(flood_risk_score, 50.0)
	landslide = _normalize_optional(landslide_risk_score, 50.0)
	soil = _normalize_optional(soil_quality_score, 50.0)
	proximity = _normalize_optional(proximity_score, 50.0)
	water = _normalize_optional(water_proximity_score, 50.0)
	pollution = _normalize_optional(pollution_score, 50.0)
	landuse = _normalize_optional(landuse_score, 50.0)

	# Simple weighted sum (weights sum to 1.0)
	weights = {
		"rainfall": 0.12,
		"flood": 0.20,
		"landslide": 0.10,
		"soil": 0.18,
		"proximity": 0.10,
		"water": 0.10,
		"pollution": 0.10,
		"landuse": 0.10,
	}

	score = (
		rainfall * weights["rainfall"]
		+ flood * weights["flood"]
		+ landslide * weights["landslide"]
		+ soil * weights["soil"]
		+ proximity * weights["proximity"]
		+ water * weights["water"]
		+ pollution * weights["pollution"]
		+ landuse * weights["landuse"]
	)

	return {
		"score": round(score, 2),
		"rainfall": rainfall,
		"flood": flood,
		"landslide": landslide,
		"soil": soil,
		"proximity": proximity,
		"water": water,
		"pollution": pollution,
		"landuse": landuse,
	}


