// src/components/LandSuitabilityChecker.js
import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import FactorBar from '../FactorBar/FactorBar';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import '../../App.css';

// Fix default marker icon issue in Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Component to handle map clicks
function LocationMarker({ lat, lng, setLat, setLng }) {
  const [position, setPosition] = useState({ lat, lng });

  useMapEvents({
    click(e) {
      setPosition(e.latlng);
      setLat(e.latlng.lat);
      setLng(e.latlng.lng);
    },
  });

  return position ? <Marker position={position} /> : null;
}

export default function LandSuitabilityChecker() {
  const [lat, setLat] = useState(17.3850);
  const [lng, setLng] = useState(78.4867);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [debug, setDebug] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    setResult(null);

    try {
      const url = debug ? '/suitability?debug=1' : '/suitability';
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latitude: lat, longitude: lng, debug }),
      });
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError('Failed to fetch suitability. Ensure backend is running on :5000');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const factors = result?.factors || {};

  return (
    <div className="App">
      <header>
        <h1>GeoAI Land Suitability</h1>
        <p className="subtitle">Click on the map to select a location</p>
      </header>

      {/* MAP */}
      <div className="panel">
        <MapContainer
          center={[lat, lng]}
          zoom={13}
          style={{ height: '400px', width: '100%' }} // fixed height is required
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
          />
          <LocationMarker lat={lat} lng={lng} setLat={setLat} setLng={setLng} />
        </MapContainer>
        <div style={{ marginTop: '10px' }}>
          Selected: Lat {lat.toFixed(4)}, Lng {lng.toFixed(4)}
        </div>
      </div>

      {/* FORM */}
      <form className="panel" onSubmit={handleSubmit}>
        <div className="row">
          <label htmlFor="lat">Latitude</label>
          <input
            id="lat"
            type="number"
            step="0.000001"
            value={lat}
            onChange={(e) => setLat(Number(e.target.value))}
          />
        </div>
        <div className="row">
          <label htmlFor="lng">Longitude</label>
          <input
            id="lng"
            type="number"
            step="0.000001"
            value={lng}
            onChange={(e) => setLng(Number(e.target.value))}
          />
        </div>
        <div className="row" style={{ gridTemplateColumns: 'auto auto auto' }}>
          <label>Debug</label>
          <input type="checkbox" checked={debug} onChange={(e) => setDebug(e.target.checked)} />
          <div />
        </div>
        <div className="row">
          <button type="submit" disabled={loading}>
            {loading ? 'Analyzing…' : 'Analyze'}
          </button>
        </div>
        {error && <div className="error">{error}</div>}
      </form>

      {/* RESULTS */}
      {result && (
        <div className="grid">
          <div className="panel">
            <h2>Overall Suitability</h2>
            <div className="score">
              <div className="score-value">{result.suitability_score?.toFixed?.(2)}</div>
              <div
                className={`score-badge ${
                  result.label?.toLowerCase()?.includes('high')
                    ? 'bad'
                    : result.label?.toLowerCase()?.includes('moderate')
                    ? 'warn'
                    : 'good'
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
    </div>
  );
}