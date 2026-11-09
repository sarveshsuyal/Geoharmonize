import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import {
  Layers,
  UploadCloud,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Play,
  FileCode,
  MapPin,
  ArrowRight,
} from "lucide-react";

const STATUS_BADGE = {
  PROCESSED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  VALIDATED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  NEEDS_CRS: "bg-amber-50 text-amber-700 border-amber-200",
  PROCESSING: "bg-sky-50 text-sky-700 border-sky-200",
  VALIDATING: "bg-sky-50 text-sky-700 border-sky-200",
  FAILED: "bg-rose-50 text-rose-700 border-rose-200",
  UPLOADED: "bg-slate-100 text-slate-700 border-slate-200",
};

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [crsPromptFor, setCrsPromptFor] = useState(null);
  const [crsValue, setCrsValue] = useState("EPSG:32644");
  const [busyId, setBusyId] = useState(null);

  function load() {
    setLoading(true);
    api
      .get("/datasets/")
      .then((res) => setDatasets(res.data.results || res.data))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleProcess(id) {
    setBusyId(id);
    try {
      await api.post(`/datasets/${id}/process/`);
    } catch (e) {
      if (e?.response?.data?.code === "INVALID_CRS") {
        setCrsPromptFor(id);
      }
    } finally {
      setBusyId(null);
      load();
    }
  }

  async function handleSetCrs() {
    await api.post(`/datasets/${crsPromptFor}/set-crs/`, { crs: crsValue });
    setCrsPromptFor(null);
    load();
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Geospatial Datasets</h1>
          <p className="text-xs text-slate-500 mt-1">
            Registered land layers, cadastral maps, drone orthomosaics, and administrative boundaries.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={load}
            disabled={loading}
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-colors"
            title="Refresh datasets"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <Link
            to="/upload"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs shadow-sm transition-colors"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload New Layer</span>
          </Link>
        </div>
      </div>

      {/* Datasets Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="px-5 py-3.5">Dataset Name</th>
                <th className="px-4 py-3.5">Type</th>
                <th className="px-4 py-3.5">Authority / Source</th>
                <th className="px-4 py-3.5">Detected CRS</th>
                <th className="px-4 py-3.5">Feature Count</th>
                <th className="px-4 py-3.5">Status</th>
                <th className="px-4 py-3.5">Uploaded</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {datasets.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="px-5 py-3.5">
                    <div className="font-semibold text-slate-900">{d.name}</div>
                    <div className="text-[10px] text-slate-400 font-mono">ID: {d.id}</div>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="px-2 py-0.5 rounded-md font-mono text-[10px] font-semibold bg-slate-100 text-slate-700">
                      {d.dataset_type}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-slate-600 font-medium">
                    {d.source || "Government Authority"}
                  </td>
                  <td className="px-4 py-3.5 font-mono text-slate-700">
                    {d.original_crs ? (
                      <span className="text-slate-800 font-semibold">{d.original_crs}</span>
                    ) : (
                      <span className="text-amber-600 font-semibold">CRS Missing</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-slate-800 font-semibold">
                    {d.feature_count ? d.feature_count.toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-3.5">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                        STATUS_BADGE[d.processing_status] || "bg-slate-100 text-slate-700 border-slate-200"
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-current" />
                      {d.processing_status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-slate-400 text-[11px]">
                    {new Date(d.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-5 py-3.5 text-right space-x-2">
                    <button
                      onClick={() => handleProcess(d.id)}
                      disabled={busyId === d.id}
                      className="px-2.5 py-1 rounded-md text-xs font-medium border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors disabled:opacity-50"
                    >
                      {busyId === d.id ? "Processing..." : "Process / Re-run"}
                    </button>
                  </td>
                </tr>
              ))}

              {datasets.length === 0 && !loading && (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-slate-400">
                    <Layers className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                    <div className="font-semibold text-slate-600 text-sm">No datasets available</div>
                    <div className="text-xs text-slate-400 mt-1">
                      Upload your first cadastral file or run the demo generator from the Dashboard.
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* CRS Modal */}
      {crsPromptFor && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center gap-2 text-amber-700 font-bold text-sm">
              <AlertCircle className="w-5 h-5 text-amber-600" />
              <span>CRS Definition Required</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              This dataset does not specify a Coordinate Reference System (.prj file missing). Select the
              appropriate projection:
            </p>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Target CRS</label>
              <select
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs font-mono"
                value={crsValue}
                onChange={(e) => setCrsValue(e.target.value)}
              >
                <option value="EPSG:32644">EPSG:32644 (UTM 44N - Northern India / UP / Delhi)</option>
                <option value="EPSG:32643">EPSG:32643 (UTM 43N - Western India / Gujarat)</option>
                <option value="EPSG:4326">EPSG:4326 (WGS 84 Geographic Lat/Lon)</option>
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCrsPromptFor(null)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSetCrs}
                className="px-3.5 py-1.5 text-xs font-semibold bg-sky-600 hover:bg-sky-700 text-white rounded-lg shadow-sm"
              >
                Assign & Process
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
