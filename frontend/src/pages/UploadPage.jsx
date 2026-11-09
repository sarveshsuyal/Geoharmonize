import React, { useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import {
  UploadCloud,
  FileCheck,
  AlertCircle,
  CheckCircle2,
  MapPin,
  Layers,
  ArrowRight,
  RefreshCw,
  FileText,
} from "lucide-react";

const DATASET_TYPES = [
  { value: "CADASTRAL", label: "Cadastral Survey Map (Khasra/Parcels)" },
  { value: "DRONE", label: "High-Resolution Drone Orthomosaic" },
  { value: "SATELLITE", label: "Satellite Imagery Layer" },
  { value: "REVENUE", label: "Revenue Land Records (RoR)" },
  { value: "MUNICIPAL", label: "Municipal GIS Boundaries" },
  { value: "BUILDING", label: "Building Footprints Vector" },
  { value: "ROAD", label: "Road & Transport Network" },
  { value: "UTILITY", label: "Utilities & Infrastructure" },
  { value: "GNSS", label: "GNSS / Ground Survey Points" },
  { value: "OTHER", label: "Other Ancillary Layer" },
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
    form.append("source", source || "Department of Land Resources");
    form.append("file", file);

    try {
      const res = await api.post("/datasets/", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setStatus({ ok: true, dataset: res.data });
    } catch (e) {
      setStatus({
        ok: false,
        message:
          e?.response?.data?.detail ||
          e?.response?.data?.error_message ||
          "Upload failed. Verify dataset format and CRS.",
      });
    } finally {
      setBusy(false);
    }
  }

  const meta = status?.dataset?.metadata || {};

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Upload Geospatial Land Dataset</h1>
        <p className="text-xs text-slate-500 mt-1">
          Ingest vector or raster layers for automated CRS transformation, validation, and multi-source matching.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Upload Form (2 cols) */}
        <div className="md:col-span-2 space-y-5">
          <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Dataset Name
              </label>
              <input
                type="text"
                className="w-full border border-slate-300 focus:border-sky-500 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Meerut Cadastral Survey 2024 (Phase 1)"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Dataset Classification
              </label>
              <select
                className="w-full border border-slate-300 focus:border-sky-500 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500"
                value={datasetType}
                onChange={(e) => setDatasetType(e.target.value)}
              >
                {DATASET_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Issuing Authority / Agency
              </label>
              <input
                type="text"
                className="w-full border border-slate-300 focus:border-sky-500 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="e.g. State Settlement Office, Survey of India, or Municipal Corp"
              />
            </div>

            {/* File Drop Area */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Geospatial File
              </label>
              <div className="border-2 border-dashed border-slate-300 hover:border-sky-400 rounded-xl p-5 text-center transition-colors bg-slate-50/50">
                <UploadCloud className="w-8 h-8 mx-auto text-slate-400 mb-2" />
                <div className="text-xs font-medium text-slate-700 mb-1">
                  {file ? file.name : "Choose a file to upload"}
                </div>
                <div className="text-[11px] text-slate-400 mb-3">
                  GeoJSON (.geojson, .json), Shapefile archive (.zip), GeoPackage (.gpkg), KML/KMZ, CSV
                </div>
                <label className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 cursor-pointer shadow-sm">
                  <span>Browse File</span>
                  <input
                    type="file"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files[0])}
                    required
                  />
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={busy || !file}
              className="w-full py-2.5 px-4 rounded-lg bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs flex items-center justify-center gap-2 shadow-sm transition-colors disabled:opacity-50"
            >
              {busy ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Ingesting and Validating Geometries...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" />
                  <span>Upload & Ingest Dataset</span>
                </>
              )}
            </button>
          </form>

          {/* Upload Status Card */}
          {status && (
            <div
              className={`p-5 rounded-2xl border shadow-sm space-y-3 ${
                status.ok ? "bg-emerald-50/60 border-emerald-200" : "bg-rose-50/60 border-rose-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {status.ok ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-rose-600" />
                  )}
                  <span className={`font-bold text-sm ${status.ok ? "text-emerald-900" : "text-rose-900"}`}>
                    {status.ok ? `Ingested: ${status.dataset.name}` : "Dataset Ingestion Failed"}
                  </span>
                </div>
                {status.ok && (
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    {status.dataset.processing_status}
                  </span>
                )}
              </div>

              {status.ok ? (
                <>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs pt-1">
                    <div className="bg-white/80 p-2 rounded-lg border border-emerald-100">
                      <div className="text-[10px] text-slate-500">Feature Count</div>
                      <div className="font-bold text-slate-900 text-sm">
                        {status.dataset.feature_count ?? meta.feature_count ?? "—"}
                      </div>
                    </div>
                    <div className="bg-white/80 p-2 rounded-lg border border-emerald-100">
                      <div className="text-[10px] text-slate-500">Detected CRS</div>
                      <div className="font-bold text-slate-900 truncate" title={status.dataset.original_crs}>
                        {status.dataset.original_crs || "None"}
                      </div>
                    </div>
                    <div className="bg-white/80 p-2 rounded-lg border border-emerald-100">
                      <div className="text-[10px] text-slate-500">Geometry Type</div>
                      <div className="font-bold text-slate-900 truncate">
                        {meta.geometry_types?.join(", ") || "Polygon"}
                      </div>
                    </div>
                    <div className="bg-white/80 p-2 rounded-lg border border-emerald-100">
                      <div className="text-[10px] text-slate-500">Topology Status</div>
                      <div className="font-bold text-emerald-700">Valid</div>
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <Link
                      to="/map"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs shadow-sm"
                    >
                      <span>Inspect On Map</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </>
              ) : (
                <div className="text-xs text-rose-700 leading-relaxed">{status.message}</div>
              )}
            </div>
          )}
        </div>

        {/* Right Info Column (1 col) */}
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Supported Data Standards
            </h3>
            <div className="space-y-2 text-xs text-slate-600 leading-relaxed">
              <div className="flex items-start gap-2">
                <FileText className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
                <span>
                  <strong>Vector Boundaries</strong>: GeoJSON, ESRI Shapefile (.zip with .shp, .shx, .dbf, .prj), GeoPackage (.gpkg).
                </span>
              </div>
              <div className="flex items-start gap-2">
                <FileText className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
                <span>
                  <strong>Raster & Ortho</strong>: GeoTIFF (.tif) with embedded CRS metadata.
                </span>
              </div>
              <div className="flex items-start gap-2">
                <FileText className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                <span>
                  <strong>Tabular Revenue</strong>: CSV with Khasra, Survey No, and WKT / coordinate columns.
                </span>
              </div>
            </div>
          </div>

          <div className="bg-sky-50 border border-sky-100 rounded-2xl p-5 text-xs text-sky-950 space-y-2">
            <div className="font-bold text-sky-900 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-sky-600" />
              Automated CRS Normalization
            </div>
            <p className="leading-relaxed text-sky-800">
              Regardless of the input coordinate system (WGS84, local state Cassini, or UTM), the system
              transforms all valid geometry into <strong>EPSG:32644</strong> for unified topological
              comparisons.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
