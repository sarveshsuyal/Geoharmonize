import React, { useState } from "react";

const LAND_USE_LEGEND = [
  { key: "BUILT_UP", label: "Built-up / Occupied", color: "#ef4444", icon: "🟥" },
  { key: "BARE_LAND", label: "Bare / Vacant", color: "#22c55e", icon: "🟩" },
  { key: "AGRICULTURE", label: "Agriculture", color: "#eab308", icon: "🟨" },
  { key: "VEGETATION", label: "Vegetation", color: "#15803d", icon: "🌲" },
  { key: "WATER", label: "Water", color: "#3b82f6", icon: "🟦" },
  { key: "ROAD", label: "Roads / Infrastructure", color: "#f97316", icon: "🟧" },
  { key: "UNKNOWN", label: "Unknown / Other", color: "#64748b", icon: "⬜" },
];

const REC_LEGEND = [
  { type: "AGRICULTURE", label: "Agriculture Candidate", color: "#10b981", icon: "🟢" },
  { type: "CONSTRUCTION", label: "Construction Candidate", color: "#f97316", icon: "🟠" },
  { type: "NOT_RECOMMENDED", label: "Not Recommended / Low Conf", color: "#94a3b8", icon: "⚪" },
];

export default function AIAnalysisPanel({
  analysis,
  analyzing,
  progressStep,
  showLandUse,
  onToggleLandUse,
  landUseOpacity,
  onChangeLandUseOpacity,
  showRecommendations,
  onToggleRecommendations,
  selectedFeature,
  onClearSelectedFeature,
  onClearAnalysis,
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState("summary"); // summary | legend | layers

  if (analyzing) {
    const steps = [
      "Preparing imagery...",
      "Processing image...",
      "Extracting features...",
      "Generating land-use classification...",
      "Generating recommendations...",
      "Analysis complete!",
    ];

    return (
      <div className="absolute top-28 right-4 z-[1000] w-80 bg-white/95 backdrop-blur border border-ink-200 rounded-lg shadow-xl p-4 text-ink-800 space-y-3">
        <div className="flex items-center gap-2 border-b border-ink-100 pb-2">
          <span className="inline-block w-4 h-4 border-2 border-brand-600 border-t-transparent rounded-full animate-spin"></span>
          <span className="text-sm font-semibold text-brand-700">Running AI GIS Analysis…</span>
        </div>

        <div className="space-y-1.5 text-xs">
          {steps.map((step, idx) => {
            const isCurrent = idx === progressStep;
            const isDone = idx < progressStep;
            return (
              <div
                key={step}
                className={`flex items-center gap-2 py-0.5 transition-colors ${
                  isCurrent
                    ? "font-semibold text-brand-600"
                    : isDone
                    ? "text-emerald-700"
                    : "text-ink-400"
                }`}
              >
                <span>{isDone ? "✓" : isCurrent ? "➔" : "○"}</span>
                <span>{step}</span>
              </div>
            );
          })}
        </div>

        <div className="text-[11px] text-ink-500 bg-ink-50 rounded p-2 border border-ink-100 italic">
          Clipping imagery to your selected AOI and running computer vision & spectral segmentation.
        </div>
      </div>
    );
  }

  if (!analysis) return null;

  const stats = analysis.summary_statistics || {};
  const percentages = stats.percentages || {};
  const recSummary = stats.recommendations_summary || {};

  return (
    <div className="absolute top-28 right-4 z-[1000] w-88 bg-white/95 backdrop-blur border border-ink-200 rounded-lg shadow-xl overflow-hidden text-ink-800 transition-all">
      {/* Header */}
      <div className="px-3.5 py-2.5 bg-brand-50/70 border-b border-ink-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-base">⚡</span>
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-brand-700">
              AI Analysis Result
            </div>
            <div className="text-[11px] text-ink-500">
              {stats.total_area_ha ? `${stats.total_area_ha} ha` : ""} ({stats.total_area_m2?.toLocaleString()} m²)
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            className="text-ink-500 hover:text-ink-800 text-xs px-1.5 py-0.5 rounded hover:bg-white"
            title={collapsed ? "Expand panel" : "Collapse panel"}
          >
            {collapsed ? "▼" : "▲"}
          </button>
          <button
            type="button"
            onClick={onClearAnalysis}
            className="text-ink-400 hover:text-rose-600 text-sm px-1 rounded hover:bg-white"
            title="Clear AI analysis overlay"
          >
            ✕
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="max-h-[75vh] overflow-y-auto">
          {/* Navigation Tabs */}
          <div className="flex border-b border-ink-100 bg-ink-50/60 text-xs font-medium text-ink-600">
            <button
              type="button"
              onClick={() => setActiveTab("summary")}
              className={`flex-1 py-1.5 text-center border-b-2 transition-colors ${
                activeTab === "summary"
                  ? "border-brand-600 text-brand-700 bg-white font-semibold"
                  : "border-transparent hover:text-ink-900"
              }`}
            >
              Summary
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("layers")}
              className={`flex-1 py-1.5 text-center border-b-2 transition-colors ${
                activeTab === "layers"
                  ? "border-brand-600 text-brand-700 bg-white font-semibold"
                  : "border-transparent hover:text-ink-900"
              }`}
            >
              Layers & Opacity
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("legend")}
              className={`flex-1 py-1.5 text-center border-b-2 transition-colors ${
                activeTab === "legend"
                  ? "border-brand-600 text-brand-700 bg-white font-semibold"
                  : "border-transparent hover:text-ink-900"
              }`}
            >
              Legend
            </button>
          </div>

          <div className="p-3.5 space-y-3">
            {/* TAB 1: SUMMARY */}
            {activeTab === "summary" && (
              <>
                {/* Land Use Percentage Grid */}
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-ink-400 mb-1.5">
                    Land-Use Distribution
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 text-xs">
                    <StatBox label="Built-up / Occupied" value={`${percentages.BUILT_UP ?? 0}%`} color="#ef4444" />
                    <StatBox label="Agriculture" value={`${percentages.AGRICULTURE ?? 0}%`} color="#eab308" />
                    <StatBox label="Bare / Vacant" value={`${percentages.BARE_LAND ?? 0}%`} color="#22c55e" />
                    <StatBox label="Vegetation" value={`${percentages.VEGETATION ?? 0}%`} color="#15803d" />
                    <StatBox label="Water Body" value={`${percentages.WATER ?? 0}%`} color="#3b82f6" />
                    <StatBox label="Roads / Transport" value={`${percentages.ROAD ?? 0}%`} color="#f97316" />
                  </div>
                </div>

                {/* Features Detected Metrics */}
                <div className="pt-2 border-t border-ink-100 flex justify-between text-xs text-ink-600">
                  <div>
                    <span className="text-ink-400">Detected Buildings:</span>{" "}
                    <span className="font-semibold text-ink-800">{stats.detected_buildings_count ?? 0}</span>
                  </div>
                  <div>
                    <span className="text-ink-400">Detected Roads:</span>{" "}
                    <span className="font-semibold text-ink-800">{stats.detected_road_length_km ?? 0} km</span>
                  </div>
                </div>

                {/* Planning Recommendations Section */}
                <div className="pt-2 border-t border-ink-100 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-brand-700 flex items-center gap-1">
                      <span>★</span> Planning Recommendations
                    </span>
                    <span className="text-[10px] text-ink-400 font-mono">Advisory</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 rounded bg-emerald-50 border border-emerald-200">
                      <div className="text-[10px] text-emerald-800 font-medium">Agriculture Candidate</div>
                      <div className="text-sm font-bold text-emerald-700">
                        {recSummary.agriculture_candidate_ha ?? 0} ha
                      </div>
                    </div>
                    <div className="p-2 rounded bg-amber-50 border border-amber-200">
                      <div className="text-[10px] text-amber-800 font-medium">Construction Candidate</div>
                      <div className="text-sm font-bold text-amber-700">
                        {recSummary.construction_candidate_ha ?? 0} ha
                      </div>
                    </div>
                  </div>

                  <div className="text-[10px] text-ink-500 bg-ink-50 border border-ink-100 rounded p-1.5 leading-tight">
                    {recSummary.disclaimer || "Simulated planning recommendation. Non-binding decision support."}
                  </div>
                </div>

                {/* Confidence & Model Attribution (Feature 14) */}
                <div className="pt-2 border-t border-ink-100 text-[11px] text-ink-500 space-y-1">
                  <div className="flex justify-between">
                    <span>Overall Confidence:</span>
                    <span className="font-semibold text-emerald-700">{stats.overall_confidence ?? 75}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Analysis Method:</span>
                    <span className="font-mono text-ink-700 text-[10px]">
                      {analysis.method_category || "COMPUTER_VISION_HEURISTIC"}
                    </span>
                  </div>
                  <div className="text-[10px] text-ink-400 italic">
                    Method: {analysis.model_name} ({analysis.model_version}). Classical CV & spectral heuristic.
                  </div>
                </div>
              </>
            )}

            {/* TAB 2: LAYERS & OPACITY CONTROLS */}
            {activeTab === "layers" && (
              <div className="space-y-4 text-xs">
                {/* Land Use Layer Toggle */}
                <div className="space-y-2 p-2.5 rounded bg-ink-50 border border-ink-100">
                  <label className="flex items-center gap-2 cursor-pointer select-none font-medium text-ink-800">
                    <input
                      type="checkbox"
                      checked={showLandUse}
                      onChange={(e) => onToggleLandUse(e.target.checked)}
                      className="rounded border-ink-300 text-brand-600 focus:ring-brand-500"
                    />
                    <span>AI Land Use Classification Layer</span>
                  </label>

                  {showLandUse && (
                    <div className="pt-1.5 pl-6 space-y-1">
                      <div className="flex justify-between text-[11px] text-ink-600">
                        <span>Overlay Opacity:</span>
                        <span className="font-mono font-semibold">{Math.round(landUseOpacity * 100)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0.15"
                        max="0.85"
                        step="0.05"
                        value={landUseOpacity}
                        onChange={(e) => onChangeLandUseOpacity(parseFloat(e.target.value))}
                        className="w-full accent-brand-600 cursor-pointer"
                      />
                      <div className="flex justify-between text-[10px] text-ink-400">
                        <span>Transparent (15%)</span>
                        <span>Solid (85%)</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Recommendations Layer Toggle */}
                <div className="space-y-2 p-2.5 rounded bg-ink-50 border border-ink-100">
                  <label className="flex items-center gap-2 cursor-pointer select-none font-medium text-ink-800">
                    <input
                      type="checkbox"
                      checked={showRecommendations}
                      onChange={(e) => onToggleRecommendations(e.target.checked)}
                      className="rounded border-ink-300 text-brand-600 focus:ring-brand-500"
                    />
                    <span>AI Planning Recommendations Layer</span>
                  </label>
                  <div className="text-[11px] text-ink-500 pl-6">
                    Displays candidate agriculture and development zones filtered from bare land.
                  </div>
                </div>

                <div className="text-[11px] text-ink-500 bg-brand-50/50 p-2 rounded border border-brand-100">
                  💡 <strong>Tip:</strong> The underlying map remains interactive. You can switch between Satellite and
                  OpenStreetMap basemaps at any time without losing the AI classification overlay.
                </div>
              </div>
            )}

            {/* TAB 3: LEGENDS */}
            {activeTab === "legend" && (
              <div className="space-y-3.5 text-xs">
                {/* Land Use Legend (Feature 6) */}
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-ink-700 mb-2">
                    AI Land Use
                  </div>
                  <div className="space-y-1.5">
                    {LAND_USE_LEGEND.map((item) => (
                      <div key={item.key} className="flex items-center justify-between text-xs py-0.5">
                        <div className="flex items-center gap-2">
                          <span
                            className="inline-block w-3.5 h-3.5 rounded-sm shadow-sm border border-black/10"
                            style={{ backgroundColor: item.color }}
                          />
                          <span className="text-ink-800 font-medium">{item.label}</span>
                        </div>
                        <span className="text-ink-400 font-mono text-[11px]">
                          {percentages[item.key] !== undefined ? `${percentages[item.key]}%` : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Planning Recommendations Legend */}
                <div className="pt-2.5 border-t border-ink-100">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-ink-700 mb-2">
                    Planning Recommendations
                  </div>
                  <div className="space-y-1.5">
                    {REC_LEGEND.map((item) => (
                      <div key={item.type} className="flex items-center gap-2 text-xs py-0.5">
                        <span
                          className="inline-block w-3.5 h-3.5 rounded-sm border-2 border-dashed shadow-sm"
                          style={{ borderColor: item.color, backgroundColor: `${item.color}33` }}
                        />
                        <span className="text-ink-800">{item.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Feature Inspector Card (when user clicks an AI polygon on map) */}
            {selectedFeature && (
              <div className="mt-3 pt-3 border-t border-ink-200 bg-ink-50/80 p-2.5 rounded-md space-y-1.5 text-xs">
                <div className="flex items-center justify-between border-b border-ink-200 pb-1">
                  <span className="font-semibold text-brand-700">
                    {selectedFeature.properties.label || selectedFeature.properties.land_use}
                  </span>
                  <button
                    type="button"
                    onClick={onClearSelectedFeature}
                    className="text-ink-400 hover:text-ink-700 font-bold"
                  >
                    ✕
                  </button>
                </div>

                <div className="space-y-1 text-ink-700">
                  <div className="flex justify-between">
                    <span className="text-ink-500">Area:</span>
                    <span className="font-mono">
                      {selectedFeature.properties.area_ha ? `${selectedFeature.properties.area_ha} ha` : `${selectedFeature.properties.area_m2} m²`}
                    </span>
                  </div>

                  {selectedFeature.properties.suitability_score !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-ink-500">Suitability Score:</span>
                      <span className="font-semibold text-emerald-700 font-mono">
                        {selectedFeature.properties.suitability_score}%
                      </span>
                    </div>
                  )}

                  {selectedFeature.properties.confidence !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-ink-500">Confidence:</span>
                      <span className="font-mono">{selectedFeature.properties.confidence}%</span>
                    </div>
                  )}

                  {selectedFeature.properties.reasons?.length > 0 && (
                    <div className="pt-1">
                      <div className="text-[11px] font-medium text-ink-500 mb-0.5">Decision Factors:</div>
                      <ul className="list-disc list-inside text-[11px] text-ink-600 space-y-0.5">
                        {selectedFeature.properties.reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value, color }) {
  return (
    <div className="p-2 rounded bg-ink-50 border border-ink-100 flex items-center justify-between">
      <div className="flex items-center gap-1.5 truncate">
        <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: color }} />
        <span className="text-ink-700 truncate text-[11px]">{label}</span>
      </div>
      <span className="font-bold text-ink-900 font-mono text-xs">{value}</span>
    </div>
  );
}
