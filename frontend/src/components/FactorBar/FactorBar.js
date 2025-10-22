import React from 'react';
import '../../App.css'

function FactorBar({ label, value }) {
  const width = Math.max(0, Math.min(100, Number(value || 0)));
  return (
    <div className="factor">
      <div className="factor-header">
        <span>{label}</span>
        <span className="factor-value">{width.toFixed(1)}</span>
      </div>
      <div className="bar">
        <div className="bar-fill" style={{ width: `${width}%` }} />

      </div>
    </div>
  );
}
export default FactorBar;
