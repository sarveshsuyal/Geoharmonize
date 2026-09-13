import React, { useState, useRef, useCallback, useEffect } from "react";
import L from "leaflet";
import api from "../services/api";
import { geodesicRingArea, formatArea, featureRoughlyIntersectsRing } from "./geoUtils.js";

// Reuses the exact same bbox-filtered GeoJSON endpoints the map layers already use -
// no new backend endpoint for this increment.
const COUNT_LAYERS = [
  { key: "parcels", label: "Harmonized Parcels", endpoint: "/parcels/geojson/" },
  { key: "buildings", label: "Buildings", endpoint: "/parcels/buildings/geojson/" },
  { key: "roads", label: "Roads", endpoint: "/parcels/roads/geojson/" },
  { key: "utilities", label: "Utilities", endpoint: "/parcels/utilities/geojson/" },
];

const SELECTION_STYLE = { color: "#0e6690", weight: 2, fillOpacity: 0.1 };
const PREVIEW_STYLE = { color: "#0e6690", weight: 2, fillOpacity: 0.12, dashArray: "4" };

// Anything past this is well beyond a single-parcel/site-scale selection; we still
// show the result, just flag it rather than pretending analysis at that scale is free.
const LARGE_AREA_WARNING_M2 = 20_000_000; // 20 km²

/**
 * "Select Area" GIS tool: explicit rectangle/polygon drawing (no drawing library
 * added - built on native Leaflet map events), a compact result panel with a
 * geodesic area figure, center, and an approximate GeoHarmonize feature count.
 *
 * "Analyze Area" is an architecture-ready placeholder only in this increment -
 * no AI backend exists yet, so it must not pretend to run analysis.
 *
 * Map behaves completely normally until this tool is explicitly activated, and
 * normal interaction (dragging, double-click zoom) is restored the moment
 * drawing ends, is cancelled, or the selection is cleared.
 */
export default function SelectAreaControl({ map, onAnalyzeArea }) {
  const [mode, setMode] = useState("idle"); // idle | choosing | drawing-polygon | drawing-rectangle | selected
  const [polyPointCount, setPolyPointCount] = useState(0);
  const [selection, setSelection] = useState(null); // { type, areaM2, center, bounds }
  const [counts, setCounts] = useState(null); // { parcels, buildings, roads, utilities, capped }
  const [countsLoading, setCountsLoading] = useState(false);
  const [error, setError] = useState("");
  const [analyzeNotice, setAnalyzeNotice] = useState(false);

  const previewLayerRef = useRef(null);
  const finalLayerRef = useRef(null);
  const pointsRef = useRef([]);
  const rectStartRef = useRef(null);
  const handlersRef = useRef({});

  const removeLayer = useCallback(
    (ref) => {
      if (ref.current && map) map.removeLayer(ref.current);
      ref.current = null;
    },
    [map]
  );

  const restoreMapInteraction = useCallback(() => {
    if (!map) return;
    map.dragging.enable();
    map.doubleClickZoom.enable();
  }, [map]);

  const detachDrawHandlers = useCallback(() => {
    if (!map) return;
    const h = handlersRef.current;
    if (h.click) map.off("click", h.click);
    if (h.dblclick) map.off("dblclick", h.dblclick);
    if (h.mousedown) map.off("mousedown", h.mousedown);
    if (h.mousemove) map.off("mousemove", h.mousemove);
    if (h.mouseup) map.off("mouseup", h.mouseup);
    handlersRef.current = {};
    restoreMapInteraction();
  }, [map, restoreMapInteraction]);

  // Safety net: if the component unmounts mid-draw, don't leave dangling map listeners.
  useEffect(() => () => detachDrawHandlers(), [detachDrawHandlers]);

  function resetAll() {
    detachDrawHandlers();
    removeLayer(previewLayerRef);
    removeLayer(finalLayerRef);
    pointsRef.current = [];
    rectStartRef.current = null;
    setPolyPointCount(0);
    setSelection(null);
    setCounts(null);
    setError("");
    setAnalyzeNotice(false);
    setMode("idle");
  }

  function cancelDrawing(message) {
    detachDrawHandlers();
    removeLayer(previewLayerRef);
    pointsRef.current = [];
    rectStartRef.current = null;
    setPolyPointCount(0);
    if (message) setError(message);
    setMode("choosing");
  }

  // ---------- Polygon drawing ----------
  function startPolygonDraw() {
    if (!map) return;
    setError("");
    pointsRef.current = [];
    setPolyPointCount(0);
    map.doubleClickZoom.disable();

    const onClick = (e) => {
      pointsRef.current.push(e.latlng);
      setPolyPointCount(pointsRef.current.length);
      removeLayer(previewLayerRef);
      previewLayerRef.current =
        pointsRef.current.length < 2
          ? L.circleMarker(pointsRef.current[0], { radius: 4, color: "#0e6690" }).addTo(map)
          : L.polygon(pointsRef.current, PREVIEW_STYLE).addTo(map);
    };
    const onDblClick = (e) => {
      if (e.originalEvent?.preventDefault) e.originalEvent.preventDefault();
      finishPolygon();
    };

    handlersRef.current = { click: onClick, dblclick: onDblClick };
    map.on("click", onClick);
    map.on("dblclick", onDblClick);
    setMode("drawing-polygon");
  }

  function finishPolygon() {
    if (pointsRef.current.length < 3) {
      cancelDrawing("Draw at least 3 points to form a polygon.");
      return;
    }
    const latlngs = [...pointsRef.current];
    detachDrawHandlers();
    removeLayer(previewLayerRef);
    finalizeSelection(latlngs, "Polygon");
  }

  // ---------- Rectangle drawing ----------
  function startRectangleDraw() {
    if (!map) return;
    setError("");
    map.dragging.disable();

    const onMouseDown = (e) => {
      rectStartRef.current = e.latlng;
      map.on("mousemove", onMouseMove);
      map.on("mouseup", onMouseUp);
    };
    const onMouseMove = (e) => {
      if (!rectStartRef.current) return;
      const bounds = L.latLngBounds(rectStartRef.current, e.latlng);
      removeLayer(previewLayerRef);
      previewLayerRef.current = L.rectangle(bounds, PREVIEW_STYLE).addTo(map);
    };
    const onMouseUp = (e) => {
      map.off("mousemove", onMouseMove);
      map.off("mouseup", onMouseUp);
      const start = rectStartRef.current;
      rectStartRef.current = null;
      if (!start) return;
      const bounds = L.latLngBounds(start, e.latlng);
      if (bounds.getNorthEast().distanceTo(bounds.getSouthWest()) < 1) {
        cancelDrawing("Drag to draw a rectangle - that click had no area.");
        return;
      }
      const corners = [bounds.getSouthWest(), bounds.getNorthWest(), bounds.getNorthEast(), bounds.getSouthEast()];
      detachDrawHandlers();
      removeLayer(previewLayerRef);
      finalizeSelection(corners, "Rectangle");
    };

    handlersRef.current = { mousedown: onMouseDown };
    map.on("mousedown", onMouseDown);
    setMode("drawing-rectangle");
  }

  // ---------- Shared finalize ----------
  function finalizeSelection(latlngs, type) {
    const ring = latlngs.map((ll) => [ll.lng, ll.lat]);
    ring.push(ring[0]);
    const areaM2 = geodesicRingArea(ring);

    if (!areaM2 || areaM2 < 1) {
      setError("That selection has no measurable area - try drawing a larger shape.");
      setMode("choosing");
      return;
    }

    const bounds = L.latLngBounds(latlngs);
    const center = bounds.getCenter();

    finalLayerRef.current = L.polygon(latlngs, SELECTION_STYLE).addTo(map);

    setSelection({ type, ring, latlngs, areaM2, center, bounds });
    setMode("selected");
    fetchFeatureCounts(bounds, ring);
  }

  async function fetchFeatureCounts(bounds, ring) {
    setCountsLoading(true);
    setCounts(null);
    try {
      const bbox = [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()].join(",");
      const responses = await Promise.allSettled(
        COUNT_LAYERS.map((layer) => api.get(layer.endpoint, { params: { bbox } }))
      );

      const result = {};
      let anyCapped = false;
      responses.forEach((res, i) => {
        const layer = COUNT_LAYERS[i];
        if (res.status !== "fulfilled") {
          result[layer.key] = null; // unavailable, not zero - don't invent a number
          return;
        }
        const features = res.value.data?.features || [];
        if (features.length >= 2000) anyCapped = true; // matches backend's hard cap
        result[layer.key] = features.filter((f) => featureRoughlyIntersectsRing(f, ring)).length;
      });
      setCounts({ ...result, capped: anyCapped });
    } catch {
      setCounts(null);
    } finally {
      setCountsLoading(false);
    }
  }

  function handleAnalyzeArea() {
    if (onAnalyzeArea && selection) {
      onAnalyzeArea({
        type: selection.type,
        ring: selection.ring,
        bounds: [
          selection.bounds.getWest(),
          selection.bounds.getSouth(),
          selection.bounds.getEast(),
          selection.bounds.getNorth(),
        ],
        areaM2: selection.areaM2,
        center: selection.center,
        geojson: {
          type: "Polygon",
          coordinates: [selection.ring],
        },
      });
      resetAll();
    } else {
      setAnalyzeNotice(true);
    }
  }

  const totalFeatures = counts
    ? COUNT_LAYERS.reduce((sum, l) => sum + (counts[l.key] || 0), 0)
    : null;

  return (
    <div className="absolute top-3 left-72 z-[1000]">
      {mode === "idle" && (
        <button
          type="button"
          onClick={() => setMode("choosing")}
          className="flex items-center gap-2 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-sm px-3 py-2 text-sm font-medium text-ink-800 hover:bg-white"
        >
          ▭ Select Area
        </button>
      )}

      {mode === "choosing" && (
        <div className="w-56 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-md p-2.5 space-y-1.5">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-400 px-0.5">Select Area</div>
          {error && <div className="text-xs text-status-low px-0.5">{error}</div>}
          <button type="button" onClick={startPolygonDraw} className="w-full text-left text-sm px-2 py-1.5 rounded border border-ink-200 text-ink-700 hover:bg-ink-50">
            ⬠ Draw Polygon
          </button>
          <button type="button" onClick={startRectangleDraw} className="w-full text-left text-sm px-2 py-1.5 rounded border border-ink-200 text-ink-700 hover:bg-ink-50">
            ▭ Draw Rectangle
          </button>
          <button type="button" onClick={resetAll} className="w-full text-left text-sm px-2 py-1.5 rounded text-ink-500 hover:bg-ink-50">
            Cancel
          </button>
        </div>
      )}

      {mode === "drawing-polygon" && (
        <div className="w-64 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-md p-2.5 space-y-2">
          <div className="text-sm text-ink-700">
            Click to add points ({polyPointCount} so far). Double-click to finish.
          </div>
          <div className="flex gap-2">
            {polyPointCount >= 3 && (
              <button type="button" onClick={finishPolygon} className="flex-1 bg-brand-600 text-white text-sm rounded px-2 py-1.5 hover:bg-brand-700">
                Finish
              </button>
            )}
            <button type="button" onClick={() => cancelDrawing()} className="flex-1 text-sm text-ink-600 border border-ink-200 rounded px-2 py-1.5 hover:bg-ink-50">
              Cancel
            </button>
          </div>
        </div>
      )}

      {mode === "drawing-rectangle" && (
        <div className="w-64 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-md p-2.5 space-y-2">
          <div className="text-sm text-ink-700">Click and drag on the map to draw a rectangle.</div>
          <button type="button" onClick={() => cancelDrawing()} className="w-full text-sm text-ink-600 border border-ink-200 rounded px-2 py-1.5 hover:bg-ink-50">
            Cancel
          </button>
        </div>
      )}

      {mode === "selected" && selection && (
        <div className="w-72 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-md overflow-hidden">
          <div className="px-3 py-2 border-b border-ink-100 flex items-center justify-between">
            <div className="text-sm font-semibold text-ink-800">Selected Area</div>
            <button type="button" onClick={resetAll} className="text-ink-400 hover:text-ink-700 text-sm">
              ✕
            </button>
          </div>

          <div className="px-3 py-2.5 text-sm space-y-1.5">
            <Row label="Area" value={formatArea(selection.areaM2)} />
            <Row label="Center" value={`${selection.center.lat.toFixed(6)}, ${selection.center.lng.toFixed(6)}`} />
            <Row
              label="GeoHarmonize Features"
              value={countsLoading ? "Counting…" : totalFeatures === null ? "Unavailable" : totalFeatures}
            />

            {counts && !countsLoading && (
              <div className="pl-2 border-l-2 border-ink-100 space-y-0.5 text-xs text-ink-500">
                {COUNT_LAYERS.map((l) => (
                  <div key={l.key} className="flex justify-between">
                    <span>{l.label}</span>
                    <span>{counts[l.key] === null ? "—" : counts[l.key]}</span>
                  </div>
                ))}
                {counts.capped && <div className="text-status-medium">Some layers hit the query cap - count may be a lower bound.</div>}
                <div className="italic">Approximate: based on feature vertices, not exact polygon clipping.</div>
              </div>
            )}

            {selection.areaM2 > LARGE_AREA_WARNING_M2 && (
              <div className="text-xs text-status-medium pt-1">
                Large selection ({formatArea(selection.areaM2)}) - future analysis may need a smaller area.
              </div>
            )}
          </div>

          <div className="px-3 pb-3 flex gap-2">
            <button
              type="button"
              onClick={handleAnalyzeArea}
              className="flex-1 bg-brand-600 text-white text-sm font-medium rounded px-2 py-1.5 hover:bg-brand-700 flex items-center justify-center gap-1.5 shadow-sm"
            >
              <span>⚡</span> AI Analyze Area
            </button>
            <button type="button" onClick={resetAll} className="flex-1 text-sm text-ink-600 border border-ink-200 rounded px-2 py-1.5 hover:bg-ink-50">
              Clear Selection
            </button>
          </div>

          {analyzeNotice && !onAnalyzeArea && (
            <div className="mx-3 mb-3 text-xs text-ink-500 bg-ink-50 border border-ink-100 rounded px-2.5 py-2">
              AI analysis will be connected in the next GIS analysis increment. This selection (area, bounds, and
              feature count above) is exactly what that step will use as input.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between">
      <span className="text-ink-500">{label}</span>
      <span className="text-ink-800 font-medium text-right">{value}</span>
    </div>
  );
}
