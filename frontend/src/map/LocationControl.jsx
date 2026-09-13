import React, { useState, useRef, useEffect, useCallback } from "react";
import L from "leaflet";

/**
 * LocationControl: "My Location" / "Locate Me" tool for the Leaflet map.
 * Uses browser's native navigator.geolocation API.
 *
 * Features:
 *  - Centers map and zooms to ~17 on locate
 *  - Renders a distinctive current-location marker and accuracy circle
 *  - Handles errors: permission denied, position unavailable, timeout, no geolocation API
 *  - Single-shot by default; optional "Follow location" mode for live tracking
 *  - Does not conflict with GIS change-detection markers or parcel layers
 */
export default function LocationControl({ map }) {
  const [loading, setLoading] = useState(false);
  const [location, setLocation] = useState(null); // { lat, lon, accuracy }
  const [error, setError] = useState("");
  const [follow, setFollow] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);

  const markerRef = useRef(null);
  const circleRef = useRef(null);
  const watchIdRef = useRef(null);
  const followRef = useRef(false);

  // Keep followRef in sync with follow state for callbacks
  useEffect(() => {
    followRef.current = follow;
  }, [follow]);

  const clearLocation = useCallback(() => {
    if (watchIdRef.current !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    if (markerRef.current && map) {
      map.removeLayer(markerRef.current);
      markerRef.current = null;
    }
    if (circleRef.current && map) {
      map.removeLayer(circleRef.current);
      circleRef.current = null;
    }
    setLocation(null);
    setFollow(false);
    setPanelOpen(false);
    setError("");
  }, [map]);

  // Clean up markers and geolocation watch when unmounting or if map changes
  useEffect(() => {
    return () => {
      if (watchIdRef.current !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
      if (markerRef.current && map) {
        map.removeLayer(markerRef.current);
      }
      if (circleRef.current && map) {
        map.removeLayer(circleRef.current);
      }
    };
  }, [map]);

  const updateMapLayers = useCallback((lat, lon, accuracy, shouldFly = true) => {
    if (!map) return;

    // Remove existing layers if any
    if (markerRef.current) map.removeLayer(markerRef.current);
    if (circleRef.current) map.removeLayer(circleRef.current);

    // Create accuracy circle
    circleRef.current = L.circle([lat, lon], {
      radius: accuracy,
      color: "#2563eb",
      fillColor: "#3b82f6",
      fillOpacity: 0.12,
      weight: 1.5,
      opacity: 0.7,
    }).addTo(map);

    // Create custom pulsing location marker
    const locationIcon = L.divIcon({
      className: "current-location-marker",
      html: `
        <div style="position: relative; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center;">
          <div style="position: absolute; width: 22px; height: 22px; border-radius: 50%; background-color: rgba(37, 99, 235, 0.3); animation: ping 1.8s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
          <div style="position: relative; width: 14px; height: 14px; border-radius: 50%; background-color: #2563eb; border: 2.5px solid #ffffff; box-shadow: 0 1px 4px rgba(0,0,0,0.35);"></div>
        </div>
      `,
      iconSize: [22, 22],
      iconAnchor: [11, 11],
    });

    const marker = L.marker([lat, lon], { icon: locationIcon, zIndexOffset: 1000 }).addTo(map);
    marker.bindPopup(`
      <div style="font-family: Inter, system-ui, sans-serif; font-size: 12px; line-height: 1.4; color: #1e293b;">
        <div style="font-weight: 600; color: #0e6690; margin-bottom: 2px;">📍 Current Location</div>
        <div>Lat: ${lat.toFixed(6)}</div>
        <div>Lon: ${lon.toFixed(6)}</div>
        <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Accuracy: &plusmn;${Math.round(accuracy)}m</div>
      </div>
    `);
    markerRef.current = marker;

    if (shouldFly) {
      map.flyTo([lat, lon], Math.max(map.getZoom(), 17), { duration: 0.8 });
    } else if (followRef.current) {
      map.panTo([lat, lon]);
    }
  }, [map]);

  const handleLocationError = useCallback((err) => {
    setLoading(false);
    let msg = "An unexpected error occurred while retrieving location.";
    if (err.code === 1) {
      msg = "Location permission denied. Please allow location access in your browser.";
    } else if (err.code === 2) {
      msg = "Location unavailable. Unable to determine your position.";
    } else if (err.code === 3) {
      msg = "Location request timed out. Please try again.";
    }
    setError(msg);
  }, []);

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError("Browser geolocation is not supported in this environment.");
      return;
    }

    if (!map) return;

    setLoading(true);
    setError("");

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLoading(false);
        const { latitude, longitude, accuracy } = pos.coords;
        setLocation({ lat: latitude, lon: longitude, accuracy });
        setPanelOpen(true);
        updateMapLayers(latitude, longitude, accuracy, true);
      },
      (err) => {
        handleLocationError(err);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  }, [map, handleLocationError, updateMapLayers]);

  const handleToggleFollow = (enabled) => {
    setFollow(enabled);
    if (enabled) {
      if (!navigator.geolocation) return;
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
      watchIdRef.current = navigator.geolocation.watchPosition(
        (pos) => {
          const { latitude, longitude, accuracy } = pos.coords;
          setLocation({ lat: latitude, lon: longitude, accuracy });
          updateMapLayers(latitude, longitude, accuracy, false);
        },
        (err) => {
          handleLocationError(err);
          setFollow(false);
        },
        {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 5000,
        }
      );
    } else {
      if (watchIdRef.current !== null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
    }
  };

  const handleRecenter = () => {
    if (location && map) {
      map.flyTo([location.lat, location.lon], Math.max(map.getZoom(), 17), { duration: 0.8 });
    } else {
      requestLocation();
    }
  };

  return (
    <div className="absolute top-16 left-40 z-[1000]">
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={location ? () => setPanelOpen((v) => !v) : requestLocation}
          disabled={loading}
          title="Find my current location"
          className={`flex items-center gap-2 bg-white/95 backdrop-blur border rounded-md shadow-sm px-3 py-2 text-sm font-medium transition-colors ${
            location
              ? "border-brand-500 text-brand-700 bg-brand-50/50"
              : "border-ink-200 text-ink-800 hover:bg-white"
          }`}
        >
          {loading ? (
            <>
              <span className="inline-block w-3.5 h-3.5 border-2 border-brand-600 border-t-transparent rounded-full animate-spin"></span>
              <span>Locating…</span>
            </>
          ) : (
            <>
              <span>📍</span>
              <span>My Location</span>
              {location && (
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
              )}
            </>
          )}
        </button>

        {location && (
          <button
            type="button"
            onClick={handleRecenter}
            title="Re-center on my location"
            className="bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-sm px-2.5 py-2 text-sm font-medium text-ink-700 hover:bg-white"
          >
            🎯
          </button>
        )}
      </div>

      {/* Error alert */}
      {error && (
        <div className="mt-2 w-72 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-md p-2.5 shadow-md flex items-start justify-between gap-2">
          <div>
            <div className="font-semibold mb-0.5">Geolocation Error</div>
            <div>{error}</div>
          </div>
          <button
            type="button"
            onClick={() => setError("")}
            className="text-rose-400 hover:text-rose-700 font-bold px-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* Active Location Info & Follow Option */}
      {location && panelOpen && !error && (
        <div className="mt-2 w-72 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-md p-3 text-xs text-ink-700 space-y-2.5">
          <div className="flex items-center justify-between border-b border-ink-100 pb-1.5">
            <span className="font-semibold text-brand-600 flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Current Position
            </span>
            <button
              type="button"
              onClick={() => setPanelOpen(false)}
              className="text-ink-400 hover:text-ink-700 text-sm"
              title="Close panel"
            >
              ✕
            </button>
          </div>

          <div className="space-y-1 text-ink-600">
            <div className="flex justify-between">
              <span className="text-ink-400">Coordinates:</span>
              <span className="font-mono">{location.lat.toFixed(5)}, {location.lon.toFixed(5)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-400">Accuracy:</span>
              <span className="font-mono">&plusmn;{Math.round(location.accuracy)} m</span>
            </div>
          </div>

          <div className="pt-2 border-t border-ink-100 flex items-center justify-between">
            <label className="flex items-center gap-2 text-ink-700 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={follow}
                onChange={(e) => handleToggleFollow(e.target.checked)}
                className="rounded border-ink-300 text-brand-600 focus:ring-brand-500"
              />
              <span>Follow location</span>
            </label>

            <button
              type="button"
              onClick={clearLocation}
              className="text-rose-600 hover:text-rose-800 hover:underline"
            >
              Clear marker
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
