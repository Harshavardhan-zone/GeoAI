// src/components/LandSuitabilityChecker.js
import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from "react-leaflet";
import FactorBar from "../FactorBar/FactorBar";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import "../../App.css";
import "./LandSuitabilityChecker.css"

// Fix default marker icon issue in Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// 📍 Component to handle map clicks
function LocationMarker({ lat, lng, setLat, setLng }) {
  const [position, setPosition] = useState({ lat, lng });
  const map = useMap();

  useMapEvents({
    click(e) {
      setPosition(e.latlng);
      setLat(e.latlng.lat);
      setLng(e.latlng.lng);
    },
  });

  // update marker position when lat/lng change manually
  useEffect(() => {
    setPosition({ lat, lng });
    map.setView([lat, lng], map.getZoom());
  }, [lat, lng, map]);

  return position ? <Marker position={position} /> : null;
}

export default function LandSuitabilityChecker() {
  const [lat, setLat] = useState(17.385);
  const [lng, setLng] = useState(78.4867);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [debug, setDebug] = useState(false);
  const [result, setResult] = useState(null);

  // Saved places (persisted in localStorage)
  const [savedPlaces, setSavedPlaces] = useState(() => {
    const stored = localStorage.getItem("savedPlaces");
    return stored ? JSON.parse(stored) : [];
  });

  // My Location button functionality
  const handleMyLocation = () => {
    if (!navigator.geolocation) {
      alert("Geolocation not supported by this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLng(pos.coords.longitude);
      },
      (err) => {
        alert("Failed to get location: " + err.message);
      }
    );
  };

  // 💾 Save current location
  const handleSavePlace = () => {
    const name = prompt("Enter a name for this location:");
    if (!name) return;
    const newPlace = { name, lat, lng };
    const updated = [...savedPlaces, newPlace];
    setSavedPlaces(updated);
    localStorage.setItem("savedPlaces", JSON.stringify(updated));
  };

  //  Jump to a saved location
  const handleSelectPlace = (place) => {
    setLat(place.lat);
    setLng(place.lng);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    setResult(null);

    try {
      const url = debug ? "/suitability?debug=1" : "/suitability";
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ latitude: lat, longitude: lng, debug }),
      });
      if (!response.ok) throw new Error("Network response was not ok");
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError("Failed to fetch suitability. Ensure backend is running on :5000");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const factors = result?.factors || {};

  return (
    <div className="App">
      <header>
        <h1>🌍 GeoAI Land Suitability</h1>
      </header>

      {/* MAP SECTION */}
      <div className="panel">
        <MapContainer
          center={[lat, lng]}
          zoom={13}
          style={{ height: "400px", width: "100%" }}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
          />
          <LocationMarker lat={lat} lng={lng} setLat={setLat} setLng={setLng} />
        </MapContainer>
        <div style={{ marginTop: "10px" }}>
          Selected: Lat {lat.toFixed(4)}, Lng {lng.toFixed(4)}
        </div>
        <button onClick={handleMyLocation} style={{ marginTop: "10px" }}>
          📍 My Location
        </button>
      </div>

      

     {/* FORM SECTION */}
<form className="panel" onSubmit={handleSubmit}>
  <div className="form-row">
    <div className="form-group">
      <label htmlFor="lat">Latitude</label>
      <input
        id="lat"
        type="number"
        step="0.000001"
        value={lat}
        onChange={(e) => setLat(Number(e.target.value))}
      />
    </div>
    <div className="form-group">
      <label htmlFor="lng">Longitude</label>
      <input
        id="lng"
        type="number"
        step="0.000001"
        value={lng}
        onChange={(e) => setLng(Number(e.target.value))}
      />
    </div>
  </div>

  <div className="debug-row">
    <label>
      <input
        type="checkbox"
        checked={debug}
        onChange={(e) => setDebug(e.target.checked)}
      />{" "}
      Enable debug mode
    </label>
  </div>

  <div className="button-row">
    <button type="submit" disabled={loading}>
      {loading ? "Analyzing…" : "Analyze"}
    </button>
    <button type="button" className="save-btn" onClick={handleSavePlace}>
      ⭐ Save This Place
    </button>
  </div>
  {error && <div className="error">{error}</div>}
</form>

  
 {/* SAVED PLACES */}
<div className="saved-places">
  <h3>📍 Saved Places</h3>
  {savedPlaces.length === 0 ? (
    <p className="no-places">
      No saved places yet. Click "Save This Place" to bookmark locations.
    </p>
  ) : (
    <div className="saved-grid">
      {savedPlaces.map((place, i) => (
        <div
          key={i}
          className="saved-item"
          onClick={() => handleSelectPlace(place)}
        >
          <div className="place-name">{place.name}</div>
          <div className="place-coords">
            {place.lat.toFixed(3)}, {place.lng.toFixed(3)}
          </div>
        </div>
      ))}
    </div>
  )}
</div>



      {/* RESULTS SECTION */}
      {result && (
        <div className="grid">
          <div className="panel">
            <h2>Overall Suitability</h2>
            <div className="score">
              <div className="score-value">{result.suitability_score?.toFixed?.(2)}</div>
              <div
                className={`score-badge ${
                  result.label?.toLowerCase()?.includes("high")
                    ? "bad"
                    : result.label?.toLowerCase()?.includes("moderate")
                    ? "warn"
                    : "good"
                }`}
              >
                {result.label}
              </div>
            </div>
            <div className="meta">
              <div>Lat: {result.location?.latitude}</div>
              <div>Lng: {result.location?.longitude}</div>
              <div>{result.timestamp}</div>
            </div>
          </div>

          <div className="panel">
            <h2>Factor Breakdown (0–100)</h2>
            <FactorBar label="Rainfall (normalized)" value={factors.rainfall} />
            <FactorBar label="Flood Safety" value={factors.flood} />
            <FactorBar label="Landslide Safety" value={factors.landslide} />
            <FactorBar label="Soil Quality" value={factors.soil} />
            <FactorBar label="Proximity (access/markets)" value={factors.proximity} />
            <FactorBar label="Water Proximity (further is safer)" value={factors.water} />
            <FactorBar label="Air Quality (lower PM2.5 is better)" value={factors.pollution} />
            <FactorBar label="Landuse Compatibility" value={factors.landuse} />
            <div className="hint">Missing factors default to neutral 50.</div>
          </div>
        </div>
        
      )}
      {/* TEAM SECTION */}
      <div className="panel" style={{ marginTop: '16px' }}>
        <h2>Project Team</h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '12px'
        }}>
          <div className="card" style={{ padding: '12px', borderRadius: 8, background: '#1b1f2a', border: '1px solid #2f3b52' }}>
            <div style={{ fontWeight: 700, fontSize: 16, color: '#f5f7fb' }}>Adepu Vaishnavi</div>
            <div style={{ color: '#c9d4f1' }}></div>
          </div>
          <div className="card" style={{ padding: '12px', borderRadius: 8, background: '#1b1f2a', border: '1px solid #2f3b52' }}>
            <div style={{ fontWeight: 700, fontSize: 16, color: '#f5f7fb' }}>Chinni Jyothika</div>
            <div style={{ color: '#c9d4f1' }}></div>
          </div>
          <div className="card" style={{ padding: '12px', borderRadius: 8, background: '#1b1f2a', border: '1px solid #2f3b52' }}>
            <div style={{ fontWeight: 700, fontSize: 16, color: '#f5f7fb' }}>Harsha vardhan Botlagunta</div>
            <div style={{ color: '#c9d4f1' }}></div>
          </div>
          <div className="card" style={{ padding: '12px', borderRadius: 8, background: '#1b1f2a', border: '1px solid #2f3b52' }}>
            <div style={{ fontWeight: 700, fontSize: 16, color: '#f5f7fb' }}>Maganti Pranathi</div>
            <div style={{ color: '#c9d4f1' }}></div>
          </div>
        </div>
        <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px dashed #333' }}>
          <div style={{ fontSize: 14, color: 'black' }}>Guide</div>
          <div style={{ fontWeight: 700, fontSize: 16, color: 'black' }}>G. Naga Chandrika</div>
        </div>
      </div>
    </div>
  );
}




