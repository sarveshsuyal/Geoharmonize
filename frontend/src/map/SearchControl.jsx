import React, { useState, useRef, useEffect, useCallback } from "react";
import L from "leaflet";
import api from "../services/api";
import { geocode } from "./geocodingApi.js";
import { geojsonBounds } from "./geoUtils.js";

const DEBOUNCE_MS = 350;

/**
 * Compact, collapsed-by-default GIS search. Two result groups:
 *  - GeoHarmonize: parcels matched via the existing /api/parcels/?search= endpoint
 *  - Places: addresses/localities/landmarks/coordinates via OpenStreetMap Nominatim geocoding
 *
 * This is a GIS-only search, isolated from the app's global search/nav.
 */
export default function SearchControl({ map }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [parcelResults, setParcelResults] = useState([]);
  const [placeResults, setPlaceResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeResult, setActiveResult] = useState(null);
  const markerRef = useRef(null);
  const debounceRef = useRef(null);

  const runSearch = useCallback(async (q) => {
    if (!q || q.trim().length < 2) {
      setParcelResults([]);
      setPlaceResults([]);
      return;
    }
    setLoading(true);
    try {
      const maybeLatLon = parseLatLonQuery(q);
      if (maybeLatLon) {
        setParcelResults([]);
        setPlaceResults([{ id: "latlon", name: `Coordinates: ${maybeLatLon.lat}, ${maybeLatLon.lon}`, center: [maybeLatLon.lon, maybeLatLon.lat], placeType: "coordinate" }]);
        setLoading(false);
        return;
      }

      // Reuse the existing /parcels/geojson/ endpoint (already bbox + search filterable,
      // already returns a proper FeatureCollection) instead of adding a new endpoint.
      const [parcelsRes, placesRes] = await Promise.allSettled([
        api.get("/parcels/geojson/", { params: { search: q } }),
        geocode(q, { limit: 5 }),
      ]);

      setParcelResults(
        parcelsRes.status === "fulfilled" ? (parcelsRes.value.data.features || []).slice(0, 5) : []
      );
      setPlaceResults(placesRes.status === "fulfilled" ? placesRes.value : []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSearch(query), DEBOUNCE_MS);
    return () => clearTimeout(debounceRef.current);
  }, [query, runSearch]);

  function clearMarker() {
    if (markerRef.current && map) {
      map.removeLayer(markerRef.current);
      markerRef.current = null;
    }
    setActiveResult(null);
  }

  function flyToPoint(lat, lon, label) {
    if (!map) return;
    clearMarker();
    map.flyTo([lat, lon], Math.max(map.getZoom(), 17), { duration: 0.8 });
    markerRef.current = L.marker([lat, lon]).addTo(map);
    setActiveResult(label);
  }

  function flyToBounds(bounds, label) {
    if (!map || !bounds) return;
    clearMarker();
    map.flyToBounds(bounds, { padding: [40, 40], duration: 0.8 });
    setActiveResult(label);
  }

  function handleSelectPlace(place) {
    if (place.bbox && place.bbox.length === 4) {
      const [minLon, minLat, maxLon, maxLat] = place.bbox;
      flyToBounds([[minLat, minLon], [maxLat, maxLon]], place.name);
    } else if (place.center) {
      flyToPoint(place.center[1], place.center[0], place.name);
    }
    setOpen(false);
  }

  function handleSelectParcel(feature) {
    const bounds = geojsonBounds(feature);
    const label = feature.properties?.parcel_id || `Parcel #${feature.id}`;
    if (bounds) flyToBounds(bounds, label);
    setOpen(false);
  }

  return (
    <div className="absolute top-3 left-32 z-[1000]">
      {!open ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-sm px-3 py-2 text-sm font-medium text-ink-800 hover:bg-white"
        >
          🔍 Search
        </button>
      ) : (
        <div className="w-72 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-md overflow-hidden">
          <div className="flex items-center gap-2 px-2.5 py-2 border-b border-ink-100">
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Address, place, lat/lon, parcel ID..."
              className="flex-1 text-sm outline-none px-1 py-0.5"
            />
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                setQuery("");
              }}
              className="text-ink-400 hover:text-ink-700 text-sm"
            >
              ✕
            </button>
          </div>

          <div className="max-h-72 overflow-y-auto">
            {loading && <div className="px-3 py-2 text-xs text-ink-400">Searching…</div>}

            {!loading && parcelResults.length > 0 && (
              <ResultGroup label="GeoHarmonize">
                {parcelResults.map((f) => (
                  <ResultRow
                    key={f.id}
                    onClick={() => handleSelectParcel(f)}
                    title={f.properties?.parcel_id || `Parcel #${f.id}`}
                    subtitle={f.properties?.survey_number || f.properties?.land_use || ""}
                  />
                ))}
              </ResultGroup>
            )}

            {!loading && placeResults.length > 0 && (
              <ResultGroup label="Places">
                {placeResults.map((p) => (
                  <ResultRow key={p.id} onClick={() => handleSelectPlace(p)} title={p.name} subtitle={p.placeType} />
                ))}
              </ResultGroup>
            )}

            {!loading && query.trim().length >= 2 && parcelResults.length === 0 && placeResults.length === 0 && (
              <div className="px-3 py-3 text-xs text-ink-400">No matches found.</div>
            )}
          </div>
        </div>
      )}

      {activeResult && !open && (
        <div className="mt-2 flex items-center gap-2 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-sm px-3 py-1.5 text-xs text-ink-700">
          <span className="truncate max-w-[180px]">{activeResult}</span>
          <button type="button" onClick={clearMarker} className="text-ink-400 hover:text-ink-700">
            ✕
          </button>
        </div>
      )}
    </div>
  );
}

function ResultGroup({ label, children }) {
  return (
    <div className="py-1">
      <div className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-ink-400">{label}</div>
      {children}
    </div>
  );
}

function ResultRow({ title, subtitle, onClick }) {
  return (
    <button type="button" onClick={onClick} className="w-full text-left px-3 py-1.5 hover:bg-ink-50">
      <div className="text-sm text-ink-800">{title}</div>
      {subtitle && <div className="text-xs text-ink-400">{subtitle}</div>}
    </button>
  );
}

/** Accepts "lat, lon" or "lat lon" style queries so users can paste coordinates straight into search. */
function parseLatLonQuery(q) {
  const m = q.trim().match(/^(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)$/);
  if (!m) return null;
  const lat = parseFloat(m[1]);
  const lon = parseFloat(m[2]);
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  return { lat, lon };
}
