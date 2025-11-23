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
        slope_penalty = min(slope * 2.5, 60)  
        score = max(0, 85 - slope_penalty)
    return float(score)

