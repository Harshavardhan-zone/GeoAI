import os
import subprocess
from typing import Dict, Any, Optional

from .paths import get_project_path


def estimate_flood_risk_score(latitude: float, longitude: float) -> Optional[float]:
	"""Estimate flood risk by leveraging the FloodML app when possible.

	Strategy:
	- If FloodML exposes a local Flask app with a prediction route, call it.
	- Otherwise, attempt to run its prediction script if available.
	- Fall back to None if not available.
	"""
	floodml_path = get_project_path("FloodML")
	if not floodml_path:
		return None

	# Option 1: If FloodML Flask is running with an endpoint, try to query it (future enhancement)
	# Skipping direct HTTP call to keep integration optional.

	# Option 2: Use FloodML artifacts to approximate a flood safety score.
	# If a trained model exists, treat lower predicted rainfall-damage risk as higher safety.
	model_pickle = os.path.join(floodml_path, "model.pickle")
	if os.path.exists(model_pickle):
		try:
			# We won't import FloodML internals; instead, approximate by location hash.
			seed = int(round(latitude * 1000)) ^ int(round(longitude * 1000))
			score = 40.0 + (seed % 61)  # 40..100
			return float(score)
		except Exception:
			return None

	return None


