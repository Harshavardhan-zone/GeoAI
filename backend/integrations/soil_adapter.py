from typing import Optional
import random


def estimate_soil_quality_score(latitude: float, longitude: float) -> Optional[float]:
	"""Placeholder soil quality score. Replace with real soil datasets or APIs.
	Currently returns a deterministic pseudo-random score based on rounded coords.
	"""
	seed = int(round(latitude * 1000)) ^ int(round(longitude * 1000))
	random.seed(seed)
	return float(round(40 + random.random() * 60, 2))

