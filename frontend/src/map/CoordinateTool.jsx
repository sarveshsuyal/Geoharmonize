import React, { useState, useRef, useEffect } from "react";
import L from "leaflet";
import { geojsonBounds, isValidLat, isValidLon } from "./geoUtils.js";

const MODES = [
  { key: "latlon", label: "Lat/Lon" },
  { key: "bbox", label: "Bounding box" },
  { key: "geojson", label: "GeoJSON" },
];

/**
 * Compact tool to jump to a coordinate, bounding box, or pasted GeoJSON
 * geometry. Temporary display only - nothing is persisted unless the user
 * later uses Select Area / Analyze Area explicitly.
 */
export default function CoordinateTool({ map }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState("latlon");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [bboxText, setBboxText] = useState("");
  const [geojsonText, setGeojsonText] = useState("");
  const [error, setError] = useState("");
  const [cursor, setCursor] = useState(null);

  const markerRef = useRef(null);
  const rectRef = useRef(null);

  useEffect(() => {
    if (!map) return;
    const onMove = (e) => setCursor(e.latlng);
    map.on("mousemove", onMove);
    return () => map.off("mousemove", onMove);
  }, [map]);

  function clearTemp() {
    if (markerRef.current && map) map.removeLayer(markerRef.current);
    if (rectRef.current && map) map.removeLayer(rectRef.current);
    markerRef.current = null;
    rectRef.current = null;
  }

  function submitLatLon() {
    const latVal = parseFloat(lat);
    const lonVal = parseFloat(lon);
    if (!isValidLat(latVal) || !isValidLon(lonVal)) {
      setError("Enter a valid latitude (-90 to 90) and longitude (-180 to 180).");
      return;
    }
    setError("");
    clearTemp();
    map.flyTo([latVal, lonVal], Math.max(map.getZoom(), 17), { duration: 0.8 });
    markerRef.current = L.marker([latVal, lonVal]).addTo(map);
  }

  function submitBbox() {
    const parts = bboxText.split(",").map((v) => parseFloat(v.trim()));
    if (parts.length !== 4 || parts.some((v) => !Number.isFinite(v))) {
      setError("Bounding box must be: minLon, minLat, maxLon, maxLat");
      return;
    }
    const [minLon, minLat, maxLon, maxLat] = parts;
    if (!isValidLon(minLon) || !isValidLon(maxLon) || !isValidLat(minLat) || !isValidLat(maxLat)) {
      setError("Bounding box coordinates are out of range.");
      return;
    }
    setError("");
    clearTemp();
    const bounds = [[minLat, minLon], [maxLat, maxLon]];
    map.flyToBounds(bounds, { padding: [40, 40], duration: 0.8 });
    rectRef.current = L.rectangle(bounds, { color: "#0e6690", weight: 2, fillOpacity: 0.08 }).addTo(map);
  }

  function submitGeojson() {
    let parsed;
    try {
      parsed = JSON.parse(geojsonText);
    } catch {
      setError("Could not parse GeoJSON - check the syntax.");
      return;
    }
    const bounds = geojsonBounds(parsed);
    if (!bounds) {
      setError("No valid coordinates found in that GeoJSON.");
      return;
    }
    setError("");
    clearTemp();
    map.flyToBounds(bounds, { padding: [40, 40], duration: 0.8 });
    rectRef.current = L.geoJSON(parsed, { style: { color: "#0e6690", weight: 2, fillOpacity: 0.08 } }).addTo(map);
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!map) return;
    if (mode === "latlon") submitLatLon();
    else if (mode === "bbox") submitBbox();
    else submitGeojson();
  }

  function handleClear() {
    clearTemp();
    setError("");
  }

  return (
    <div className="absolute top-16 left-3 z-[1000]">
      {!open ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-sm px-3 py-2 text-sm font-medium text-ink-800 hover:bg-white"
        >
          ⌖ Coordinates
        </button>
      ) : (
        <div className="w-72 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-md overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-ink-100">
            <div className="flex gap-1">
              {MODES.map((m) => (
                <button
                  key={m.key}
                  type="button"
                  onClick={() => {
                    setMode(m.key);
                    setError("");
                  }}
                  className={`text-[11px] px-2 py-1 rounded ${
                    mode === m.key ? "bg-brand-600 text-white" : "text-ink-600 hover:bg-ink-50"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
            <button type="button" onClick={() => setOpen(false)} className="text-ink-400 hover:text-ink-700 text-sm">
              ✕
            </button>
          </div>

          <form onSubmit={handleSubmit} className="px-3 py-2.5 space-y-2">
            {mode === "latlon" && (
              <div className="flex gap-2">
                <input
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                  placeholder="Latitude"
                  className="w-1/2 text-sm border border-ink-200 rounded px-2 py-1 outline-none focus:border-brand-500"
                />
                <input
                  value={lon}
                  onChange={(e) => setLon(e.target.value)}
                  placeholder="Longitude"
                  className="w-1/2 text-sm border border-ink-200 rounded px-2 py-1 outline-none focus:border-brand-500"
                />
              </div>
            )}

            {mode === "bbox" && (
              <input
                value={bboxText}
                onChange={(e) => setBboxText(e.target.value)}
                placeholder="minLon, minLat, maxLon, maxLat"
                className="w-full text-sm border border-ink-200 rounded px-2 py-1 outline-none focus:border-brand-500"
              />
            )}

            {mode === "geojson" && (
              <textarea
                value={geojsonText}
                onChange={(e) => setGeojsonText(e.target.value)}
                placeholder='{"type": "Polygon", "coordinates": [...] }'
                rows={4}
                className="w-full text-xs font-mono border border-ink-200 rounded px-2 py-1 outline-none focus:border-brand-500"
              />
            )}

            {error && <div className="text-xs text-status-low">{error}</div>}

            <div className="flex gap-2">
              <button type="submit" className="flex-1 bg-brand-600 text-white text-sm rounded px-2 py-1.5 hover:bg-brand-700">
                Go
              </button>
              <button type="button" onClick={handleClear} className="text-sm text-ink-600 border border-ink-200 rounded px-2 py-1.5 hover:bg-ink-50">
                Clear
              </button>
            </div>
          </form>

          {cursor && (
            <div className="px-3 py-1.5 border-t border-ink-100 text-[11px] text-ink-400 font-mono">
              Cursor: {cursor.lat.toFixed(5)}, {cursor.lng.toFixed(5)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
