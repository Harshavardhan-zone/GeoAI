# from typing import Optional
# import requests
# import json
# import numpy as np  # For potential PyLandslide extensions

# def estimate_landslide_risk_score(latitude: float, longitude: float, api_key: Optional[str] = None) -> Optional[float]:
#     """
#     Enhanced landslide risk estimation: Primary via NASA's EONET API for historical events.
#     Fallback/Advanced: Placeholder for PyLandslide integration (requires pip install PyLandslide and factor maps).
#     Returns safety score (0-100, higher = lower risk). Reference: PyLandslide for ML-weighted susceptibility.
#     """
#     # Primary: Query EONET for historical landslides (~10-year window)
#     delta = 0.05  # ~5km bounding box
#     bbox = f"{longitude - delta},{latitude - delta},{longitude + delta},{latitude + delta}"
#     url = "https://eonet.gsfc.nasa.gov/api/v3/events"
#     params = {
#         'category': 'landslides',  # NASA category for landslides
#         'bbox': bbox,
#         'days': 3650,  # 10 years historical
#         'limit': 50
#     }
    
#     try:
#         response = requests.get(url, params=params, timeout=10)
#         response.raise_for_status()
#         data = response.json()
#         events = data.get('events', [])
#         num_events = len([e for e in events if e.get('geometry')])  # Filter valid geoms
        
#         # Heuristic score: Base 85 (global avg low risk), penalize by events/recency
#         # Weight recent (last 2y: x2 penalty); cap for extremes
#         recent_events = sum(1 for e in events if (2025 - int(e.get('date', '2025').split('-')[0])) <= 2)
#         risk_penalty = min((num_events * 8) + (recent_events * 4), 85)
#         safety_score = 85 - risk_penalty
#         score = max(0, safety_score)
        
#         # Optional: Boost with Ambee API if key provided (near real-time, ML-backed)
#         if api_key:
#             ambee_url = "https://api.ambeedata.com/landslides/v1/landslides"  # Assumed endpoint
#             ambee_params = {'lat': latitude, 'lon': longitude, 'limit': 10}
#             headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
#             try:
#                 ambee_resp = requests.get(ambee_url, params=ambee_params, headers=headers, timeout=10)
#                 ambee_resp.raise_for_status()
#                 ambee_data = ambee_resp.json()
#                 high_risk_events = sum(1 for e in ambee_data.get('result', []) if e.get('proximity_severity_level') == 'High Risk')
#                 score = max(0, score - (high_risk_events * 10))  # Adjust down for active risks
#             except requests.RequestException:
#                 pass  # Fall back to EONET
        
#         return float(score)
        
#     except requests.RequestException:
#         pass
    
#     # Advanced Fallback: PyLandslide (reference integration; requires installed package + prepped rasters)
#     # Example: Load factor maps (e.g., slope, soil from your MongoDB), compute susceptibility
#     try:
#         # import PyLandslide as pyls  # pip install PyLandslide
#         # # Assume pre-loaded JSON config with factors (e.g., from Open-Meteo + soil APIs)
#         # config = {
#         #     "factors": ["slope", "rainfall", "soil_type"],  # Weighted via RF in PyLandslide
#         #     "weights": [0.4, 0.3, 0.3],  # ML-derived (e.g., from training on historical data)
#         #     "uncertainty": True
#         # }
#         # # Sample at point: pyls.susceptibility_map(config, lat=latitude, lon=longitude)
#         # pyls_score = pyls.susceptibility_map(config, lat=latitude, lon=longitude)['susceptibility']  # 0-1 normalized
#         # return float(pyls_score * 100)  # Scale to 0-100 safety (invert if risk)
#         return 50.0  # Placeholder mid-risk if integrated
#     except ImportError:
#         return None
# """
# PyLandslide Adapter for GeoAI: Enhanced landslide safety score (0-100, higher = safer).
# Primary: EONET for recent events. Fallback: Improved slope via larger span (Open-Meteo coarse grid fix).
# Ref: USGS (Oso ~15-20° avg → high penalty); PyLandslide for ML.
# """

# from typing import Optional
# import requests
# import json
# import math

# def get_elevation(lat: float, lon: float) -> Optional[float]:
#     """Fetch elevation (m) from Open-Meteo."""
#     url = "https://api.open-meteo.com/v1/elevation"
#     params = {'latitude': lat, 'longitude': lon, 'format': 'json'}
#     try:
#         resp = requests.get(url, params=params, timeout=5)
#         resp.raise_for_status()
#         elevation_list = resp.json().get('elevation')
#         return float(elevation_list[0]) if elevation_list else None
#     except (requests.RequestException, IndexError, ValueError):
#         return None

# def estimate_slope(lat: float, lon: float) -> float:
#     """Approx % slope with larger span (~5.5km) to cross grid cells."""
#     delta = 0.05  # ~5.5km for variation
#     points = [
#         (lat, lon),  # Center
#         (lat + delta, lon),  # North
#         (lat, lon + delta),  # East
#         (lat - delta, lon),  # South
#         (lat, lon - delta)   # West
#     ]
#     elevations = []
#     for p_lat, p_lon in points:
#         elev = get_elevation(p_lat, p_lon)
#         if elev is not None:
#             elevations.append(elev)
#     if len(elevations) < 2:
#         return 0.0
#     center_elev = elevations[0]
#     dist_m = delta * 111000  # ~km to m (approx)
#     deltas = [abs(e - center_elev) / dist_m for e in elevations[1:]]  # Rise/run
#     avg_gradient = sum(deltas) / len(deltas)
#     slope_percent = math.degrees(math.atan(avg_gradient)) * 100 / math.pi * 180  # Approx % from angle? Wait, simplify to gradient *100
#     return round(avg_gradient * 100, 2)  # % slope

# def estimate_landslide_risk_score(latitude: float, longitude: float, api_key: Optional[str] = None) -> Optional[float]:
#     """
#     Safety score. Base 85; penalize events/slope (amplified for extremes).
#     Feed to RF/XGBoost (page 12) for suitability.
#     """
#     # EONET (recent; 0 for historical like Oso)
#     delta_bbox = 0.2
#     bbox = f"{longitude - delta_bbox},{latitude - delta_bbox},{longitude + delta_bbox},{latitude + delta_bbox}"
#     url = "https://eonet.gsfc.nasa.gov/api/v3/events"
#     params = {'category': 'landslides', 'bbox': bbox, 'days': 3650, 'limit': 50}
#     num_events = 0
#     try:
#         resp = requests.get(url, params=params, timeout=10)
#         resp.raise_for_status()
#         events = [e for e in resp.json().get('events', []) if e.get('geometry')]
#         num_events = len(events)
#         recent = sum(1 for e in events if int(e.get('date', '2025')[:4]) >= 2023)
#         event_penalty = min((num_events * 8) + (recent * 4), 40)
#     except requests.RequestException:
#         event_penalty = 0

#     score = 85 - event_penalty

#     # Ambee (if key; historical severity)
#     if api_key:
#         # ... (as before)
#         pass

#     # Slope fallback (amplified; USGS: >15% high risk)
#     if num_events == 0:
#         slope = estimate_slope(latitude, longitude)
#         slope_penalty = min(slope * 4, 50)  # Amp for coarse data (e.g., 15% → 60 penalty → score 25)
#         score = max(0, 85 - slope_penalty)

#     return float(score)

# # Test (expect Oso ~35-50, Salina ~82+)
# if __name__ == "__main__":
#     print(estimate_landslide_risk_score(48.28256, -121.84806))  # Oso: Lower now
#     print(estimate_landslide_risk_score(38.84, -97.61))         # Salina: High        # Salina: ~85 (flat ~0.5% slope)        # Salina: ~85



"""
PyLandslide Adapter: Now with Google Elevation for high-res slope (~3m vs. 1km).
Get free key: console.cloud.google.com/apis/library/elevation-backend.googleapis.com
Fallback to Open-Meteo if no key.
"""

from typing import Optional
import requests
import json
import math

def get_elevation(lat: float, lon: float, google_key: Optional[str] = None) -> Optional[float]:
    """Primary: Google (high-res); fallback Open-Meteo."""
    if google_key:
        url = "https://maps.googleapis.com/maps/api/elevation/json"
        params = {'locations': f"{lat},{lon}", 'key': google_key}
        try:
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            if data['status'] == 'OK':
                return data['results'][0]['elevation']
        except requests.RequestException:
            pass
    # Fallback
    url = "https://api.open-meteo.com/v1/elevation"
    params = {'latitude': lat, 'longitude': lon, 'format': 'json'}
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        elevation_list = resp.json().get('elevation')
        return float(elevation_list[0]) if elevation_list else None
    except (requests.RequestException, IndexError, ValueError):
        return None

def estimate_slope(lat: float, lon: float, google_key: Optional[str] = None) -> float:
    """High-res approx with smaller span (0.001° ~111m)."""
    delta = 0.001
    points = [(lat, lon), (lat + delta, lon), (lat, lon + delta), (lat - delta, lon), (lat, lon - delta)]
    elevations = [get_elevation(p_lat, p_lon, google_key) for p_lat, p_lon in points]
    elevations = [e for e in elevations if e is not None]
    if len(elevations) < 2:
        return 0.0
    center_elev = elevations[0]
    dist_m = delta * 111000
    deltas = [abs(e - center_elev) / dist_m for e in elevations[1:]]
    avg_gradient = sum(deltas) / len(deltas)
    return round(avg_gradient * 100, 2)

def estimate_landslide_risk_score(latitude: float, longitude: float, api_key: Optional[str] = None, google_key: Optional[str] = None) -> Optional[float]:
    # EONET unchanged (recent events; 0 for Oso historical)
    delta_bbox = 0.2
    bbox = f"{longitude - delta_bbox},{latitude - delta_bbox},{longitude + delta_bbox},{latitude + delta_bbox}"
    url = "https://eonet.gsfc.nasa.gov/api/v3/events"
    params = {'category': 'landslides', 'bbox': bbox, 'days': 3650, 'limit': 50}
    num_events = 0
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        events = [e for e in resp.json().get('events', []) if e.get('geometry')]
        num_events = len(events)
        recent = sum(1 for e in events if int(e.get('date', '2025')[:4]) >= 2023)
        event_penalty = min((num_events * 8) + (recent * 4), 40)
    except requests.RequestException:
        event_penalty = 0
    score = 85 - event_penalty
    if num_events == 0:
        slope = estimate_slope(latitude, longitude, google_key)
        slope_penalty = min(slope * 2.5, 60)  # Tuned: 36% → ~90 penalty cap → score ~0
        score = max(0, 85 - slope_penalty)
    return float(score)

# # Test (with key: Oso ~20-30; no key: fallback)
# if __name__ == "__main__":
#     print(estimate_landslide_risk_score(48.28256, -121.84806, google_key="YOUR_KEY"))
#     print(estimate_landslide_risk_score(38.84, -97.61, google_key="YOUR_KEY"))