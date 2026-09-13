import React, { useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";

const DATASET_TYPES = [
  "CADASTRAL", "DRONE", "ORTHO_IMAGE", "SATELLITE", "MUNICIPAL", "REVENUE",
  "BUILDING", "ROAD", "UTILITY", "GNSS", "DSM", "DTM", "OTHER",
];

export default function UploadPage() {
  const [name, setName] = useState("");
  const [datasetType, setDatasetType] = useState("CADASTRAL");
  const [source, setSource] = useState("");
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setStatus(null);
    const form = new FormData();
    form.append("name", name || file.name);
    form.append("dataset_type", datasetType);
    form.append("source", source);
    form.append("file", file);
    try {
      const res = await api.post("/datasets/", form, { headers: { "Content-Type": "multipart/form-data" } });
      setStatus({ ok: true, dataset: res.data });
    } catch (e) {
      setStatus({ ok: false, message: e?.response?.data?.detail || e?.response?.data?.error_message || "Upload failed." });
    } finally {
      setBusy(false);
    }
  }

  const meta = status?.dataset?.metadata || {};

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-xl font-semibold text-ink-900 mb-1">Upload Geospatial Dataset</h1>
      <p className="text-sm text-ink-500 mb-4">
        Supported formats: GeoJSON (.geojson, .json), Shapefile archive (.zip), GeoPackage (.gpkg), KML/KMZ, CSV.
      </p>

      <form onSubmit={handleSubmit} className="card p-5 space-y-4">
        <div>
          <label className="block text-xs font-medium text-ink-600 mb-1">Dataset Name</label>
          <input className="w-full border border-ink-200 rounded-md px-3 py-2 text-sm"
                 value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Meerut Cadastral Survey 2024" />
        </div>
        <div>
          <label className="block text-xs font-medium text-ink-600 mb-1">Dataset Type</label>
          <select className="w-full border border-ink-200 rounded-md px-3 py-2 text-sm"
                  value={datasetType} onChange={(e) => setDatasetType(e.target.value)}>
            {DATASET_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-ink-600 mb-1">Source / Issuing Authority</label>
          <input className="w-full border border-ink-200 rounded-md px-3 py-2 text-sm"
                 value={source} onChange={(e) => setSource(e.target.value)} placeholder="e.g. State Revenue Department" />
        </div>
        <div>
          <label className="block text-xs font-medium text-ink-600 mb-1">Geospatial File</label>
          <input type="file" className="w-full text-sm" onChange={(e) => setFile(e.target.files[0])} required />
        </div>
        <button type="submit" disabled={busy} className="btn-primary">
          {busy ? "Uploading & Ingesting..." : "Upload & Ingest Dataset"}
        </button>
      </form>

      {status && (
        <div className={`card p-5 mt-5 border ${status.ok ? "border-green-300 bg-green-50/20" : "border-red-300 bg-red-50/20"}`}>
          {status.ok ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-status-high flex items-center gap-2">
                  <span>✓</span> Ingestion Successful: {status.dataset.name}
                </div>
                <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-800 font-medium">
                  {status.dataset.processing_status}
                </span>
              </div>

              {/* Extracted Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-2">
                <div className="bg-white p-2.5 rounded border border-ink-100 shadow-sm">
                  <div className="text-ink-400">Features</div>
                  <div className="text-base font-semibold text-ink-800">{status.dataset.feature_count ?? meta.feature_count ?? "—"}</div>
                </div>
                <div className="bg-white p-2.5 rounded border border-ink-100 shadow-sm">
                  <div className="text-ink-400">CRS</div>
                  <div className="text-sm font-semibold text-ink-800 truncate" title={status.dataset.original_crs || "None"}>
                    {status.dataset.original_crs || "Needs CRS"}
                  </div>
                </div>
                <div className="bg-white p-2.5 rounded border border-ink-100 shadow-sm">
                  <div className="text-ink-400">Geometry Types</div>
                  <div className="text-xs font-medium text-ink-800">
                    {(meta.layer_geometry_types || [status.dataset.geometry_type]).join(", ") || "Polygon"}
                  </div>
                </div>
                <div className="bg-white p-2.5 rounded border border-ink-100 shadow-sm">
                  <div className="text-ink-400">Valid / Invalid</div>
                  <div className="text-xs font-medium text-ink-800">
                    <span className="text-green-600 font-semibold">{meta.valid_geometry_count ?? status.dataset.feature_count ?? 0} valid</span>
                    {meta.invalid_geometry_count > 0 && (
                      <span className="text-red-500 font-semibold block"> {meta.invalid_geometry_count} invalid</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Warnings / Notices */}
              {meta.invalid_geometry_count > 0 && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
                  ⚠️ Dataset contains {meta.invalid_geometry_count} invalid geometries. They will be automatically validated and repaired where safe during harmonization.
                </div>
              )}

              {/* Attributes schema */}
              {meta.field_names && meta.field_names.length > 0 && (
                <div className="text-xs text-ink-600 pt-1">
                  <span className="font-semibold text-ink-700">Detected Attributes: </span>
                  {meta.field_names.map((fn) => (
                    <span key={fn} className="inline-block bg-ink-100 rounded px-1.5 py-0.5 mr-1 mb-1 font-mono text-[11px]">
                      {fn}
                    </span>
                  ))}
                </div>
              )}

              <div className="pt-2 flex gap-3">
                <Link to="/harmonization" className="btn-primary text-xs">
                  Proceed to Harmonization →
                </Link>
                <Link to="/datasets" className="btn-secondary text-xs">
                  View All Datasets
                </Link>
              </div>
            </div>
          ) : (
            <div className="text-sm text-status-low font-medium">{status.message}</div>
          )}
        </div>
      )}
    </div>
  );
}
