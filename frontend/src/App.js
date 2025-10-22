
// import React, { useState } from 'react';
// import './App.css';

// function FactorBar({ label, value }) {
//   const width = Math.max(0, Math.min(100, Number(value || 0)));
//   return (
//     <div className="factor">
//       <div className="factor-header">
//         <span>{label}</span>
//         <span className="factor-value">{width.toFixed(1)}</span>
//       </div>
//       <div className="bar">
//         <div className="bar-fill" style={{ width: `${width}%` }} />
//       </div>
//     </div>
//   );
// }

// function App() {
//   const [lat, setLat] = useState(17.3850);
//   const [lng, setLng] = useState(78.4867);
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState('');
//   const [debug, setDebug] = useState(false);

//   const [result, setResult] = useState(null);

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     setError('');
//     setLoading(true);
//     setResult(null);
//     try {
//       const url = debug ? '/suitability?debug=1' : '/suitability';
//       const response = await fetch(url, {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ latitude: Number(lat), longitude: Number(lng), debug })
//       });
//       if (!response.ok) throw new Error('Network response was not ok');
//       const data = await response.json();
//       setResult(data);
//     } catch (err) {
//       setError('Failed to fetch suitability. Ensure backend is running on :5000');
//       console.error('Fetch error:', err);
//     } finally {
//       setLoading(false);
//     }
//   };

//   const factors = result?.factors || {};

//   return (
//     <div className="App">
//       <header>
//         <h1>GeoAI Land Suitability</h1>
//         <p className="subtitle">Unified, factor-based scoring from your geospatial toolchain</p>
//       </header>

//       <form className="panel" onSubmit={handleSubmit}>
//         <div className="row">
//           <label>Latitude</label>
//           <input type="number" step="0.0001" value={lat} onChange={(e) => setLat(e.target.value)} />
//           <label>Longitude</label>
//           <input type="number" step="0.0001" value={lng} onChange={(e) => setLng(e.target.value)} />
//           <button type="submit" disabled={loading}>{loading ? 'Scoring…' : 'Score Land'}</button>
//         </div>
//         <div className="row" style={{ gridTemplateColumns: 'auto auto auto' }}>
//           <label>Debug</label>
//           <input type="checkbox" checked={debug} onChange={(e) => setDebug(e.target.checked)} />
//           <div />
//         </div>
//         {error && <div className="error">{error}</div>}
//       </form>

//       {result && (
//         <div className="grid">
//           <div className="panel">
//             <h2>Overall Suitability</h2>
//             <div className="score">
//               <div className="score-value">{result.suitability_score?.toFixed?.(2)}</div>
//               <div className={`score-badge ${result.label?.toLowerCase()?.includes('high') ? 'bad' : result.label?.toLowerCase()?.includes('moderate') ? 'warn' : 'good'}`}>{result.label}</div>
//             </div>
//             <div className="meta">
//               <div>Lat: {result.location?.latitude}</div>
//               <div>Lng: {result.location?.longitude}</div>
//               <div>{result.timestamp}</div>
//             </div>
//           </div>

//           <div className="panel">
//             <h2>Factor Breakdown (0–100)</h2>
//             <FactorBar label="Rainfall (normalized)" value={factors.rainfall} />
//             <FactorBar label="Flood Safety" value={factors.flood} />
//             <FactorBar label="Landslide Safety" value={factors.landslide} />
//             <FactorBar label="Soil Quality" value={factors.soil} />
//             <FactorBar label="Proximity (access/markets)" value={factors.proximity} />
//             <FactorBar label="Water Proximity (further is safer)" value={factors.water} />
//             <FactorBar label="Air Quality (lower PM2.5 is better)" value={factors.pollution} />
//             <FactorBar label="Landuse Compatibility" value={factors.landuse} />
//             <div className="hint">Missing factors default to neutral 50. Extend adapters to enrich.</div>
//           </div>
//           {result?.evidence?.water_distance_km != null && (
//             <div className="panel">
//               <h2>Evidence</h2>
//               <div>Nearest water body distance: {result.evidence.water_distance_km} km</div>
//               {result?.debug && (
//                 <pre style={{ textAlign: 'left', whiteSpace: 'pre-wrap' }}>{JSON.stringify(result.debug, null, 2)}</pre>
//               )}
//             </div>
//           )}
//         </div>
//       )}
//     </div>
//   );
// }

// export default App;









// import React, { useState } from 'react';
// import './App.css';

// function App() {
//   const [score, setScore] = useState('');
//   const [risk, setRisk] = useState('');

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     const response = await fetch('http://localhost:5000/predict', {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify({ latitude: 17.3850, longitude: 78.4867 })
//     });
//     const data = await response.json();
//     setScore(data.suitability_score);
//     setRisk(data.risk_flags);
//   };

//   return (
//     <div className="App">
//       <h1>Land Suitability Checker</h1>
//       <button onClick={handleSubmit}>Check Suitability</button>
//       <p>Score: {score}</p>
//       <p>Risk: {risk}</p>
//     </div>
//   );
// }

// export default App;

// src/App.js
import React from 'react';
import './App.css';
import LandSuitabilityChecker from './components/LandSuitabilityChecker/LandSuitabilityChecker';

function App() {
  return (
    <div className="App">
      <LandSuitabilityChecker />
    </div>
  );
}

export default App;
