import React, { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { MapContainer, TileLayer, GeoJSON, useMapEvents, useMap } from "react-leaflet";
import api from "../services/api";
import LayerControl from "../map/LayerControl.jsx";
import SearchControl from "../map/SearchControl.jsx";
import CoordinateTool from "../map/CoordinateTool.jsx";
import SelectAreaControl from "../map/SelectAreaControl.jsx";
import LocationControl from "../map/LocationControl.jsx";
import AIAnalysisOverlay from "../map/AIAnalysisOverlay.jsx";
import AIAnalysisPanel from "../map/AIAnalysisPanel.jsx";
import { DEFAULT_BASEMAP_KEY, getBasemap } from "../map/basemaps.js";

const LAYER_CONFIG = [
  { key: "parcels", label: "All Parcels", endpoint: "/parcels/geojson/", color: "#0e6690" },
  { key: "harmonized", label: "Harmonized Only", endpoint: "/parcels/geojson/?is_harmonized=true", color: "#10b981" },
  { key: "unmatched", label: "Unmatched Gaps", endpoint: "/parcels/geojson/?unmatched=true", color: "#ef4444" },
  { key: "buildings", label: "Buildings", endpoint: "/parcels/buildings/geojson/", color: "#b45309" },
  { key: "roads", label: "Roads", endpoint: "/parcels/roads/geojson/", color: "#475569" },
  { key: "utilities", label: "Utilities", endpoint: "/parcels/utilities/geojson/", color: "#1d4ed8" },
];

const DATASET_PALETTE = ["#8b5cf6", "#f59e0b", "#06b6d4", "#ec4899", "#6366f1", "#14b8a6", "#f97316"];

function BoundsWatcher({ onBoundsChange }) {
  useMapEvents({
    moveend: (e) => onBoundsChange(e.target.getBounds()),
    load: (e) => onBoundsChange(e.target.getBounds()),
  });
  return null;
}

function ResetViewController({ resetSignal, center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (resetSignal > 0) map.setView(center, zoom);
  }, [resetSignal, center, zoom, map]);
  return null;
}

function MapInstanceBridge({ onReady }) {
  const map = useMap();
  useEffect(() => {
    onReady(map);
  }, [map, onReady]);
  return null;
}

function confidenceColor(feature) {
  const band = feature?.properties?.confidence_band;
  if (band === "HIGH") return "#15803d";
  if (band === "MEDIUM") return "#b45309";
  if (band === "LOW") return "#b91c1c";
  return "#0e6690";
}

function computeGeoJsonBounds(data) {
  if (!data || !data.features || data.features.length === 0) return null;
  let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity;
  let hasValid = false;

  function processCoords(coords) {
    if (typeof coords[0] === "number" && typeof coords[1] === "number") {
      const lng = coords[0];
      const lat = coords[1];
      if (Number.isFinite(lat) && Number.isFinite(lng)) {
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
        minLng = Math.min(minLng, lng);
        maxLng = Math.max(maxLng, lng);
        hasValid = true;
      }
    } else if (Array.isArray(coords)) {
      coords.forEach(processCoords);
    }
  }

  data.features.forEach((f) => {
    if (f.geometry && f.geometry.coordinates) {
      processCoords(f.geometry.coordinates);
    }
  });

  if (!hasValid) return null;
  return [[minLat, minLng], [maxLat, maxLng]];
}

const DEFAULT_CENTER = [29.0588, 77.7064];
const DEFAULT_ZOOM = 16;

export default function MapPage() {
  const [activeLayers, setActiveLayers] = useState({ parcels: true, harmonized: false, unmatched: false, buildings: false, roads: false, utilities: false });
  const [datasets, setDatasets] = useState([]);
  const [activeDatasetLayers, setActiveDatasetLayers] = useState({});
  const [layerData, setLayerData] = useState({});
  const [datasetLayerData, setDatasetLayerData] = useState({});
  const [selectedParcel, setSelectedParcel] = useState(null);
  const [bounds, setBounds] = useState(null);
  const [basemapKey, setBasemapKey] = useState(DEFAULT_BASEMAP_KEY);
  const [resetSignal, setResetSignal] = useState(0);
  const [mapInstance, setMapInstance] = useState(null);
  const hasAutoFitted = useRef(false);

  // AI Analysis state
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiAnalyzing, setAiAnalyzing] = useState(false);
  const [aiProgressStep, setAiProgressStep] = useState(0);
  const [showAILandUse, setShowAILandUse] = useState(true);
  const [aiLandUseOpacity, setAiLandUseOpacity] = useState(0.40);
  const [showAIRecs, setShowAIRecs] = useState(true);
  const [aiSelectedFeature, setAiSelectedFeature] = useState(null);

  const handleRunAIAnalysis = useCallback(async (selectionData) => {
    setAiAnalyzing(true);
    setAiProgressStep(0);
    setAiSelectedFeature(null);

    const t1 = setTimeout(() => setAiProgressStep(1), 350);
    const t2 = setTimeout(() => setAiProgressStep(2), 750);
    const t3 = setTimeout(() => setAiProgressStep(3), 1200);
    const t4 = setTimeout(() => setAiProgressStep(4), 1600);

    try {
      const res = await api.post("/ai/analyze/", {
        aoi: selectionData.geojson,
        bounds: selectionData.bounds,
      });

      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
      setAiProgressStep(5);

      setTimeout(() => {
        setAiAnalysis(res.data);
        setShowAILandUse(true);
        setShowAIRecs(true);
        setAiAnalyzing(false);
      }, 400);
    } catch (err) {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
      setAiAnalyzing(false);
      console.error("AI Analysis failed:", err);
      alert("AI Analysis request failed: " + (err.response?.data?.error || err.message));
    }
  }, []);

  const activeBasemap = getBasemap(basemapKey);

  // Load available source datasets
  useEffect(() => {
    api.get("/datasets/").then((res) => {
      const list = res.data.results || res.data || [];
      const styledList = list.map((ds, idx) => ({
        ...ds,
        color: DATASET_PALETTE[idx % DATASET_PALETTE.length],
      }));
      setDatasets(styledList);
    }).catch(() => {});
  }, []);

  const fetchLayer = useCallback((layer, bbox) => {
    api.get(layer.endpoint, { params: bbox ? { bbox } : {} }).then((res) => {
      setLayerData((prev) => ({ ...prev, [layer.key]: res.data }));
    });
  }, []);

  const fetchDatasetLayer = useCallback((datasetId, bbox) => {
    api.get("/parcels/geojson/", { params: { dataset_id: datasetId, ...(bbox ? { bbox } : {}) } }).then((res) => {
      setDatasetLayerData((prev) => ({ ...prev, [datasetId]: res.data }));
    });
  }, []);

  // Fetch active standard layers
  useEffect(() => {
    const bbox = bounds ? [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()].join(",") : undefined;
    LAYER_CONFIG.forEach((layer) => {
      if (activeLayers[layer.key]) fetchLayer(layer, bbox);
    });
  }, [bounds, activeLayers, fetchLayer]);

  // Fetch active dataset layers
  useEffect(() => {
    const bbox = bounds ? [bounds.getWest(), bounds.getSouth(), bounds.getEast(), bounds.getNorth()].join(",") : undefined;
    Object.keys(activeDatasetLayers).forEach((id) => {
      if (activeDatasetLayers[id]) {
        fetchDatasetLayer(id, bbox);
      }
    });
  }, [bounds, activeDatasetLayers, fetchDatasetLayer]);

  // Auto-fit bounds on initial data load
  useEffect(() => {
    if (hasAutoFitted.current || !mapInstance) return;
    const allData = layerData.parcels || layerData.harmonized || Object.values(datasetLayerData)[0];
    if (allData && allData.features && allData.features.length > 0) {
      const b = computeGeoJsonBounds(allData);
      if (b) {
        mapInstance.fitBounds(b, { padding: [40, 40], maxZoom: 18 });
        hasAutoFitted.current = true;
      }
    }
  }, [layerData, datasetLayerData, mapInstance]);

  function handleFitExtent() {
    if (!mapInstance) return;
    let combinedFeatures = [];
    Object.values(layerData).forEach((d) => {
      if (d?.features) combinedFeatures = combinedFeatures.concat(d.features);
    });
    Object.values(datasetLayerData).forEach((d) => {
      if (d?.features) combinedFeatures = combinedFeatures.concat(d.features);
    });

    const b = computeGeoJsonBounds({ features: combinedFeatures });
    if (b) {
      mapInstance.fitBounds(b, { padding: [40, 40], maxZoom: 18 });
    }
  }

  async function handleFeatureClick(feature) {
    if (!feature?.properties?.id) return;
    try {
      const res = await api.get(`/parcels/${feature.properties.id}/`);
      setSelectedParcel(res.data);
    } catch (e) {
      setSelectedParcel(feature.properties);
    }
  }

  return (
    <div className="flex h-screen">
      <div className="flex-1 relative">
        <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            key={activeBasemap.key}
            attribution={activeBasemap.attribution}
            url={activeBasemap.url}
            maxZoom={activeBasemap.maxZoom}
          />

          <BoundsWatcher onBoundsChange={setBounds} />
          <ResetViewController resetSignal={resetSignal} center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} />
          <MapInstanceBridge onReady={setMapInstance} />

          {/* All Parcels Layer */}
          {activeLayers.parcels && layerData.parcels && (
            <GeoJSON
              key={`parcels-${JSON.stringify(layerData.parcels).length}`}
              data={layerData.parcels}
              style={(feature) => ({ color: confidenceColor(feature), weight: 2, fillOpacity: 0.15 })}
              onEachFeature={(feature, layer) => layer.on("click", () => handleFeatureClick(feature))}
            />
          )}

          {/* Harmonized Parcels Layer */}
          {activeLayers.harmonized && layerData.harmonized && (
            <GeoJSON
              key={`harmonized-${JSON.stringify(layerData.harmonized).length}`}
              data={layerData.harmonized}
              style={{ color: "#10b981", weight: 2.5, fillOpacity: 0.25 }}
              onEachFeature={(feature, layer) => layer.on("click", () => handleFeatureClick(feature))}
            />
          )}

          {/* Unmatched Gaps Layer */}
          {activeLayers.unmatched && layerData.unmatched && (
            <GeoJSON
              key={`unmatched-${JSON.stringify(layerData.unmatched).length}`}
              data={layerData.unmatched}
              style={{ color: "#ef4444", weight: 2.5, dashArray: "4", fillOpacity: 0.2 }}
              onEachFeature={(feature, layer) => layer.on("click", () => handleFeatureClick(feature))}
            />
          )}

          {/* Individual Dataset Layers */}
          {datasets.map((ds) => {
            if (!activeDatasetLayers[ds.id] || !datasetLayerData[ds.id]) return null;
            return (
              <GeoJSON
                key={`ds-${ds.id}-${JSON.stringify(datasetLayerData[ds.id]).length}`}
                data={datasetLayerData[ds.id]}
                style={{ color: ds.color, weight: 2, fillOpacity: 0.2 }}
                onEachFeature={(feature, layer) => layer.on("click", () => handleFeatureClick(feature))}
              />
            );
          })}

          {/* Auxiliary Layers */}
          {activeLayers.buildings && layerData.buildings && (
            <GeoJSON key="buildings" data={layerData.buildings} style={{ color: "#b45309", weight: 1, fillOpacity: 0.4 }} />
          )}
          {activeLayers.roads && layerData.roads && (
            <GeoJSON key="roads" data={layerData.roads} style={{ color: "#475569", weight: 2 }} />
          )}
          {activeLayers.utilities && layerData.utilities && (
            <GeoJSON key="utilities" data={layerData.utilities} style={{ color: "#1d4ed8", weight: 1, dashArray: "4" }} />
          )}

          {/* AI Analysis Transparent Overlays */}
          <AIAnalysisOverlay
            analysis={aiAnalysis}
            showLandUse={showAILandUse}
            landUseOpacity={aiLandUseOpacity}
            showRecommendations={showAIRecs}
            onFeatureClick={(feat) => setAiSelectedFeature(feat)}
            onRecommendationClick={(feat) => setAiSelectedFeature(feat)}
          />
        </MapContainer>

        <LayerControl
          basemapKey={basemapKey}
          onBasemapChange={setBasemapKey}
          geoLayers={LAYER_CONFIG}
          activeGeoLayers={activeLayers}
          onToggleGeoLayer={(key, checked) => setActiveLayers((prev) => ({ ...prev, [key]: checked }))}
          datasets={datasets}
          activeDatasetLayers={activeDatasetLayers}
          onToggleDatasetLayer={(id, checked) => setActiveDatasetLayers((prev) => ({ ...prev, [id]: checked }))}
          onResetView={() => setResetSignal((s) => s + 1)}
          onFitExtent={handleFitExtent}
        />
        <SearchControl map={mapInstance} />
        <CoordinateTool map={mapInstance} />
        <SelectAreaControl map={mapInstance} onAnalyzeArea={handleRunAIAnalysis} />
        <LocationControl map={mapInstance} />

        <AIAnalysisPanel
          analysis={aiAnalysis}
          analyzing={aiAnalyzing}
          progressStep={aiProgressStep}
          showLandUse={showAILandUse}
          onToggleLandUse={setShowAILandUse}
          landUseOpacity={aiLandUseOpacity}
          onChangeLandUseOpacity={setAiLandUseOpacity}
          showRecommendations={showAIRecs}
          onToggleRecommendations={setShowAIRecs}
          selectedFeature={aiSelectedFeature}
          onClearSelectedFeature={() => setAiSelectedFeature(null)}
          onClearAnalysis={() => {
            setAiAnalysis(null);
            setAiSelectedFeature(null);
          }}
        />
      </div>

      {selectedParcel && (
        <div className="w-88 bg-white border-l border-ink-200 p-4 overflow-y-auto shadow-lg z-20 flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-start mb-3 pb-2 border-b border-ink-100">
              <div>
                <div className="text-xs font-semibold text-brand-600 uppercase tracking-wider">Parcel Feature</div>
                <div className="font-bold text-ink-900 text-base">{selectedParcel.parcel_id || `Parcel #${selectedParcel.id}`}</div>
              </div>
              <button
                className="text-ink-400 hover:text-ink-700 p-1 rounded hover:bg-ink-100"
                onClick={() => setSelectedParcel(null)}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <dl className="text-xs space-y-2">
              <Row label="Survey Number" value={selectedParcel.survey_number || "—"} />
              <Row label="Area" value={selectedParcel.area ? `${selectedParcel.area.toFixed(1)} m²` : "—"} />
              <Row label="Land Use" value={selectedParcel.land_use || "—"} />
              <Row
                label="Confidence"
                value={
                  selectedParcel.confidence_score !== undefined ? (
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold ${
                      selectedParcel.confidence_band === "HIGH" ? "bg-emerald-100 text-emerald-800" :
                      selectedParcel.confidence_band === "MEDIUM" ? "bg-amber-100 text-amber-800" :
                      "bg-rose-100 text-rose-800"
                    }`}>
                      {selectedParcel.confidence_score.toFixed(1)}% ({selectedParcel.confidence_band || "N/A"})
                    </span>
                  ) : "—"
                }
              />
              <Row label="Status" value={<span className="font-mono text-[11px]">{selectedParcel.validation_status}</span>} />
              <Row
                label="Harmonized"
                value={
                  selectedParcel.is_harmonized ? (
                    <span className="text-emerald-700 font-medium">✓ Harmonized</span>
                  ) : (
                    <span className="text-ink-500">No</span>
                  )
                }
              />
              <Row label="Unresolved Conflicts" value={selectedParcel.conflict_count ?? 0} />
              <Row label="Sources" value={(selectedParcel.source_dataset_names || []).join(", ") || "—"} />
            </dl>

            {selectedParcel.raw_attributes && Object.keys(selectedParcel.raw_attributes).length > 0 && (
              <div className="mt-4 pt-3 border-t border-ink-100">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-500 mb-2">Raw Attributes</div>
                <div className="bg-ink-50 rounded p-2 max-h-40 overflow-y-auto space-y-1">
                  {Object.entries(selectedParcel.raw_attributes).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-[11px]">
                      <span className="text-ink-500 truncate mr-2">{k}:</span>
                      <span className="text-ink-800 font-mono text-right">{String(v ?? "")}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="pt-4 mt-4 border-t border-ink-100 space-y-2">
            <Link
              to="/review"
              className="block w-full text-center text-xs py-2 px-3 bg-brand-600 text-white rounded font-medium hover:bg-brand-700 transition-colors shadow-sm"
            >
              Open Review Queue &rarr;
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between items-center border-b border-ink-100 pb-1">
      <dt className="text-ink-500">{label}</dt>
      <dd className="text-ink-800 font-medium text-right">{value}</dd>
    </div>
  );
}
