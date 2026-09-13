import React, { useState } from "react";
import { BASEMAPS } from "./basemaps.js";

/**
 * Compact floating layer control, modeled on modern GIS apps: closed by
 * default so the satellite view isn't obstructed, expands on demand.
 *
 * Only exposes sections backed by real, working functionality:
 *  - BASEMAP (Satellite / OpenStreetMap styles)
 *  - GEOHARMONIZE (existing parcels/buildings/roads/utilities layers)
 *  - TOOLS (Reset View)
 *
 * Land Analysis / AI sections are intentionally NOT included here yet -
 * they get added once the analysis pipeline exists, so we never ship a
 * toggle that does nothing (see project rule: no fake completeness).
 */
export default function LayerControl({
  basemapKey,
  onBasemapChange,
  geoLayers,
  activeGeoLayers,
  onToggleGeoLayer,
  datasets = [],
  activeDatasetLayers = {},
  onToggleDatasetLayer,
  onResetView,
  onFitExtent,
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="absolute top-3 left-3 z-[1000]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-sm px-3 py-2 text-sm font-medium text-ink-800 hover:bg-white"
        aria-expanded={open}
        aria-label="Toggle layer control"
      >
        <LayersIcon />
        Layers
      </button>

      {open && (
        <div className="mt-2 w-72 max-h-[80vh] overflow-y-auto bg-white/95 backdrop-blur border border-ink-200 rounded-md shadow-md">
          <Section title="Basemap">
            <div className="grid grid-cols-2 gap-1.5">
              {BASEMAPS.map((b) => (
                <button
                  key={b.key}
                  type="button"
                  onClick={() => onBasemapChange(b.key)}
                  className={`text-xs px-2 py-1.5 rounded border transition-colors ${
                    basemapKey === b.key
                      ? "bg-brand-600 border-brand-600 text-white"
                      : "border-ink-200 text-ink-700 hover:bg-ink-50"
                  }`}
                >
                  {b.label}
                </button>
              ))}
            </div>
          </Section>

          <Section title="Harmonization Layers">
            {geoLayers.map((layer) => (
              <label key={layer.key} className="flex items-center gap-2 text-sm text-ink-700 py-0.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!activeGeoLayers[layer.key]}
                  onChange={(e) => onToggleGeoLayer(layer.key, e.target.checked)}
                />
                <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: layer.color }} />
                {layer.label}
              </label>
            ))}
            <div className="pt-2 mt-1 border-t border-ink-100 text-[11px] text-ink-500 leading-snug">
              Parcel color reflects match confidence:{" "}
              <span className="text-status-high">green = high</span>,{" "}
              <span className="text-status-medium">amber = medium</span>,{" "}
              <span className="text-status-low">red = low</span>.
            </div>
          </Section>

          {datasets.length > 0 && (
            <Section title="Source Datasets">
              <div className="space-y-1">
                {datasets.map((ds) => (
                  <label key={ds.id} className="flex items-center gap-2 text-sm text-ink-700 py-0.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!activeDatasetLayers[ds.id]}
                      onChange={(e) => onToggleDatasetLayer(ds.id, e.target.checked)}
                    />
                    <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: ds.color || "#8b5cf6" }} />
                    <span className="truncate flex-1 text-xs" title={ds.name}>{ds.name}</span>
                  </label>
                ))}
              </div>
            </Section>
          )}

          <Section title="Tools" last>
            <div className="flex flex-col gap-1.5">
              {onFitExtent && (
                <button
                  type="button"
                  onClick={onFitExtent}
                  className="w-full text-left text-xs px-2.5 py-1.5 rounded border border-ink-200 text-ink-700 hover:bg-ink-50 flex items-center gap-1.5"
                >
                  <span>⛶</span> Fit to Parcels Extent
                </button>
              )}
              <button
                type="button"
                onClick={onResetView}
                className="w-full text-left text-xs px-2.5 py-1.5 rounded border border-ink-200 text-ink-700 hover:bg-ink-50 flex items-center gap-1.5"
              >
                <span>⟳</span> Reset View
              </button>
            </div>
          </Section>
        </div>
      )}
    </div>
  );
}

function Section({ title, children, last }) {
  return (
    <div className={`px-3 py-2.5 ${!last ? "border-b border-ink-100" : ""}`}>
      <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-400 mb-1.5">{title}</div>
      {children}
    </div>
  );
}

function LayersIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  );
}
